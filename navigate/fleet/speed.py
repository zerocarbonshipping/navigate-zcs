# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from scipy.optimize import minimize_scalar

from navigate.core.enum_ import SpeedAlignmentID
from navigate.core.nodes.vessel import Vessel
from navigate.fleet.marginal_saving import calculate_marginal_speed_saving, get_smoothed_energy_duals_speed
from navigate.fleet.operation import calculate_operational_profile, transfer_operational_profile
from navigate.fleet.power import calculate_speed_bounds, calculate_technical_speed_limits, loads_are_convex
from navigate.fleet.utils import net_energy_from_raw
from navigate.util import YEAR, to_numpy

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet

logger = logging.getLogger(__name__)


@dataclass
class SpeedResult:
    vessel: Vessel
    mu_ref: float = 0.
    mu_optimal: float = 0.
    deltas_ref: np.ndarray = field(default_factory=lambda: np.empty(0))
    speed_min: np.ndarray = field(default_factory=lambda: np.empty(0))
    speed_max: np.ndarray = field(default_factory=lambda: np.empty(0))
    distribution: np.ndarray = field(default_factory=lambda: np.empty(0))
    maximum_change: float = 0.


def perform_speed_management(fleet: Fleet,
                             time_step: float,
                             idx: int
                             ) -> None:
    """
    Dynamically update the speed of each vessel in the fleet if speed management is allowed.

    Vessel speeds are first individually optimized and then aligned across vessels according to the
    fleet's speed alignment method.

    Parameters
    ----------
    fleet
        Fleet for which speed management is performed.
    time_step
        Size of the current time-step in days.
    idx
        Current time-step index.
    """

    if not fleet.allow_speed_management:
        return

    maximum_change = fleet.maximum_speed_change.get() * time_step / YEAR
    alignment = fleet.speed_alignment

    # transfer fleet-level operational savings to vessel expectations
    fleet.transfer_operational_saving_to_vessels()

    # phase 1: individual optimization
    results = [_optimize_vessel_speed(vessel, maximum_change, idx) for vessel in fleet.get_vessels()]

    # anchor speed to reference if enabled
    if fleet.assume_reference_speed_optimal:
        for result in results:
            anchor_ref = result.vessel.expectation.get_speed_anchor_reference()
            if np.isnan(anchor_ref):
                _initialize_speed_anchor(result)
            else:
                _shift_speed_to_anchor(result)

    # phase 2: alignment and finalization
    if alignment == SpeedAlignmentID.INDIVIDUAL:
        for result in results:
            _finalize_vessel_speed(result, result.mu_optimal, idx)

    else:
        mu_values = [result.mu_optimal for result in results]

        if alignment == SpeedAlignmentID.MINIMUM:
            mu_aligned = min(mu_values)

        elif alignment == SpeedAlignmentID.MAXIMUM:
            mu_aligned = max(mu_values)

        elif alignment == SpeedAlignmentID.AVERAGE:
            weights = fleet.get_multipliers()
            mu_aligned = float(np.average(mu_values, weights=weights))

        else:
            raise ValueError(f"Unknown speed alignment method: {alignment}")

        for result in results:
            _finalize_vessel_speed(result, mu_aligned, idx)


def _initialize_speed_anchor(result: SpeedResult) -> None:
    """
    Store the initial route reference speed and modelled optimal speed as anchors.

    The route reference speed is used as the target for the first time-step (no change from
    the reference). Both values are stored on the vessel expectation for use in subsequent
    time-steps by :func:`_shift_speed_to_anchor`.

    Parameters
    ----------
    result
        SpeedResult from individual optimization.
    """

    speeds_reference = to_numpy(result.vessel.route.speeds)
    operations = calculate_operational_profile(result.vessel, speeds_reference)
    mu_route = float(np.average(speeds_reference, weights=operations.distribution))

    expectation = result.vessel.expectation
    expectation.set_speed_anchor_reference(mu_route)
    expectation.set_speed_anchor_optimal(result.mu_optimal)
    result.mu_optimal = mu_route


def _shift_speed_to_anchor(result: SpeedResult) -> None:
    """
    Shift the optimal speed relative to the stored anchor values.

    The adjusted target is: mu_ref_initial + (mu_optimal - mu_optimal_initial), so speed only
    changes if the modelled optimum has shifted relative to its initial value.

    Parameters
    ----------
    result
        SpeedResult from individual optimization.
    """

    expectation = result.vessel.expectation
    anchor_ref = expectation.get_speed_anchor_reference()
    anchor_opt = expectation.get_speed_anchor_optimal()
    result.mu_optimal = anchor_ref + (result.mu_optimal - anchor_opt)


