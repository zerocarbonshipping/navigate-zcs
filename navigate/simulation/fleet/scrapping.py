# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Vessel ageing and the scrapping that removes vessels."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.cohort import calculate_share_below, extends_past
from navigate.simulation.fleet.composition import (
    extract_cargo_miles,
    get_trade_capacity,
)
from navigate.util import ROUND_OFF, YEAR

if TYPE_CHECKING:
    from navigate.core.increment import VesselIncrement
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.types_ import ForecastInput
    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)


def update_vessel_ages(fleet: Fleet, time_step: float) -> None:
    """
    Age the fleet's vessels by the time since the last time-step.

    Parameters
    ----------
    fleet
        Fleet whose vessels are aged.
    time_step
        Current time-step size, days.
    """
    dt = time_step / YEAR

    for increments in fleet.increments:
        for increment in increments:
            increment.age += dt


def perform_primary_scrapping(fleet: Fleet, time_step: float, idx: int) -> None:
    """
    Scrap vessels by age, or by the fixed scrap rate when the fleet sets one.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    time_step
        Current time-step size, days.
    idx
        Current time-step index.
    """
    if fleet.fixed_scrap_rate is None:
        _scrap_by_age(fleet, idx)
    else:
        _scrap_at_fixed_rate(fleet, fleet.fixed_scrap_rate, time_step, idx)


def perform_secondary_scrapping(fleet: Fleet, trade_gap: float, idx: int) -> float:
    """
    Scrap the oldest vessels to remove the over-capacity left by primary scrapping.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    trade_gap
        Trade gap after primary scrapping, cargo-miles/year; negative.
    idx
        Current time-step index.

    Returns
    -------
    float
        Scrapped capacity, cargo-miles/year.
    """
    scrapped_capacity, youngest_age = _scrap_oldest(fleet, -trade_gap, idx)

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


def _scrap_by_age(fleet: Fleet, idx: int) -> None:
    """
    Scrap the increments at the vessel lifetime, and any older part of the next one.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    idx
        Current time-step index.
    """
    scrap = fleet.results.scrap

    for v, vessel in enumerate(fleet.vessels):
        lifetime = vessel.lifetime.get()
        increments = fleet.increments[v]
        expired = _count_expired(increments, lifetime)

        scrapped_vessels = 0.0
        for increment in increments[:expired]:
            scrapped_vessels += increment.multiplier

        increments = _drop_oldest(increments, expired)
        fleet.increments[v] = increments

        if increments:
            scrapped_vessels += _scrap_past_lifetime(increments[0], lifetime)

        scrap[vessel.name][idx] += scrapped_vessels


def _count_expired(increments: list[VesselIncrement], lifetime: float) -> int:
    """Count the increments at or past the lifetime, oldest first."""
    count = 0

    for increment in increments:
        if increment.age >= lifetime:
            count += 1
        else:
            break

    return count


def _scrap_past_lifetime(oldest: VesselIncrement, lifetime: float) -> float:
    """
    Scrap the part of the oldest increment beyond the lifetime.

    Parameters
    ----------
    oldest
        Oldest increment of a vessel type.
    lifetime
        Vessel lifetime, years.

    Returns
    -------
    float
        Vessels scrapped.
    """
    baseline = oldest.baseline

    if baseline is None or not extends_past(oldest, lifetime):
        return 0.0

    # the cohort's vessels are assumed to have entered uniformly over its age span
    alpha = calculate_share_below(oldest, lifetime)
    remaining = baseline * alpha
    scrapping = oldest.multiplier - remaining

    # conversions out of the cohort can leave fewer vessels than the baseline share
    # that remains, so the scrapping is floored at zero
    scrapping = max(scrapping, 0.0)
    oldest.multiplier -= scrapping

    return scrapping


