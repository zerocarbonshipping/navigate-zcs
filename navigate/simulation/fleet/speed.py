# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Speed management: each vessel's cost-optimal mean speed and the fleet's alignment."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from scipy.optimize import minimize_scalar

from navigate.core.enum_ import SpeedAlignmentID
from navigate.simulation.fleet.cohort import get_multipliers
from navigate.simulation.fleet.marginal_saving import calculate_marginal_speed_saving
from navigate.simulation.fleet.operation import (
    calculate_operations,
    transfer_operational_savings,
    transfer_operations,
)
from navigate.simulation.fleet.power import (
    calculate_speed_bounds,
    calculate_technical_speed_limits,
    loads_are_convex,
)
from navigate.simulation.fleet.residual_energy import calculate_net_energy
from navigate.simulation.fleet.trip import ReferenceTrip, derive_reference_trip
from navigate.util import YEAR

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)


@dataclass
class SpeedResult:
    """
    One vessel's individually optimized speed, before the fleet aligns it.

    Parameters
    ----------
    vessel
        Vessel whose speed is optimized.
    trip
        Reference trip of the vessel's route in this time-step.
    mu_ref
        Mean speed the actual speed moves from, knots.
    mu_optimal
        Optimal mean speed, knots.
    deltas_ref
        Speed in each condition relative to the mean speed, knots.
    speed_min
        Technical minimum speed in each condition, knots.
    speed_max
        Technical maximum speed in each condition, knots.
    distribution
        Share of the sea time in each condition, fraction.
    maximum_change
        Largest change of the mean speed in this time-step, knots.
    """

    vessel: Vessel
    trip: ReferenceTrip
    mu_ref: float = 0.0
    mu_optimal: float = 0.0
    deltas_ref: FloatArray = field(default_factory=lambda: np.empty(0))
    speed_min: FloatArray = field(default_factory=lambda: np.empty(0))
    speed_max: FloatArray = field(default_factory=lambda: np.empty(0))
    distribution: FloatArray = field(default_factory=lambda: np.empty(0))
    maximum_change: float = 0.0


def perform_speed_management(fleet: Fleet, time_step: float, idx: int) -> None:
    """
    Dynamically update each vessel's speed in the fleet if speed management is allowed.

    Vessel speeds are first individually optimized and then aligned across vessels
    according to the fleet's speed alignment method.

    Parameters
    ----------
    fleet
        Fleet for which speed management is performed.
    time_step
        Current time-step size, days.
    idx
        Current time-step index.
    """
    if not fleet.allow_speed_management:
        return

    maximum_change = fleet.maximum_speed_change.get() * time_step / YEAR
    alignment = fleet.speed_alignment

    transfer_operational_savings(fleet)

    results = [
        _optimize_vessel_speed(vessel, maximum_change, idx) for vessel in fleet.vessels
    ]

    if fleet.assume_reference_speed_optimal:
        for result in results:
            anchor_ref = result.vessel.expectation.get_speed_anchor_reference()
            if np.isnan(anchor_ref):
                _initialize_speed_anchor(result)
            else:
                _shift_speed_to_anchor(result)

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
            weights = get_multipliers(fleet)
            mu_aligned = float(np.average(mu_values, weights=weights))

        else:
            raise ValueError(f"Unknown speed alignment method: {alignment}")

        for result in results:
            _finalize_vessel_speed(result, mu_aligned, idx)


def _initialize_speed_anchor(result: SpeedResult) -> None:
    """
    Store the initial route reference speed and modelled optimal speed as anchors.

    The route reference speed is used as the target for the first time-step (no change
    from the reference). Both values are stored on the vessel expectation for use in
    subsequent time-steps by :func:`_shift_speed_to_anchor`.

    Parameters
    ----------
    result
        SpeedResult from individual optimization.
    """
    mu_route = float(np.average(result.trip.speeds, weights=result.distribution))

    expectation = result.vessel.expectation
    expectation.set_speed_anchor_reference(mu_route)
    expectation.set_speed_anchor_optimal(result.mu_optimal)
    result.mu_optimal = mu_route