def _optimize_vessel_speed(vessel: Vessel,
                           maximum_change: float,
                           idx: int,
                           ) -> SpeedResult:
    """
    Compute the individually optimal mean speed for a vessel.

    The method calculates the speed that will yield the lowest freight-cost for the vessel, assuming that a lower
    speed can be offset by chartering additional vessels and thus yielding an optimal freight-cost across a fleet,
    not a single vessel.

    Parameters
    ----------
    vessel
        Vessel for which the optimal speed is calculated.
    maximum_change
        Maximum allowed change in mean speed (up or down).
    idx
        Current time-step index.

    Returns
    -------
    SpeedResult
        Intermediate optimization result.
    """

    # calculate the reference deltas based
    # on the route's speed distribution
    deltas_ref, distribution, speeds_reference = _calculate_reference_speed_deltas(vessel)

    expectation = vessel.expectation

    # the reference mean speed (excluding distribution weighting)
    # is used as the reference point for updating the actual speed
    mu_ref = expectation.get_speed_mean()
    if np.isnan(mu_ref):
        # if the mean speed has not been previously assigned,
        # use the distribution weighted reference speed instead
        speeds_current = expectation.get_speeds(idx)
        mu_ref = float(np.average(speeds_current, weights=distribution))

    # calculate the bounds that are applied to truncate
    # the distribution of speeds if they become infeasible
    speed_min, speed_max = calculate_technical_speed_limits(vessel)
    mu_low, mu_high = calculate_speed_bounds(speed_min, speed_max, speeds_reference)

    fuel_ref = expectation.get_total_fuel_expenses(idx)
    charter_rate = expectation.get_asset_charter_rate(idx)
    savings_sea = expectation.get_energy_saving_sea(idx)
    savings_port = expectation.get_energy_saving_port(idx)

    # pre-compute operational saving factors outside the objective closure
    saving_fraction_sea = expectation.get_operational_saving_fraction_sea()
    saving_fraction_port = expectation.get_operational_saving_fraction_port()
    factor_sea = {d: 1. - saving_fraction_sea[d] for d in saving_fraction_sea}
    factor_port = {d: 1. - saving_fraction_port[d] for d in saving_fraction_port}

    # smoothed scarcity duals are constant across objective evaluations,
    # so compute them once outside the closure
    smoothed_duals = get_smoothed_energy_duals_speed(vessel)

    def objective(mu: float) -> float:

        # calculate the operational profile based on the mean speed
        speeds = _mean_to_speeds(mu, deltas_ref, speed_min, speed_max)
        operations = calculate_operational_profile(vessel, speeds)

        # apply operational savings (JIT, weather routing, etc.) to the
        # freshly computed energy before applying technology savings
        energy_sea = {d: [e * factor_sea[d] for e in operations.energy_sea[d]]
                      for d in operations.energy_sea}
        energy_port = {d: [e * factor_port[d] for e in operations.energy_port[d]]
                       for d in operations.energy_port}

        # the energy needs to account for the impact of the current
        # technology uptake since the comparison occurs relative to
        # the energy used during the call to expected bunkering.
        # Notice this does not use an exact heuristic since external
        # power has a higher proportional impact at lower speeds
        residual_energy_sea = net_energy_from_raw(energy_sea, savings_sea)
        residual_energy_port = net_energy_from_raw(energy_port, savings_port)

        # calculate the residual fuel cost after
        # accounting for the saved amount
        fuel_saving = calculate_marginal_speed_saving(vessel,
                                                      residual_energy_sea,
                                                      residual_energy_port,
                                                      idx,
                                                      smoothed_duals=smoothed_duals)

        fuel_cost = fuel_ref - fuel_saving

        return (fuel_cost + charter_rate) / operations.cargo_miles

    sol = minimize_scalar(
        objective,
        bounds=(mu_low, mu_high),
        method="bounded",
        options={"xatol": 0.1}
    )

    mu_optimal = float(sol.x)

    return SpeedResult(
        vessel=vessel,
        mu_ref=mu_ref,
        mu_optimal=mu_optimal,
        deltas_ref=deltas_ref,
        speed_min=speed_min,
        speed_max=speed_max,
        distribution=distribution,
        maximum_change=maximum_change,
    )


