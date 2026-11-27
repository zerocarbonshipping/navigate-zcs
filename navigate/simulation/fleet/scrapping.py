# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The scrapping that removes vessels, by age or at a fixed rate."""

from __future__ import annotations

import itertools
import logging
from dataclasses import replace
from typing import TYPE_CHECKING, NamedTuple

import numpy as np

from navigate.simulation.cohort import calculate_share_below, retire_past_age
from navigate.simulation.fleet._composition import (
    count_by_type,
    extract_cargo_miles,
    get_trade_capacity,
)
from navigate.util import (
    calculate_removed_fraction,
    divide_nonzero,
    drop_negligible,
    subtract,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.core.increment import VesselIncrement
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.types_ import ForecastInput
    from navigate.util.types_ import FloatArray, IntArray

logger = logging.getLogger(__name__)


class OldestFirstScrapping(NamedTuple):
    """The increments scrapping oldest first leaves, and what it scraps."""

    increments: list[list[VesselIncrement]]
    scrapped_counts: list[float]
    scrapped_capacity: float
    cutoff: float | None


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


def calculate_fixed_rate_scrap(rate: float, time_step: float, capacity: float) -> float:
    """
    Calculate the capacity the fixed scrap rate scraps over a time step.

    The yearly rate compounds over the time step, each year scrapping its share of
    what the years before left.

    Parameters
    ----------
    rate
        Share of the fleet's trade scrapped per year, fraction.
    time_step
        Time-step size, in years.
    capacity
        Trade capacity of the vessels counted, in cargo-miles/year.

    Returns
    -------
    float
        Capacity to scrap, in cargo-miles/year.
    """
    return calculate_removed_fraction(rate, time_step) * capacity


def scrap_oldest_first(
    increments: list[list[VesselIncrement]], cargo_miles: FloatArray, capacity: float
) -> OldestFirstScrapping:
    """
    Scrap a capacity from increments, the oldest vessels first across vessel types.

    Every vessel that entered service before a cutoff is scrapped, so each increment
    loses the oldest part of its vessels, as at the lifetime. The increments passed
    are left as they are: the ones kept whole are passed on, and the ones cut are
    rebuilt.

    Parameters
    ----------
    increments
        Increments of each vessel type, oldest first.
    cargo_miles
        Cargo-miles of one vessel of each type, in cargo-miles/year.
    capacity
        Capacity to scrap, in cargo-miles/year.

    Returns
    -------
    OldestFirstScrapping
        The increments left of each vessel type, in their order, and the vessels
        scrapped of each; the capacity scrapped, in cargo-miles/year; and the entry
        time of the cutoff, in years, or None where the capacity exceeds the
        increments' and every vessel is scrapped.
    """
    vessel_indices, counts, starts, ends = _tabulate_increments(increments)
    capacities = counts * cargo_miles[vessel_indices]

    # a capacity beyond the increments' leaves no cutoff and scraps every vessel
    cutoff = _find_cutoff(starts, ends, capacities, capacity)
    if cutoff is None:
        left: list[list[VesselIncrement]] = [[] for _ in increments]
        total = float(np.sum(capacities))
        return OldestFirstScrapping(left, count_by_type(increments), total, None)

    kept_shares = 1.0 - calculate_share_below(starts, ends, cutoff)
    scrapped_capacity = float(np.dot(capacities, 1.0 - kept_shares))

    left = []
    scrapped_counts = []
    shares = iter(kept_shares)

    for group in increments:
        group_shares = itertools.islice(shares, len(group))
        kept, scrapped = _scrap_entered_before(group, group_shares, cutoff)

        left.append(kept)
        scrapped_counts.append(scrapped)

    return OldestFirstScrapping(left, scrapped_counts, scrapped_capacity, cutoff)


def _tabulate_increments(
    increments: list[list[VesselIncrement]],
) -> tuple[IntArray, FloatArray, FloatArray, FloatArray]:
    """
    Tabulate increments in vessel-type order, for scrapping oldest first.

    The vessels of an increment entered uniformly over its entry interval, from the
    entry of its oldest vessel to that of its youngest.

    Parameters
    ----------
    increments
        Increments of each vessel type.

    Returns
    -------
    tuple[IntArray, FloatArray, FloatArray, FloatArray]
        Each increment's vessel-type index, its count, and the start and end of its
        entry interval, in years.
    """
    sizes = [len(group) for group in increments]
    flat = list(itertools.chain.from_iterable(increments))

    vessel_indices = np.repeat(np.arange(len(sizes)), sizes)
    counts = np.array([increment.count for increment in flat])
    ends = np.array([increment.entered for increment in flat])
    starts = ends - np.array([increment.age_span for increment in flat])

    return vessel_indices, counts, starts, ends


def _find_cutoff(
    starts: FloatArray, ends: FloatArray, capacities: FloatArray, capacity: float
) -> float | None:
    """
    Find the entry time before which the vessels entered hold a capacity.

    Each increment's capacity entered uniformly over its entry interval, so the
    capacity entered by a time is piecewise linear in the time, with knots at the
    ends of the intervals; the cutoff lies in the segment over which that capacity
    reaches the one to scrap. A capacity within rounding of what had entered by a
    knot puts the cutoff on the knot, so a capacity within rounding of the total
    scraps every increment.

    Parameters
    ----------
    starts
        Start of each increment's entry interval, in years.
    ends
        End of each increment's entry interval, in years.
    capacities
        Capacity of each increment, in cargo-miles/year.
    capacity
        Capacity to scrap, in cargo-miles/year.

    Returns
    -------
    float | None
        Entry time of the cutoff, in years, or None where the capacity exceeds the
        increments' total.
    """
    density = divide_nonzero(capacities, ends - starts)
    knots = np.concatenate((starts, ends))
    changes = np.concatenate((density, -density))

    # the capacity entering per year after each knot; knots of equal time are
    # neighbours in the order, so the segments between them have zero length
    order = np.argsort(knots)
    knots = knots[order]
    slopes = np.cumsum(changes[order])

    cumulative = np.zeros(knots.size)
    cumulative[1:] = np.cumsum(slopes[:-1] * np.diff(knots))

    excess = drop_negligible(cumulative - capacity, capacity)
    reached = np.flatnonzero(excess >= 0.0)
    if not reached.size:
        return None

    knot_idx = reached[0]
    if excess[knot_idx] == 0.0:
        return float(knots[knot_idx])

    # nothing has entered by the first knot, so the capacity is reached inside the
    # segment before a later knot; that segment has a positive length, so the knot
    # starting it is the last of its time in the order, and its positive slope holds
    # every change at that time
    shortfall = capacity - cumulative[knot_idx - 1]
    return float(knots[knot_idx - 1] + shortfall / slopes[knot_idx - 1])


def _scrap_entered_before(
    increments: list[VesselIncrement],
    kept_shares: Iterable[float],
    cutoff: float,
) -> tuple[list[VesselIncrement], float]:
    """
    Scrap the vessels of a type's increments that entered before a cutoff.

    An increment spanning the cutoff keeps its vessels entered at or after it, its
    span then starting at the cutoff.

    Parameters
    ----------
    increments
        Increments of a vessel type.
    kept_shares
        Share of each increment's vessels entered at or after the cutoff, snapped to
        0.0 or 1.0 within rounding of an end of its entry interval.
    cutoff
        Entry time of the cutoff, in years.

    Returns
    -------
    tuple[list[VesselIncrement], float]
        The increments left, in their order, and the vessels scrapped.
    """
    kept = []
    scrapped = 0.0

    for increment, share in zip(increments, kept_shares, strict=True):
        if share == 1.0:
            kept.append(increment)

        elif share == 0.0:
            scrapped += increment.count

        else:
            count = increment.count * share
            span = increment.entered - cutoff

            kept.append(replace(increment, count=count, age_span=span))
            scrapped += increment.count - count

    return kept, scrapped


def _scrap_by_age(fleet: Fleet, time: float, idx: int) -> None:
    """
    Scrap the part of each increment beyond the vessel lifetime.

    A converted increment keeps its source type's ages, so any increment, not only
    the oldest, can reach past the lifetime.

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
        surviving, scrapped = retire_past_age(fleet.increments[v], lifetime, time)

        fleet.increments[v] = surviving
        scrap[vessel.name][idx] += scrapped


def _scrap_at_fixed_rate(
    fleet: Fleet,
    fixed_scrap_rate: ForecastInput,
    time: float,
    time_step: float,
    idx: int,
) -> None:
    """
    Scrap a fixed yearly share of the fleet's trade, the oldest vessels first.

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
    rate = fixed_scrap_rate.get()
    trade_capacity = get_trade_capacity(fleet, idx)

    capacity = calculate_fixed_rate_scrap(rate, time_step, trade_capacity)
    _scrap_oldest(fleet, capacity, time, idx)

    for vessel, increments in zip(fleet.vessels, fleet.increments, strict=True):
        if not increments:
            continue

        oldest = increments[0]
        youngest_age = oldest.youngest_age(time)
        lifetime = vessel.lifetime.get()

        if subtract(youngest_age, lifetime) > 0.0:
            raise ValueError(
                f"{fleet}: The youngest vessel of the oldest increment from {vessel} is"
                f" older ({youngest_age} years) than the allowed lifetime ({lifetime}"
                " years)."
            )


def _scrap_oldest(
    fleet: Fleet, capacity: float, time: float, idx: int
) -> tuple[float, float | None]:
    """
    Scrap a given capacity from the fleet, the oldest vessels first.

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
        years, or None where the capacity exceeds the fleet's.
    """
    cargo_miles = extract_cargo_miles(fleet.vessels, idx)
    scrapping = scrap_oldest_first(fleet.increments, cargo_miles, capacity)
    scrap = fleet.results.scrap

    for v, vessel in enumerate(fleet.vessels):
        fleet.increments[v] = scrapping.increments[v]
        scrap[vessel.name][idx] += scrapping.scrapped_counts[v]

    if scrapping.cutoff is None:
        return scrapping.scrapped_capacity, None

    return scrapping.scrapped_capacity, time - scrapping.cutoff
