# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Smoothed shadow-price beliefs of each vessel and the investment signals from them."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.util import derive_smoothing_alpha, update_belief_path

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from navigate.core.enum_ import EnergyDemandTypeID
    from navigate.core.nodes.fleet import Fleet
    from navigate.util.types_ import FloatArray


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
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    for fleet in fleets.values():
        tech_horizon = fleet.technology_horizon.get()
        speed_horizon = fleet.speed_horizon.get()

        alpha_tech = derive_smoothing_alpha(idx, tech_horizon, timeline)
        alpha_speed = derive_smoothing_alpha(idx, speed_horizon, timeline)

        for vessel in fleet.vessels:
            expectation = vessel.expectation

            raw_pi_sea = expectation.get_energy_conservation_pi_sea()
            raw_pi_port = expectation.get_energy_conservation_pi_port()

            _smooth_pi_dict(
                raw_pi_sea, expectation.get_belief_pi_sea_technology(), alpha_tech, idx
            )
            _smooth_pi_dict(
                raw_pi_port,
                expectation.get_belief_pi_port_technology(),
                alpha_tech,
                idx,
            )
            _smooth_pi_dict(
                raw_pi_sea, expectation.get_belief_pi_sea_speed(), alpha_speed, idx
            )
            _smooth_pi_dict(
                raw_pi_port, expectation.get_belief_pi_port_speed(), alpha_speed, idx
            )


def record_investment_signals(fleets: dict[str, Fleet], idx: int) -> None:
    """
    Store each vessel's investment signal: its beliefs' energy-weighted average dual.

    The technology and speed beliefs each give one signal, USD/GJ, written to the
    vessel profile for output.

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

            rhs_sea = expectation.get_energy_conservation_rhs_sea()
            rhs_port = expectation.get_energy_conservation_rhs_port()

            signal_technology = _energy_weighted_signal(
                expectation.get_belief_pi_sea_technology(),
                expectation.get_belief_pi_port_technology(),
                rhs_sea,
                rhs_port,
                idx,
            )
            signal_speed = _energy_weighted_signal(
                expectation.get_belief_pi_sea_speed(),
                expectation.get_belief_pi_port_speed(),
                rhs_sea,
                rhs_port,
                idx,
            )

            profile = vessel.profile
            profile.set_investment_signal_technology(idx, signal_technology)
            profile.set_investment_signal_speed(idx, signal_speed)


def _energy_weighted_signal(
    belief_sea: Mapping[EnergyDemandTypeID, Sequence[FloatArray]],
    belief_port: Mapping[EnergyDemandTypeID, Sequence[FloatArray]],
    rhs_sea: Mapping[EnergyDemandTypeID, Sequence[FloatArray]],
    rhs_port: Mapping[EnergyDemandTypeID, Sequence[FloatArray]],
    idx: int,
) -> float:
    """
    Collapse the per-(energy-type, leg) belief duals into one energy-weighted average.

    Each leg and port dual is weighted by its energy-conservation RHS, the energy
    demand it prices, so the result is the marginal value of energy the vessel faces.

    Parameters
    ----------
    belief_sea
        Smoothed duals at sea per energy demand type and leg, USD/GJ.
    belief_port
        Smoothed duals in port per energy demand type and port, USD/GJ.
    rhs_sea
        Energy-conservation RHS at sea, shaped as `belief_sea`, GJ/year.
    rhs_port
        Energy-conservation RHS in port, shaped as `belief_port`, GJ/year.
    idx
        Current time-step index.

    Returns
    -------
    float
        Energy-weighted average dual, USD/GJ, or ``np.nan`` when there is no demand.
    """
    weighted_sum = 0.0
    weight_total = 0.0

    for belief_dict, rhs_dict in ((belief_sea, rhs_sea), (belief_port, rhs_port)):
        for energy_id, belief_legs in belief_dict.items():
            rhs_legs = rhs_dict[energy_id]
            for belief_leg, rhs_leg in zip(belief_legs, rhs_legs, strict=True):
                weight = rhs_leg[idx]
                weighted_sum += belief_leg[idx] * weight
                weight_total += weight

    if weight_total <= 0.0:
        return np.nan

    return weighted_sum / weight_total


def _smooth_pi_dict(
    raw_dict: Mapping[EnergyDemandTypeID, Sequence[FloatArray]],
    belief_dict: Mapping[EnergyDemandTypeID, Sequence[FloatArray]],
    alpha: float,
    idx: int,
) -> None:
    """
    Smooth every per-leg array of a belief dict towards the raw duals, in place.

    Parameters
    ----------
    raw_dict
        Raw LP duals per energy demand type and leg, USD/GJ.
    belief_dict
        Beliefs of the same shape; updated in place.
    alpha
        EMA weight on the new raw projection, fraction: ``alpha = 1`` trusts the
        latest projection fully, ``alpha = 0`` ignores it.
    idx
        Current time-step index; only the time-steps from it on are updated.
    """
    for energy_id, raw_legs in raw_dict.items():
        belief_legs = belief_dict[energy_id]
        for raw_leg, belief_leg in zip(raw_legs, belief_legs, strict=True):
            update_belief_path(raw_leg, belief_leg, alpha, idx)
