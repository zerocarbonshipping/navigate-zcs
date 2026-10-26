# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Speed management: each vessel's cost-optimal mean speed and the fleet's alignment."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from scipy.optimize import minimize_scalar

from navigate.core.enum_ import SpeedAlignmentID
from navigate.simulation.fleet._composition import get_multipliers
from navigate.simulation.fleet._marginal_saving import calculate_marginal_speed_saving
from navigate.simulation.fleet._residual_energy import (
    calculate_energy_savings,
    calculate_net_energy,
    scale_per_key,
)
from navigate.simulation.fleet._trip import ReferenceTrip, derive_reference_trip
from navigate.simulation.fleet.charter import calculate_fuel_and_policy_expenses
from navigate.simulation.fleet.operation import (
    calculate_operations,
    transfer_operational_savings,
    transfer_operations,
)
from navigate.simulation.fleet.power import (
    calculate_mean_speed_bounds,
    calculate_technical_speed_limits,
    loads_are_convex,
)
from navigate.util import YEAR

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)


@dataclass
class _SpeedResult:
    """
    One vessel's individually optimized speed, before the fleet aligns it.

    Parameters
    ----------
    vessel
        Vessel whose speed is optimized.
    trip
        Reference trip of the vessel's route in this time-step.
    mu_route
        Mean of the route's reference speeds, in knots.
    mu_ref
        Mean speed the actual speed moves from, in knots.
    mu_optimal
        Optimal mean speed, in knots.
    deltas_ref
        Speed in each condition relative to the mean speed, in knots.
    speeds_min
        Technical minimum speed in each condition, in knots.
    speeds_max
        Technical maximum speed in each condition, in knots.
    distribution
        Share of the sea time in each condition, fraction.
    """

    vessel: Vessel
    trip: ReferenceTrip
    mu_route: float
    mu_ref: float
    mu_optimal: float
    deltas_ref: FloatArray
    speeds_min: FloatArray
    speeds_max: FloatArray
    distribution: FloatArray


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
        Current time-step size, in days.
    idx
        Current time-step index.
    """
    if not fleet.allow_speed_management:
        return

    transfer_operational_savings(fleet)
    results = [_optimize_vessel_speed(vessel, idx) for vessel in fleet.vessels]

    if fleet.assume_reference_speed_optimal:
        for result in results:
            result.mu_optimal = _anchor_speed(result)

    mu_targets = _align_speeds(fleet, [result.mu_optimal for result in results])
    maximum_change = fleet.maximum_speed_change.get() * time_step / YEAR

    for result, mu_target in zip(results, mu_targets, strict=True):
        _finalize_vessel_speed(result, mu_target, maximum_change, idx)


def _optimize_vessel_speed(vessel: Vessel, idx: int) -> _SpeedResult:
    """
    Calculate a vessel's individually optimal mean speed.

    The optimum minimizes the freight cost per cargo-mile, on the assumption that the
    trade lost to a lower speed is made up by chartering more vessels, so it is the
    optimum across the fleet rather than for one vessel.

    Parameters
    ----------
    vessel
        Vessel whose optimal speed is calculated.
    idx
        Current time-step index.

    Returns
    -------
    _SpeedResult
        Intermediate optimization result.
    """
    trip = derive_reference_trip(vessel.route)
    legs = trip.condition_legs
    expectation = vessel.expectation

    # the deltas come from the route's reference speeds, which reflect the user's
    # assumptions, and not from the current speeds, which speed management has
    # truncated to the propulsion engine's technical limits
    distribution = calculate_operations(vessel, trip, trip.speeds).distribution
    mu_route = float(np.average(trip.speeds, weights=distribution))
    deltas_ref = trip.speeds - mu_route

    # the actual speed moves from the mean speed set at the previous time-step; before
    # one is first set, the distribution-weighted current speed stands in
    mu_ref = expectation.get_speed_mean()
    if np.isnan(mu_ref):
        speeds_current = np.array(expectation.get_speeds_condition(idx), dtype=float)
        mu_ref = float(np.average(speeds_current, weights=distribution))

    # the technical limits truncate each condition's speed, and those of the
    # conditions that take sea time bound the mean speed
    sailed = trip.sailed
    speeds_min, speeds_max = calculate_technical_speed_limits(vessel, trip)
    mu_low, mu_high = calculate_mean_speed_bounds(
        speeds_min[sailed], speeds_max[sailed], trip.speeds[sailed]
    )

    fuel_ref = float(calculate_fuel_and_policy_expenses(vessel, idx))
    charter_rate = expectation.get_asset_charter_rate(idx)

    energy_sea_ref = expectation.get_energy_sea_condition(idx)
    energy_port_ref = expectation.get_energy_port(idx)
    raw_energy_sea = expectation.get_raw_energy_sea_condition(idx)
    raw_energy_port = expectation.get_raw_energy_port(idx)

    savings_sea = calculate_energy_savings(energy_sea_ref, raw_energy_sea)
    savings_port = calculate_energy_savings(energy_port_ref, raw_energy_port)

    fractions_sea = expectation.get_operational_saving_fraction_sea()
    fractions_port = expectation.get_operational_saving_fraction_port()

    remaining_sea = {key: 1.0 - value for key, value in fractions_sea.items()}
    remaining_port = {key: 1.0 - value for key, value in fractions_port.items()}

    def objective(mu: float) -> float:
        speeds = _mean_to_speeds(mu, deltas_ref, speeds_min, speeds_max)
        operations = calculate_operations(vessel, trip, speeds)

        # the operational savings (JIT, weather routing, etc.) apply to the freshly
        # computed energy, before the technology savings
        energy_sea = scale_per_key(operations.energy_sea, remaining_sea)
        energy_port = scale_per_key(operations.energy_port, remaining_port)

        # the current technology uptake is applied, as the saving is measured from
        # the energy of the expected bunkering; the proportional savings are an
        # approximation, since external power has a larger share at lower speeds
        net_sea = calculate_net_energy(energy_sea, savings_sea)
        net_port = calculate_net_energy(energy_port, savings_port)

        saving = calculate_marginal_speed_saving(vessel, legs, net_sea, net_port, idx)

        return (fuel_ref - saving + charter_rate) / operations.cargo_miles

    solution = minimize_scalar(
        objective, bounds=(mu_low, mu_high), method="bounded", options={"xatol": 0.1}
    )

    # minimize_scalar works best on a unimodal objective, which convex load
    # functions make likely
    if not loads_are_convex(vessel):
        logger.warning(
            "%s: Does not have convex load functions which may lead to suboptimal "
            "speed management results.",
            vessel,
        )

    return _SpeedResult(
        vessel=vessel,
        trip=trip,
        mu_route=mu_route,
        mu_ref=mu_ref,
        mu_optimal=float(solution.x),
        deltas_ref=deltas_ref,
        speeds_min=speeds_min,
        speeds_max=speeds_max,
        distribution=distribution,
    )


def _anchor_speed(result: _SpeedResult) -> float:
    """
    Anchor a vessel's optimal mean speed to the mean of its route's reference speeds.

    The route's reference speeds are assumed optimal when the anchors are first stored,
    so the modelled optimum only moves the speed by how far it has shifted since then:
    the anchored speed is anchor_ref + (mu_optimal - anchor_opt). The first call stores
    the route's mean speed and the current optimum as the anchors, so it returns the
    route's mean speed.

    Parameters
    ----------
    result
        Intermediate optimization result of the vessel.

    Returns
    -------
    float
        Anchored optimal mean speed, in knots.
    """
    expectation = result.vessel.expectation

    if np.isnan(expectation.get_speed_anchor_reference()):
        expectation.set_speed_anchor_reference(result.mu_route)
        expectation.set_speed_anchor_optimal(result.mu_optimal)

    anchor_ref = expectation.get_speed_anchor_reference()
    anchor_opt = expectation.get_speed_anchor_optimal()

    return anchor_ref + (result.mu_optimal - anchor_opt)


def _align_speeds(fleet: Fleet, mu_values: list[float]) -> list[float]:
    """
    Align the vessels' optimal mean speeds by the fleet's speed alignment method.

    Parameters
    ----------
    fleet
        Fleet whose vessels' speeds are aligned.
    mu_values
        Optimal mean speed of each vessel, in knots.

    Returns
    -------
    list[float]
        Target mean speed of each vessel, in knots.
    """
    match fleet.speed_alignment:
        case SpeedAlignmentID.INDIVIDUAL:
            return mu_values

        case SpeedAlignmentID.MINIMUM:
            mu_aligned = min(mu_values)

        case SpeedAlignmentID.MAXIMUM:
            mu_aligned = max(mu_values)

        case SpeedAlignmentID.AVERAGE:
            mu_aligned = float(np.average(mu_values, weights=get_multipliers(fleet)))

        case _:
            raise ValueError(f"Unknown speed alignment method: {fleet.speed_alignment}")

    return [mu_aligned] * len(mu_values)


def _finalize_vessel_speed(
    result: _SpeedResult, mu_target: float, maximum_change: float, idx: int
) -> None:
    """
    Move a vessel's mean speed towards the target, transfer its results, store results.

    Parameters
    ----------
    result
        Intermediate optimization result of the vessel.
    mu_target
        Target mean speed, in knots; the fleet alignment may move it from the
        individual optimum.
    maximum_change
        Largest change of the mean speed in this time-step, up or down, in knots.
    idx
        Current time-step index.
    """
    vessel = result.vessel
    trip = result.trip
    sailed = trip.sailed
    distribution = result.distribution

    mu_ref = result.mu_ref
    deltas_ref = result.deltas_ref
    speeds_min = result.speeds_min
    speeds_max = result.speeds_max

    change = float(np.clip(mu_target - mu_ref, -maximum_change, maximum_change))
    mu_actual = mu_ref + change

    speeds_actual = _mean_to_speeds(mu_actual, deltas_ref, speeds_min, speeds_max)
    speeds_optimal = _mean_to_speeds(mu_target, deltas_ref, speeds_min, speeds_max)

    operations_actual = calculate_operations(vessel, trip, speeds_actual)
    transfer_operations(vessel, trip, operations_actual, idx)
    vessel.expectation.set_speed_mean(mu_actual)

    results = vessel.results
    results.minimum_speed[idx] = np.min(speeds_min[sailed])
    results.maximum_speed[idx] = np.max(speeds_max[sailed])
    results.actual_speed[idx] = np.average(speeds_actual, weights=distribution)
    results.optimal_speed[idx] = np.average(speeds_optimal, weights=distribution)
    results.lowest_speed[idx] = np.min(speeds_actual[sailed])
    results.highest_speed[idx] = np.max(speeds_actual[sailed])


def _mean_to_speeds(
    mu: float, deltas_ref: FloatArray, speeds_min: FloatArray, speeds_max: FloatArray
) -> FloatArray:
    """
    Convert a mean speed to a speed per condition, within the speed limits.

    Parameters
    ----------
    mu
        Mean speed, in knots.
    deltas_ref
        Speed in each condition relative to the mean speed, in knots.
    speeds_min
        Minimum allowed speed in each condition, in knots.
    speeds_max
        Maximum allowed speed in each condition, in knots.

    Returns
    -------
    FloatArray
        Speed in each condition, in knots.
    """
    return np.clip(mu + deltas_ref, speeds_min, speeds_max)
