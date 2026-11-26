# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The scrapping that removes vessels, by age or at a fixed rate."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, overload

import numpy as np

from navigate.simulation.cohort import calculate_retired_share
from navigate.simulation.fleet._composition import (
    extract_cargo_miles,
    get_trade_capacity,
)
from navigate.util import divide_nonzero, drop_negligible, subtract

if TYPE_CHECKING:
    from navigate.core.increment import VesselIncrement
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.types_ import ForecastInput
    from navigate.util.types_ import FloatArray, FloatLike

logger = logging.getLogger(__name__)


def perform_primary_scrapping(
    fleet: Fleet, time: float, time_step: float, idx: int
) -> None:
    """
    Scrap vessels by age, or by the fixed scrap rate when the fleet sets one.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    time
        Current time, in years.
    time_step
        Current time-step size, in years.
    idx
        Current time-step index.
    """
    if fleet.fixed_scrap_rate is None:
        _scrap_by_age(fleet, time, idx)
    else:
        _scrap_at_fixed_rate(fleet, fleet.fixed_scrap_rate, time, time_step, idx)


def perform_secondary_scrapping(
    fleet: Fleet, trade_gap: float, time: float, idx: int
) -> float:
    """
    Scrap the oldest vessels to remove the over-capacity left by primary scrapping.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    trade_gap
        Trade gap after primary scrapping, in cargo-miles/year; negative.
    time
        Current time, in years.
    idx
        Current time-step index.

    Returns
    -------
    float
        Scrapped capacity, in cargo-miles/year.
    """
    scrapped_capacity, youngest_age = _scrap_oldest(fleet, -trade_gap, time, idx)

    trade = fleet.trade[idx]
    if trade > 0 and abs(trade_gap / trade) > 1e-3:
        youngest = "undefined"
        if youngest_age is not None:
            youngest = f"{round(youngest_age)} years"
        logger.info(
            "%s: Secondary scrapping of vessels to make up for an over capacity of %s "
            "cargo-miles. The youngest age of scrapping was %s.",
            fleet,
            round(trade_gap),
            youngest,
        )

    return scrapped_capacity


def group_by_age(fleet: Fleet) -> list[list[tuple[int, int]]]:
    """
    Group the fleet's increments by age across vessel types, oldest first.

    Scrapping takes the increments of one age together across vessel types. An age
    group holds the increments that entered service at the same time: an entry time
    is set once and copied, never accumulated, so increments of one vintage hold
    equal entry times.

    Parameters
    ----------
    fleet
        Fleet whose increments are grouped.

    Returns
    -------
    list[list[tuple[int, int]]]
        (vessel, increment) indices of each age group, oldest group first.
    """
    groups: dict[float, list[tuple[int, int]]] = {}
    for v, increments in enumerate(fleet.increments):
        for i, increment in enumerate(increments):
            groups.setdefault(increment.entered, []).append((v, i))

    return [groups[entered] for entered in sorted(groups)]


def split_oldest_first(
    capacities: FloatArray, capacity: float
) -> tuple[int, float | None]:
    """
    Split a capacity to scrap over age groups, oldest group first.

    The oldest groups are scrapped whole until what is left of the capacity fits in
    the next group, which then has the same fraction of each of its increments
    scrapped. What is left is exact zero once it is negligible against the capacity,
    so a group it fills to rounding is scrapped whole, with nothing split off.

    Parameters
    ----------
    capacities
        Capacity of each age group, oldest first, in cargo-miles/year.
    capacity
        Capacity to scrap, in cargo-miles/year.

    Returns
    -------
    tuple[int, float | None]
        Number of the oldest groups scrapped whole, and the fraction of the next
        group scrapped, or None when the capacity exceeds all groups.
    """
    remaining = capacity

    for g, group_capacity in enumerate(capacities):
        left = float(drop_negligible(remaining - group_capacity, capacity))

        # the group takes the rest of the capacity, in part where it holds more
        if remaining == 0.0 or left < 0.0:
            return g, float(divide_nonzero(remaining, group_capacity))

        # and whole where it holds the rest to rounding
        if left == 0.0:
            return g, 1.0

        remaining = left

    return len(capacities), None


@overload
def calculate_survivors(
    increment: VesselIncrement, lifetime: float, times: float
) -> float: ...


@overload
def calculate_survivors(
    increment: VesselIncrement, lifetime: FloatLike, times: FloatArray
) -> FloatArray: ...


def calculate_survivors(
    increment: VesselIncrement, lifetime: FloatLike, times: FloatLike
) -> FloatLike:
    """
    Calculate the vessels of an increment that age-based scrapping leaves at times.

    The increment's vessels are spread uniformly over its age span and scrapped as
    they pass the lifetime. The share below the lifetime is taken of the increment's
    size before any such scrapping, so that it shrinks pro rata as it ages past it.

    Parameters
    ----------
    increment
        Increment of a vessel type.
    lifetime
        Vessel lifetime, in years: one for all times, or one per time.
    times
        Times at which the vessels are counted, in years.

    Returns
    -------
    FloatLike
        Vessels left at each of the times.
    """
    size_before = increment.count + increment.scrapped_past_lifetime
    ages = times - increment.entered
    retired = calculate_retired_share(lifetime, increment.age_span, ages)

    # vessels converted from a shorter-lived type, and round-off, can leave the cohort
    # scrapped beyond this lifetime's share, so the survivors are capped at the
    # vessels the increment holds
    return np.minimum(increment.count, size_before * (1.0 - retired))


