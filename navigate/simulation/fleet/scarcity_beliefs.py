# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Smoothed shadow-price beliefs of each vessel and the investment signals from them."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.util import calculate_smoothing_alpha, update_belief_path

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence

    from navigate.core.enum_ import EnergyDemandID
    from navigate.core.expectations import VesselExpectation
    from navigate.core.nodes.fleet import Fleet
    from navigate.util.types_ import FloatArray


type _LegPaths = Mapping[EnergyDemandID, Sequence[FloatArray]]
type _SeaPortPaths = tuple[_LegPaths, _LegPaths]


def update_vessel_scarcity_beliefs(
    fleets: dict[str, Fleet], timeline: FloatArray, idx: int
) -> None:
    """
    Update every vessel's per-leg shadow-price beliefs.

    Each (energy-demand-type, leg) array of LP duals is smoothed on its own by an
    exponential moving average, in place on the expectation's belief arrays. A slower
    belief serves technology decisions, amortised over `technology_horizon`, and a
    faster one operational speed management, over `speed_horizon`. Smoothing each leg
    on its own keeps the LP's structure across legs, where shadow prices may differ
    in sign and magnitude, while damping each leg's year-to-year volatility.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    for fleet in fleets.values():
        technology_horizon = fleet.technology_horizon.get()
        speed_horizon = fleet.speed_horizon.get()

        alpha_technology = calculate_smoothing_alpha(technology_horizon, timeline, idx)
        alpha_speed = calculate_smoothing_alpha(speed_horizon, timeline, idx)

        for vessel in fleet.vessels:
            expectation = vessel.expectation

            raw = (
                expectation.get_energy_conservation_pi_sea(),
                expectation.get_energy_conservation_pi_port(),
            )
            technology, speed = _beliefs(expectation)

            for raw_leg, belief_leg in _zip_legs(raw, technology):
                update_belief_path(raw_leg, belief_leg, alpha_technology, idx)

            for raw_leg, belief_leg in _zip_legs(raw, speed):
                update_belief_path(raw_leg, belief_leg, alpha_speed, idx)


def record_investment_signals(fleets: dict[str, Fleet], idx: int) -> None:
    """
    Store each vessel's investment signal: its beliefs' energy-weighted average dual.

    The technology and speed beliefs each give one signal, in USD/GJ, written to the
    vessel results for output.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.
    """
    for fleet in fleets.values():
        for vessel in fleet.vessels:
            expectation = vessel.expectation
            results = vessel.results

            rhs = (
                expectation.get_energy_conservation_rhs_sea(),
                expectation.get_energy_conservation_rhs_port(),
            )
            technology, speed = _beliefs(expectation)

            signal_technology = _average_dual(technology, rhs, idx)
            signal_speed = _average_dual(speed, rhs, idx)

            results.investment_signal_technology[idx] = signal_technology
            results.investment_signal_speed[idx] = signal_speed


def _beliefs(expectation: VesselExpectation) -> tuple[_SeaPortPaths, _SeaPortPaths]:
    """Return a vessel's technology and speed beliefs, each at sea and in port."""
    technology = (
        expectation.get_belief_pi_sea_technology(),
        expectation.get_belief_pi_port_technology(),
    )
    speed = (
        expectation.get_belief_pi_sea_speed(),
        expectation.get_belief_pi_port_speed(),
    )
    return technology, speed


def _zip_legs(
    first: _SeaPortPaths, second: _SeaPortPaths
) -> Iterator[tuple[FloatArray, FloatArray]]:
    """Pair the leg paths of two quantities alike in shape, at sea then in port."""
    for first_side, second_side in zip(first, second, strict=True):
        for energy_id, first_legs in first_side.items():
            yield from zip(first_legs, second_side[energy_id], strict=True)


def _average_dual(beliefs: _SeaPortPaths, rhs: _SeaPortPaths, idx: int) -> float:
    """
    Collapse the per-(energy-type, leg) belief duals into one energy-weighted average.

    Each leg and port dual is weighted by its energy-conservation RHS, the energy
    demand it prices, so the result is the marginal value of energy the vessel faces.

    Parameters
    ----------
    beliefs
        Smoothed duals at sea and in port, per energy demand type and leg or port, in
        USD/GJ.
    rhs
        Energy-conservation RHS at sea and in port, shaped as `beliefs`, in GJ/year.
    idx
        Current time-step index.

    Returns
    -------
    float
        Energy-weighted average dual, in USD/GJ, or ``np.nan`` when there is no
        demand.
    """
    weighted_sum = 0.0
    weight_total = 0.0

    for belief_leg, rhs_leg in _zip_legs(beliefs, rhs):
        weight = rhs_leg[idx]
        weighted_sum += belief_leg[idx] * weight
        weight_total += weight

    if weight_total <= 0.0:
        return np.nan

    return weighted_sum / weight_total