def _finalize_vessel_speed(result: SpeedResult,
                           mu_target: float,
                           idx: int
                           ) -> None:
    """
    Apply the target mean speed to a vessel, transfer the operational profile, and store results.

    Parameters
    ----------
    result
        Intermediate optimization result from _optimize_vessel_speed.
    mu_target
        Target mean speed to apply (may differ from the individual optimum due to alignment).
    idx
        Current time-step index.
    """

    vessel = result.vessel
    mu_actual = _update_mean_speed(result.mu_ref, mu_target, result.maximum_change)

    # realized per-leg speeds at idx
    speeds_actual = _mean_to_speeds(mu_actual, result.deltas_ref, result.speed_min, result.speed_max)
    speeds_optimal = _mean_to_speeds(mu_target, result.deltas_ref, result.speed_min, result.speed_max)

    # transfer the updated operational
    # profile to expectations and profile
    operations_actual = calculate_operational_profile(vessel, speeds_actual)
    transfer_operational_profile(vessel, operations_actual, idx)
    vessel.expectation.set_speed_mean(mu_actual)

    # transfer speed management results to profile
    profile = vessel.profile
    profile.set_minimum_speed(idx, np.min(result.speed_min))
    profile.set_maximum_speed(idx, np.max(result.speed_max))
    profile.set_actual_speed(idx, np.average(speeds_actual, weights=result.distribution))
    profile.set_optimal_speed(idx, np.average(speeds_optimal, weights=result.distribution))
    profile.set_lowest_speed(idx, np.min(speeds_actual))
    profile.set_highest_speed(idx, np.max(speeds_actual))

    # the method 'minimize_scalar' assumes the objective function
    # is reasonably well-behaved over the interval. Predominantly
    # this means that it works best when the function is unimodal.
    # This will most likely be the case if the load functions are
    # convex. So, a warning is issued if they are not
    if not loads_are_convex(vessel):
        logger.warning(f"{vessel}: Does not have convex load functions which may lead to suboptimal speed management results.")


def _calculate_reference_speed_deltas(vessel: Vessel) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate the reference speed deltas per leg based on the route's speed distribution.

    Notice that this can be different from the current speed per leg (as an output from the previous speed management
    optimization) since speeds are truncated to the technical limits of the propulsion engine. The route's reference
    speed distribution is used as the correct speed envelope because it best reflects the assumptions passed by the user.

    Parameters
    ----------
    vessel
        Vessel for which the reference speed deltas are calculated.

    Returns
    -------
    tuple[np.ndarray, np.ndarray, np.ndarray]
        Speed deltas per leg, distribution of time spent at each leg, expected speeds at each leg.
    """

    speeds_reference = to_numpy(vessel.route.speeds)

    # calculate an operational profile in order to
    # access the condition distribution of the route
    operations = calculate_operational_profile(vessel, speeds_reference)

    speed_mean = np.average(speeds_reference, weights=operations.distribution)
    deltas = speeds_reference - speed_mean

    return deltas, operations.distribution, speeds_reference


def _mean_to_speeds(mu: float,
                    deltas_ref: np.ndarray,
                    speeds_min: np.ndarray,
                    speeds_max: np.ndarray
                    ) -> np.ndarray:
    """
    Convert the mean speed into a speed per leg based on the reference speed deltas.
    The speeds per leg adheres to the given minimum and maximum speeds.

    Parameters
    ----------
    mu
        Mean speed.
    deltas_ref
        Speed deltas per leg relative to the mean speed.
    speeds_min
        Minimum allowed speed per leg.
    speeds_max
        Maximum allowed speed per leg.

    Returns
    -------
    np.ndarray
        Speed per leg.
    """

    return np.clip(mu + deltas_ref, speeds_min, speeds_max)


def _update_mean_speed(mu_ref: float, mu_target: float, maximum_change: float) -> float:
    """
    Based on the current (reference) mean speed and the target mean speed, update the actual mean speed while
    accounting for the maximum possible change in either direction.

    Parameters
    ----------
    mu_ref
        Reference mean speed.
    mu_target
        Target mean speed.
    maximum_change
        Maximum allowed change in mean speed (up or down).

    Returns
    -------
    float
        Updated mean speed.
    """
    step = float(np.clip(mu_target - mu_ref, -maximum_change, +maximum_change))
    return mu_ref + step
