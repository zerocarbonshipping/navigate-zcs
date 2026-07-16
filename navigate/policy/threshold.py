# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
fair-share threshold calculations for absolute-emission regulations.

calculate_fair_share_threshold is the entry point: it first distributes each
policed vessel's share of the global operational demand (the "fair share"),
then converts that share into a per-vessel emission threshold. fair-share must
run before the vessel threshold because the threshold consumes its result.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

import numpy as np

from navigate.core.enum_ import BunkerScopeID, RegulationMeasureID
from navigate.policy.jurisdiction import calculate_operational_demand_in_policy_jurisdiction
from navigate.util import divide_nonzero

if TYPE_CHECKING:
    from navigate.policy.regulation import Regulation
    from navigate.vessel import Vessel
    from navigate.vessel.fleet.fleet import Fleet


def calculate_fair_share_threshold(regulation: Regulation,
                                   fleets: dict[str, Fleet],
                                   timeline: np.ndarray,
                                   idx: int,
                                   scope: BunkerScopeID
                                   ) -> None:
    """
    Assign the fair share emissions of each vessel for all regulations it is impacted by.

    Parameters
    ----------
    regulation
        Regulation for which fair-share is calculated
    fleets
        All fleets in the simulation.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    scope
        Whether this is for expected fuel cost or global bunkering.
    """

    # fair-share is called prior to vessel threshold as
    # vessel threshold uses the result from fair-share
    _calculate_fair_share(regulation, fleets, timeline, idx, scope)
    _calculate_vessel_threshold(regulation, fleets, timeline, idx, scope)


def _resolve_time_index(timeline: np.ndarray, idx: int, scope: BunkerScopeID) -> tuple[int | slice, np.ndarray]:
    """
    Resolve the timeline index and times for the requested scope.

    Parameters
    ----------
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    scope
        Whether this is for expected fuel cost or global bunkering.

    Returns
    -------
    Tuple of the time-step index (scalar for existing, slice for expected) and
    the corresponding timeline values.
    """

    if scope == BunkerScopeID.EXISTING:
        _idx = idx
    else:
        _idx = np.s_[idx:]

    return _idx, timeline[_idx]


def _iter_fleet_vessels(fleets: dict[str, Fleet]) -> Iterator[tuple[Fleet, Vessel, str]]:
    """
    Iterate over every vessel across all fleets.

    Parameters
    ----------
    fleets
        All fleets in the simulation.

    Returns
    -------
    Iterator of (fleet, vessel, vessel name) tuples.
    """

    for fleet in fleets.values():
        for vessel in fleet.get_vessels():
            yield fleet, vessel, vessel.get_name()


def _calculate_fair_share(regulation: Regulation,
                          fleets: dict[str, Fleet],
                          timeline: np.ndarray,
                          idx: int,
                          scope: BunkerScopeID
                          ) -> None:
    """
    Distribute each policed vessel's share of the global operational demand.

    Parameters
    ----------
    regulation
        Regulation for which fair-share is calculated.
    fleets
        All fleets in the simulation.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    scope
        Whether this is for expected fuel cost or global bunkering.
    """

    # fair-share only applies to absolute-emission regulations; intensity-based
    # regulations apply directly to each vessel.
    if regulation.measure != RegulationMeasureID.ABSOLUTE:
        return

    _idx, times = _resolve_time_index(timeline, idx, scope)

    demands = {}
    global_demand = 0.

    for fleet, vessel, vessel_name in _iter_fleet_vessels(fleets):

        if regulation.vessel_is_policed(vessel_name):

            demand = calculate_operational_demand_in_policy_jurisdiction(regulation, vessel, times, _idx)

            if scope == BunkerScopeID.EXISTING:
                multiplier = fleet.expectation.get_existing_multipliers(vessel_name, _idx)
            else:
                multiplier = fleet.expectation.get_expected_multipliers(vessel_name, _idx)

            global_demand += demand * multiplier

        else:
            demand = 0.

        demands[vessel_name] = demand

    for vessel_name, demand in demands.items():

        fair_share = divide_nonzero(demand, global_demand)

        if scope == BunkerScopeID.EXISTING:
            regulation.expectation.set_vessel_fair_share_existing(vessel_name, fair_share)
        else:
            regulation.expectation.set_vessel_fair_share_expected(idx, vessel_name, fair_share)


def _calculate_vessel_threshold(regulation: Regulation,
                                fleets: dict[str, Fleet],
                                timeline: np.ndarray,
                                idx: int,
                                scope: BunkerScopeID
                                ) -> None:
    """
    Convert each policed vessel's fair share into a per-vessel emission threshold.

    Parameters
    ----------
    regulation
        Regulation for which the vessel threshold is calculated.
    fleets
        All fleets in the simulation.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    scope
        Whether this is for expected fuel cost or global bunkering.
    """

    _idx, times = _resolve_time_index(timeline, idx, scope)

    shared_threshold = regulation.shared_threshold

    if shared_threshold is not None:
        shared_threshold = shared_threshold.get(times)

    for _, _, vessel_name in _iter_fleet_vessels(fleets):

        if regulation.vessel_is_policed(vessel_name):

            if shared_threshold is None:
                vessel_threshold = regulation.get_vessel_threshold(vessel_name).get(times)
            else:
                if regulation.measure == RegulationMeasureID.ABSOLUTE:

                    if scope == BunkerScopeID.EXISTING:
                        fair_share = regulation.expectation.get_vessel_fair_share_existing(vessel_name)
                    else:
                        fair_share = regulation.expectation.get_vessel_fair_share_expected(vessel_name, _idx)

                else:
                    fair_share = 1.

                vessel_threshold = fair_share * shared_threshold

            if scope == BunkerScopeID.EXISTING:
                regulation.expectation.set_vessel_threshold_existing(vessel_name, vessel_threshold)
                regulation.profile.set_vessel_threshold(idx, vessel_name, vessel_threshold)
            else:
                regulation.expectation.set_vessel_threshold_expected(idx, vessel_name, vessel_threshold)
