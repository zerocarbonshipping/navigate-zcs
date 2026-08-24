# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from navigate.core import calculate_compound_growth
from navigate.core.enum_ import EnergyDemandTypeID
from navigate.core.nodes.vessel import Vessel
from navigate.util import ROUND_OFF

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet


def extract_cargo_miles(vessels: list[Vessel], idx: int | slice) -> list[NDArray[np.float64]]:
    return [vessel.expectation.get_cargo_miles(idx) for vessel in vessels]


def is_retrofit_cycle(age: float, retrofit_frequency: float, time_step: float, decimals: int = 2) -> bool:
    """
    Returns whether the vessel is in a retrofit cycle.
    """

    # check the increment is within a retrofit
    # frequency period and not at age 0
    age_ = round(age, decimals)
    time_step_ = round(time_step, decimals)
    return (age_ > time_step_) and ((age_ % retrofit_frequency) < time_step_)


def calculate_projected_multipliers(multipliers: float, trade: np.ndarray) -> np.ndarray:
    """
    Calculate a naive projection of future number of multipliers. This method does not take into account that different
     vessel types may have varying nominal capacity or cargo utilization.

    Parameters
    ----------
    multipliers
        Sum of multipliers across vessel types.
    trade
        Trade forecast.

    Returns
    -------
        Naive projection of future multipliers.
    """

    compound_growth = trade / trade[0]
    return multipliers * compound_growth


def calculate_increments(uptakes: np.ndarray, cargo_miles: np.ndarray, trade_gap: float) -> np.ndarray:
    """
    Calculate the number of multipliers with a given uptake share which satisfies the trade-gap.

    Parameters
    ----------
    uptakes
        The uptake share of each vessel type.
    cargo_miles
        The yearly cargo-miles delivered by each vessel type.
    trade_gap
        The total trade-gap for the fleet.

    Returns
    -------
    The number of multipliers for each vessel type that satisfies the trade-gap.
    """

    return uptakes * trade_gap / cargo_miles


def extract_investment_metrics(vessels: list[Vessel]) -> np.ndarray:
    """
    Parameters
    ----------
    vessels
        All applicable vessels in the fleet.

    Returns
    -------
    Value of investment metric per vessel.
    """

    return np.array([vessel.expectation.get_investment_metric() for vessel in vessels])


def get_remaining_lifetime(vessel: Vessel, age: float, dt: float) -> int:
    lifetime = vessel.lifetime.get()
    return max(0, int(round(lifetime - (age + dt / 2.0), ROUND_OFF)))


def net_energy_from_raw(raw_energies: dict[EnergyDemandTypeID, list[float]],
                        savings: dict[EnergyDemandTypeID, list[float]],
                        ) -> dict[EnergyDemandTypeID, list[float]]:
    out = {}
    for k, raw in raw_energies.items():
        sav = savings[k]
        out[k] = [(1.0 - s) * e for e, s in zip(raw, sav)]
    return out


def define_initial_split(fleet: Fleet) -> None:
    """
    Define the initial fraction of each vessel type in the fleet.

    Parameters
    ----------
    fleet
        Fleet to define the initial split for.
    """

    # if the initial split is not supplied
    # by the user, then assume a uniform
    # split on cargo-miles
    if not fleet.initial_split:
        nv = len(fleet.assets)
        fleet.initial_split = [1. / nv for v in range(nv)]

    # while the initial split of the entire
    # existing fleet does not necessarily
    # correspond to current trends in
    # newbuilds, it is the best available proxy
    # TODO: allow this to be user-defined
    fleet.current_uptake = np.array(fleet.initial_split)


def define_initial_trade(fleet: Fleet, timeline: np.ndarray) -> None:
    """
    Define the initial trade of the fleet and project it forward over the timeline by the
    user-supplied growth rates.

    Parameters
    ----------
    fleet
        Fleet to define the trade for.
    timeline
        Simulation timeline.
    """

    idx = 0
    cargo_miles = extract_cargo_miles(fleet.assets, idx)

    multipliers = fleet.get_multipliers()
    initial_trade = np.dot(multipliers, cargo_miles)
    trade_growth = fleet.trade_growth.get(timeline)

    # the initial trade is projected forward in
    # time by calculating the compound growth
    # from the user-supplied growth rates
    fleet.trade = calculate_compound_growth(initial_trade, trade_growth, timeline)

    # transfer to profile
    fleet.profile.set_trade(idx, fleet.trade[idx])
