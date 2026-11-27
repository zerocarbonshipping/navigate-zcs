# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The scrapping that removes vessels, by age or at a fixed rate."""

from __future__ import annotations

import itertools
import logging
from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.cohort import calculate_retired_share, retire_past_age
from navigate.simulation.fleet._composition import (
    extract_cargo_miles,
    get_count,
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


def tabulate_increments(
    fleet: Fleet,
) -> tuple[IntArray, FloatArray, FloatArray, FloatArray]:
    """
    Tabulate the fleet's increments in fleet order, for scrapping oldest first.

    The vessels of an increment entered uniformly over its entry interval, from the
    entry of its oldest vessel to that of its youngest.

    Parameters
    ----------
    fleet
        Fleet whose increments are tabulated.

    Returns
    -------
    tuple[IntArray, FloatArray, FloatArray, FloatArray]
        Each increment's vessel-type index, its count, and the start and end of its
        entry interval, in years.
    """
    sizes = [len(increments) for increments in fleet.increments]
    increments = list(itertools.chain.from_iterable(fleet.increments))

    vessel_indices = np.repeat(np.arange(len(sizes)), sizes)
    counts = np.array([increment.count for increment in increments])
    ends = np.array([increment.entered for increment in increments])
    starts = ends - np.array([increment.age_span for increment in increments])

    return vessel_indices, counts, starts, ends


def split_oldest_first(
    starts: FloatArray, ends: FloatArray, capacities: FloatArray, capacity: float
) -> tuple[FloatArray, float | None]:
    """
    Split a capacity to scrap over increments, the oldest vessels first.

    Every vessel that entered service before a cutoff is scrapped, so each increment
    keeps the share of its vessels that entered at or after it.

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
    tuple[FloatArray, float | None]
        Share of each increment's vessels kept, and the entry time of the
        cutoff, in years, or None where the capacity exceeds the increments' total.
    """
    cutoff = _find_cutoff(starts, ends, capacities, capacity)
    if cutoff is None:
        return np.zeros_like(capacities), None

    return _calculate_share_entered_after(starts, ends, cutoff), cutoff


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

    An interval holding capacity has a positive length, as every increment's span
    does; one the forecast has scrapped whole holds none and adds nothing.

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


def _calculate_share_entered_after(
    starts: FloatArray, ends: FloatArray, cutoff: float
) -> FloatArray:
    """
    Calculate the share of each increment's vessels entered at or after a cutoff.

    The vessels entered uniformly over the entry interval. A cutoff within
    rounding of an end of the interval, against the larger of its ends, splits
    nothing off; an interval ending at or before the cutoff is scrapped whole, even
    where both its ends lie within rounding of it.

    Parameters
    ----------
    starts
        Start of each increment's entry interval, in years.
    ends
        End of each increment's entry interval, in years.
    cutoff
        Entry time of the cutoff, in years.

    Returns
    -------
    FloatArray
        Share of each increment's vessels entered at or after the cutoff: 0.0
        for an interval ending at or before it, 1.0 for one from the cutoff on.
    """
    scale = np.maximum(np.abs(starts), np.abs(ends))
    before = drop_negligible(cutoff - starts, scale)
    after = drop_negligible(ends - cutoff, scale)

    # the cutoff lies inside an interval only where the interval is positive
    inside = divide_nonzero(after, ends - starts)
    shares: FloatArray = np.select([after <= 0.0, before <= 0.0], [0.0, 1.0], inside)

    return shares


def calculate_survivors(
    increment: VesselIncrement, lifetimes: FloatArray, times: FloatArray
) -> FloatArray:
    """
    Calculate the vessels of an increment that age-based scrapping leaves at times.

    The increment's vessels are spread uniformly over its age span and scrapped as
    they pass the lifetime.

    Parameters
    ----------
    increment
        Increment of a vessel type.
    lifetimes
        Vessel lifetime at each of the times, in years.
    times
        Times at which the vessels are counted, in years.

    Returns
    -------
    FloatArray
        Vessels left at each of the times.
    """
    ages = times - increment.entered
    retired = calculate_retired_share(lifetimes, increment.age_span, ages)

    return increment.count * (1.0 - retired)


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

    The share compounds over the time step, each year scrapping its share of what the
    years before left.

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
    scrap_share = calculate_removed_fraction(fixed_scrap_rate.get(), time_step)
    target_scrap = scrap_share * get_trade_capacity(fleet, idx)
    _scrap_oldest(fleet, target_scrap, time, idx)

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
    Scrap a given capacity, the oldest vessels first across vessel types.

    Each increment loses the oldest part of its vessels, as at the lifetime.

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
    vessel_indices, counts, starts, ends = tabulate_increments(fleet)
    capacities = counts * cargo_miles[vessel_indices]

    kept_shares, cutoff = split_oldest_first(starts, ends, capacities, capacity)
    scrapped_capacity = float(np.dot(capacities, 1.0 - kept_shares))

    # a capacity beyond the fleet's leaves no cutoff and scraps every vessel
    if cutoff is None:
        _scrap_all(fleet, idx)
        return scrapped_capacity, None

    scrap = fleet.results.scrap
    shares = iter(kept_shares)

    for v, vessel in enumerate(fleet.vessels):
        increments = fleet.increments[v]
        type_shares = itertools.islice(shares, len(increments))
        surviving, scrapped = _scrap_entered_before(increments, type_shares, cutoff)

        fleet.increments[v] = surviving
        scrap[vessel.name][idx] += scrapped

    return scrapped_capacity, time - cutoff


def _scrap_all(fleet: Fleet, idx: int) -> None:
    """
    Scrap every vessel of the fleet.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    idx
        Current time-step index.
    """
    scrap = fleet.results.scrap

    for v, vessel in enumerate(fleet.vessels):
        scrap[vessel.name][idx] += get_count(fleet, v)
        fleet.increments[v] = []


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