def _shift_speed_to_anchor(result: SpeedResult) -> None:
    """
    Shift the optimal speed relative to the stored anchor values.

    The adjusted target is: mu_ref_initial + (mu_optimal - mu_optimal_initial), so speed
    only changes if the modelled optimum has shifted relative to its initial value.

    Parameters
    ----------
    result
        SpeedResult from individual optimization.
    """
    expectation = result.vessel.expectation
    anchor_ref = expectation.get_speed_anchor_reference()
    anchor_opt = expectation.get_speed_anchor_optimal()
    result.mu_optimal = anchor_ref + (result.mu_optimal - anchor_opt)


def _optimize_vessel_speed(
    vessel: Vessel,
    maximum_change: float,
    idx: int,
) -> SpeedResult:
    """
    Calculate a vessel's individually optimal mean speed.

    The optimum minimizes the freight cost per cargo-mile, on the assumption that the
    trade lost to a lower speed is made up by chartering more vessels, so it is the
    optimum across the fleet rather than for one vessel.

    Parameters
    ----------
    vessel
        Vessel whose optimal speed is calculated.
    maximum_change
        Largest change of the mean speed in this time-step, up or down, knots.
    idx
        Current time-step index.

    Returns
    -------
    SpeedResult
        Intermediate optimization result.
    """
    trip = derive_reference_trip(vessel.route)
    deltas_ref, distribution = _calculate_reference_speed_deltas(vessel, trip)

    expectation = vessel.expectation

    # the actual speed moves from the mean speed set at the previous time-step
    mu_ref = expectation.get_speed_mean()
    if np.isnan(mu_ref):
        # before a mean speed is first set, the distribution-weighted current speed
        # stands in
        speeds_current = np.array(expectation.get_speeds_condition(idx), dtype=float)
        mu_ref = float(np.average(speeds_current, weights=distribution))

    # the technical limits truncate each condition's speed, and those of the
    # conditions that take sea time bound the mean speed
    sailed = trip.sailed
    speed_min, speed_max = calculate_technical_speed_limits(vessel, trip)
    mu_low, mu_high = calculate_speed_bounds(
        speed_min[sailed], speed_max[sailed], trip.speeds[sailed]
    )

    fuel_ref = float(expectation.get_total_fuel_expenses(idx))
    charter_rate = expectation.get_asset_charter_rate(idx)
    savings_sea = expectation.get_energy_saving_sea_condition(idx)
    savings_port = expectation.get_energy_saving_port(idx)

    # pre-compute operational saving factors outside the objective closure
    saving_fraction_sea = expectation.get_operational_saving_fraction_sea()
    saving_fraction_port = expectation.get_operational_saving_fraction_port()
    factor_sea = {d: 1.0 - saving_fraction_sea[d] for d in saving_fraction_sea}
    factor_port = {d: 1.0 - saving_fraction_port[d] for d in saving_fraction_port}

    def objective(mu: float) -> float:
        speeds = _mean_to_speeds(mu, deltas_ref, speed_min, speed_max)
        operations = calculate_operations(vessel, trip, speeds)

        # apply operational savings (JIT, weather routing, etc.) to the
        # freshly computed energy before applying technology savings
        energy_sea = {
            d: [e * factor_sea[d] for e in operations.energy_sea[d]]
            for d in operations.energy_sea
        }
        energy_port = {
            d: [e * factor_port[d] for e in operations.energy_port[d]]
            for d in operations.energy_port
        }

        # the current technology uptake is applied, as the saving is measured from
        # the energy of the expected bunkering; the proportional savings are an
        # approximation, since external power has a larger share at lower speeds
        residual_energy_sea = calculate_net_energy(energy_sea, savings_sea)
        residual_energy_port = calculate_net_energy(energy_port, savings_port)

        fuel_saving = calculate_marginal_speed_saving(
            vessel,
            trip.condition_legs,
            residual_energy_sea,
            residual_energy_port,
            idx,
        )

        fuel_cost = fuel_ref - fuel_saving

        return (fuel_cost + charter_rate) / operations.cargo_miles

    sol = minimize_scalar(
        objective, bounds=(mu_low, mu_high), method="bounded", options={"xatol": 0.1}
    )

    mu_optimal = float(sol.x)

    return SpeedResult(
        vessel=vessel,
        trip=trip,
        mu_ref=mu_ref,
        mu_optimal=mu_optimal,
        deltas_ref=deltas_ref,
        speed_min=speed_min,
        speed_max=speed_max,
        distribution=distribution,
        maximum_change=maximum_change,
    )