def _scrap_by_age(fleet: Fleet, time: float, idx: int) -> None:
    """
    Scrap the part of each increment beyond the vessel lifetime.

    An increment at or past the lifetime, or within rounding of it, is scrapped whole
    and removed. A converted increment keeps its source type's entry time and span,
    so any increment, not only the oldest, can reach past the lifetime.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    time
        Current time, in years.
    idx
        Current time-step index.
    """
    scrap = fleet.results.scrap

    for v, vessel in enumerate(fleet.vessels):
        lifetime = vessel.lifetime.get()
        increments = fleet.increments[v]

        scrapped_vessels = 0.0
        for increment in increments:
            scrapped_vessels += _scrap_past_lifetime(increment, lifetime, time)

        surviving = [increment for increment in increments if increment.count > 0.0]
        fleet.increments[v] = surviving
        scrap[vessel.name][idx] += scrapped_vessels


def _scrap_past_lifetime(
    increment: VesselIncrement, lifetime: float, time: float
) -> float:
    """
    Scrap the part of an increment beyond the lifetime.

    Parameters
    ----------
    increment
        Increment of a vessel type.
    lifetime
        Vessel lifetime, in years.
    time
        Current time, in years.

    Returns
    -------
    float
        Vessels scrapped.
    """
    survivors = calculate_survivors(increment, lifetime, time)
    scrapping = increment.count - survivors

    increment.count = survivors
    increment.scrapped_past_lifetime += scrapping

    return scrapping


def _scrap_at_fixed_rate(
    fleet: Fleet,
    fixed_scrap_rate: ForecastInput,
    time: float,
    time_step: float,
    idx: int,
) -> None:
    """
    Scrap a fixed yearly share of the fleet's trade, oldest increments first.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    fixed_scrap_rate
        Share of the fleet's trade scrapped per year, fraction.
    time
        Current time, in years.
    time_step
        Current time-step size, in years.
    idx
        Current time-step index.
    """
    scrap_rate = fixed_scrap_rate.get() * time_step
    target_scrap = scrap_rate * get_trade_capacity(fleet, idx)
    _scrap_oldest(fleet, target_scrap, time, idx)

    for vessel, increments in zip(fleet.vessels, fleet.increments, strict=True):
        if not increments:
            continue

        oldest_age = increments[0].age(time)
        lifetime = vessel.lifetime.get()

        if subtract(oldest_age, lifetime) > 0.0:
            raise ValueError(
                f"{fleet}: The oldest increment from {vessel} is older ({oldest_age}"
                f" years) than the allowed lifetime ({lifetime} years)."
            )


def _scrap_oldest(
    fleet: Fleet, capacity: float, time: float, idx: int
) -> tuple[float, float | None]:
    """
    Scrap a given capacity, oldest increments first.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    capacity
        Capacity to scrap, in cargo-miles/year.
    time
        Current time, in years.
    idx
        Current time-step index.

    Returns
    -------
    tuple[float, float | None]
        Scrapped capacity, in cargo-miles/year, and the youngest age scrapped, in
        years, or None when nothing was scrapped in part.
    """
    groups = group_by_age(fleet)
    cargo_miles = extract_cargo_miles(fleet.vessels, idx)

    capacities = np.zeros(len(groups))
    for g, group in enumerate(groups):
        capacities[g] = _group_capacity(fleet, group, cargo_miles)

    whole, fraction = split_oldest_first(capacities, capacity)

    scrap = fleet.results.scrap
    scrapped_increments = [0] * len(fleet.increments)

    for group in groups[:whole]:
        for v, i in group:
            increment = fleet.increments[v][i]
            scrapped_increments[v] = i + 1
            scrap[fleet.vessels[v].name][idx] += increment.count

    # the increments scrapped in part are found by their index, so they are scrapped
    # before the increments scrapped whole are removed
    if fraction is None:
        scrapped_capacity = float(np.sum(capacities))
        youngest_age = None
    else:
        scrapped_capacity = capacity
        youngest_age = _scrap_in_part(fleet, groups[whole], fraction, time, idx)

    for v, scrapped in enumerate(scrapped_increments):
        fleet.increments[v] = fleet.increments[v][scrapped:]

    return scrapped_capacity, youngest_age


def _group_capacity(
    fleet: Fleet, group: list[tuple[int, int]], cargo_miles: FloatArray
) -> np.float64:
    """Return the capacity of an age group, in cargo-miles/year."""
    capacities = []

    for v, i in group:
        increment = fleet.increments[v][i]
        capacities.append(increment.count * cargo_miles[v])

    capacity: np.float64 = np.sum(capacities)

    return capacity


def _scrap_in_part(
    fleet: Fleet,
    group: list[tuple[int, int]],
    fraction: float,
    time: float,
    idx: int,
) -> float | None:
    """
    Scrap the same fraction of each increment of an age group.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    group
        (vessel, increment) indices of the age group.
    fraction
        Share of each increment scrapped.
    time
        Current time, in years.
    idx
        Current time-step index.

    Returns
    -------
    float | None
        Youngest age scrapped, in years.
    """
    scrap = fleet.results.scrap
    youngest_age = None

    for v, i in group:
        increment = fleet.increments[v][i]
        to_scrap = increment.count * fraction
        increment.count -= to_scrap
        increment.scrapped_past_lifetime *= 1.0 - fraction

        # vessels are scrapped from the oldest part of the uniform increment first,
        # which is inconsistent when several time-steps shorter than the increment's
        # age span pass
        youngest_age = increment.age(time) + increment.age_span * (1.0 - fraction)

        scrap[fleet.vessels[v].name][idx] += to_scrap

    return youngest_age