def _scrap_at_fixed_rate(
    fleet: Fleet, fixed_scrap_rate: ForecastInput, time_step: float, idx: int
) -> None:
    """
    Scrap a fixed yearly share of the fleet's trade, oldest increments first.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    fixed_scrap_rate
        Share of the fleet's trade scrapped per year, fraction.
    time_step
        Current time-step size, days.
    idx
        Current time-step index.
    """
    scrap_rate = fixed_scrap_rate.get() * time_step / YEAR
    target_scrap = scrap_rate * get_trade_capacity(fleet, idx)
    _scrap_oldest(fleet, target_scrap, idx)

    for vessel, increments in zip(fleet.vessels, fleet.increments, strict=True):
        if not increments:
            continue

        # rounding keeps round-off error from tripping the lifetime check
        oldest_age = np.round(increments[0].age, ROUND_OFF)
        lifetime = np.round(vessel.lifetime.get(), ROUND_OFF)

        if oldest_age > lifetime:
            raise ValueError(
                f"{fleet}: The oldest increment from {vessel} is older ({oldest_age}"
                f" years) than the allowed lifetime ({lifetime} years)."
            )


def _scrap_oldest(
    fleet: Fleet, capacity: float, idx: int
) -> tuple[float, float | None]:
    """
    Scrap a given capacity, oldest increments first.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    capacity
        Capacity to scrap, cargo-miles/year.
    idx
        Current time-step index.

    Returns
    -------
    tuple[float, float | None]
        Scrapped capacity, cargo-miles/year, and the youngest age scrapped, years, or
        None when nothing was scrapped in part.
    """
    # the increments of one age are scrapped together across vessel types, so their
    # (vessel, increment) indices are grouped by the rounded age
    groups: dict[float, list[tuple[int, int]]] = {}
    for v, increments in enumerate(fleet.increments):
        ages = np.round([increment.age for increment in increments], ROUND_OFF)
        for i, age in enumerate(ages):
            groups.setdefault(age, []).append((v, i))

    cargo_miles = extract_cargo_miles(fleet.vessels, idx)
    scrap = fleet.results.scrap

    remaining = capacity
    youngest_age = None
    scrapped_counts = [0] * len(fleet.increments)

    for age in sorted(groups, reverse=True):
        group = groups[age]
        group_capacity = _group_capacity(fleet, group, cargo_miles)

        if group_capacity >= remaining:
            # the age group covers what is left: scrap the same fraction of each of
            # its increments
            fraction = remaining / group_capacity
            youngest_age = _scrap_in_part(fleet, group, fraction, idx)
            remaining = 0.0
            break

        # what is left exceeds the age group's capacity: scrap all of its increments
        remaining -= group_capacity

        for v, i in group:
            increment = fleet.increments[v][i]
            scrapped_counts[v] = i + 1
            scrap[fleet.vessels[v].name][idx] += increment.multiplier

    for v, count in enumerate(scrapped_counts):
        fleet.increments[v] = _drop_oldest(fleet.increments[v], count)

    return capacity - remaining, youngest_age


def _group_capacity(
    fleet: Fleet, group: list[tuple[int, int]], cargo_miles: FloatArray
) -> np.float64:
    """Return the capacity of an age group, in cargo-miles/year."""
    capacities = []

    for v, i in group:
        increment = fleet.increments[v][i]
        capacities.append(increment.multiplier * cargo_miles[v])

    capacity: np.float64 = np.sum(capacities)

    return capacity


def _scrap_in_part(
    fleet: Fleet, group: list[tuple[int, int]], fraction: float, idx: int
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
    idx
        Current time-step index.

    Returns
    -------
    float | None
        Youngest age scrapped, years.
    """
    scrap = fleet.results.scrap
    youngest_age = None

    for v, i in group:
        increment = fleet.increments[v][i]
        to_scrap = increment.multiplier * fraction
        increment.multiplier -= to_scrap

        if i == 0 and increment.baseline is not None:
            increment.baseline -= to_scrap

        # vessels are scrapped from the oldest part of the uniform increment first,
        # which is inconsistent when several time-steps shorter than the increment's
        # age span pass
        youngest_age = increment.age + increment.age_span * (1.0 - fraction)

        scrap[fleet.vessels[v].name][idx] += to_scrap

    return youngest_age


def _drop_oldest(
    increments: list[VesselIncrement], count: int
) -> list[VesselIncrement]:
    """Drop the oldest increments; the new oldest takes its multiplier as baseline."""
    if count == 0:
        return increments

    surviving = increments[count:]
    if surviving:
        surviving[0].baseline = surviving[0].multiplier

    return surviving