def _finalize_vessel_speed(result: SpeedResult, mu_target: float, idx: int) -> None:
    """
    Apply the target mean speed to a vessel, transfer the profile, and store results.

    Parameters
    ----------
    result
        Intermediate optimization result from _optimize_vessel_speed.
    mu_target
        Target mean speed, knots; the fleet alignment may move it from the individual
        optimum.
    idx
        Current time-step index.
    """
    vessel = result.vessel
    mu_actual = _update_mean_speed(result.mu_ref, mu_target, result.maximum_change)

    speeds_actual = _mean_to_speeds(
        mu_actual, result.deltas_ref, result.speed_min, result.speed_max
    )
    speeds_optimal = _mean_to_speeds(
        mu_target, result.deltas_ref, result.speed_min, result.speed_max
    )

    operations_actual = calculate_operations(vessel, result.trip, speeds_actual)
    transfer_operations(vessel, result.trip, operations_actual, idx)
    vessel.expectation.set_speed_mean(mu_actual)

    distribution = result.distribution
    sailed = result.trip.sailed

    profile = vessel.profile
    profile.set_minimum_speed(idx, np.min(result.speed_min[sailed]))
    profile.set_maximum_speed(idx, np.max(result.speed_max[sailed]))
    profile.set_actual_speed(idx, np.average(speeds_actual, weights=distribution))
    profile.set_optimal_speed(idx, np.average(speeds_optimal, weights=distribution))
    profile.set_lowest_speed(idx, np.min(speeds_actual[sailed]))
    profile.set_highest_speed(idx, np.max(speeds_actual[sailed]))

    # minimize_scalar works best on a unimodal objective, which convex load
    # functions make likely
    if not loads_are_convex(vessel):
        logger.warning(
            "%s: Does not have convex load functions which may lead to suboptimal "
            "speed management results.",
            vessel,
        )


def _calculate_reference_speed_deltas(
    vessel: Vessel, trip: ReferenceTrip
) -> tuple[FloatArray, FloatArray]:
    """
    Calculate each condition's reference speed relative to the mean reference speed.

    The deltas come from the route's reference speeds, which reflect the user's
    assumptions, and not from the current speeds, which speed management has
    truncated to the propulsion engine's technical limits.

    Parameters
    ----------
    vessel
        Vessel for which the reference speed deltas are calculated.
    trip
        Reference trip of the vessel's route.

    Returns
    -------
    tuple[FloatArray, FloatArray]
        Speed delta in each condition, knots, and share of the sea time in each
        condition at the reference speeds, fraction.
    """
    operations = calculate_operations(vessel, trip, trip.speeds)

    speed_mean = np.average(trip.speeds, weights=operations.distribution)
    deltas = trip.speeds - speed_mean

    return deltas, operations.distribution


def _mean_to_speeds(
    mu: float, deltas_ref: FloatArray, speeds_min: FloatArray, speeds_max: FloatArray
) -> FloatArray:
    """
    Convert a mean speed to a speed per condition, within the speed limits.

    Parameters
    ----------
    mu
        Mean speed, knots.
    deltas_ref
        Speed in each condition relative to the mean speed, knots.
    speeds_min
        Minimum allowed speed in each condition, knots.
    speeds_max
        Maximum allowed speed in each condition, knots.

    Returns
    -------
    FloatArray
        Speed in each condition, knots.
    """
    return np.clip(mu + deltas_ref, speeds_min, speeds_max)


def _update_mean_speed(mu_ref: float, mu_target: float, maximum_change: float) -> float:
    """
    Move the mean speed towards the target by at most the maximum change.

    Parameters
    ----------
    mu_ref
        Mean speed the move starts from, knots.
    mu_target
        Target mean speed, knots.
    maximum_change
        Largest change of the mean speed, up or down, knots.

    Returns
    -------
    float
        Updated mean speed, knots.
    """
    step = float(np.clip(mu_target - mu_ref, -maximum_change, +maximum_change))
    return mu_ref + step
