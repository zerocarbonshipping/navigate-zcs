# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The fleet's increments: vessel counts, retrofit cycles and the trade they carry."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from itertools import groupby
from operator import attrgetter
from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.cohort import split_at_age
from navigate.util import DAYS_PER_YEAR, is_negligible, subtract

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.core.increment import VesselIncrement
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import BoolArray, FloatArray


@dataclass(frozen=True, slots=True)
class CycleSplit:
    """
    A vessel type's increments split at their retrofit cycles.

    Parameters
    ----------
    vessel_idx
        Index of the vessel type in the fleet.
    originals
        The increments as they were before the split, sorted oldest first.
    parts
        The parts of each original increment, youngest first.
    at_cycle
        The parts whose vessels are at a cycle, sorted oldest first.
    """

    vessel_idx: int
    originals: list[VesselIncrement]
    parts: list[list[VesselIncrement]]
    at_cycle: list[VesselIncrement]


def get_trade_capacity(fleet: Fleet, idx: int) -> float:
    """
    Return the trade the fleet's vessels can carry at a time-step.

    Parameters
    ----------
    fleet
        Fleet holding the vessels.
    idx
        Time-step index.

    Returns
    -------
    float
        Trade capacity of the fleet, in cargo-miles/year.
    """
    counts = get_counts(fleet)
    cargo_miles = extract_cargo_miles(fleet.vessels, idx)

    return float(np.dot(counts, cargo_miles))


def get_counts(fleet: Fleet) -> list[float]:
    """
    Return the number of vessels of each type in the fleet.

    Parameters
    ----------
    fleet
        Fleet holding the vessels.

    Returns
    -------
    list[float]
        Number of vessels of each type.
    """
    return [get_count(fleet, v) for v in range(len(fleet.increments))]


def get_total_count(fleet: Fleet) -> float:
    """
    Return the number of vessels in the fleet.

    Parameters
    ----------
    fleet
        Fleet holding the vessels.

    Returns
    -------
    float
        Number of vessels of all types.
    """
    return float(sum(get_counts(fleet)))


def get_count(fleet: Fleet, vessel_idx: int) -> float:
    """
    Return the number of vessels of one type in the fleet.

    Parameters
    ----------
    fleet
        Fleet holding the vessels.
    vessel_idx
        Index of the vessel type in the fleet.

    Returns
    -------
    float
        Number of vessels of the type.
    """
    return sum(increment.count for increment in fleet.increments[vessel_idx])


def is_in_service(counts: FloatArray) -> BoolArray:
    """
    Mark the vessel types whose count is not negligible against the fleet's total.

    Parameters
    ----------
    counts
        Number of vessels of each type: at one time-step, or one row per type over
        several.

    Returns
    -------
    BoolArray
        Whether each vessel type is in service, in the shape of ``counts``.
    """
    return ~is_negligible(counts, np.sum(counts, axis=0))


def extract_cargo_miles(vessels: list[Vessel], idx: int | slice) -> FloatArray:
    """
    Extract each vessel's cargo-miles at a time-step or over a slice of the timeline.

    Parameters
    ----------
    vessels
        Vessels to extract cargo-miles for.
    idx
        Time-step index or slice.

    Returns
    -------
    FloatArray
        Cargo-miles of one vessel of each type, in cargo-miles/year: one per vessel
        for a time-step, one row per vessel for a slice.
    """
    return np.array([vessel.expectation.cargo_miles[idx] for vessel in vessels])


def sort_oldest_first(increments: Iterable[VesselIncrement]) -> list[VesselIncrement]:
    """
    Sort increments oldest first, by their entry time.

    Increments that entered at the same time keep their order.

    Parameters
    ----------
    increments
        Increments sorted.

    Returns
    -------
    list[VesselIncrement]
        The increments, oldest first.
    """
    return sorted(increments, key=attrgetter("entered"))


def split_at_cycle(
    fleet: Fleet, vessel_idx: int, time: float, time_step: float, minimum_age: float
) -> CycleSplit:
    """
    Split a vessel type's increments at their retrofit-cycle windows.

    A decision on the vessels at a cycle, a retrofit or a conversion, acts on them
    alone. The vessels of an increment in a window therefore become an increment of
    their own, spanning the window's part of the age span, and each part outside the
    windows another. A split keeps each vessel's age, technology package and charter
    rate. The fleet keeps the increments until ``rejoin_unchanged`` replaces them
    with the parts, joined again where the decision left them unchanged.

    Parameters
    ----------
    fleet
        Fleet holding the vessel type.
    vessel_idx
        Index of the vessel type in the fleet.
    time
        Time at the end of the time-step, in years.
    time_step
        Time-step size, in years.
    minimum_age
        Age below which a vessel is not eligible, in years.

    Returns
    -------
    CycleSplit
        The increments, their parts and the parts at a cycle.
    """
    increments = fleet.increments[vessel_idx]
    interval = fleet.retrofit_interval.get()
    lifetime = fleet.vessels[vessel_idx].lifetime.get()

    parts = []
    at_cycle = []

    for increment in increments:
        cycle_parts = _cycle_parts(
            increment, time, time_step, interval, lifetime, minimum_age
        )
        bounds = [oldest for oldest, _ in cycle_parts[:-1]]
        pieces = _cut(increment, bounds, time)

        for piece, (_, is_at_cycle) in zip(pieces, cycle_parts, strict=True):
            if is_at_cycle:
                at_cycle.append(piece)

        parts.append(pieces)

    return CycleSplit(vessel_idx, increments, parts, sort_oldest_first(at_cycle))


def rejoin_unchanged(fleet: Fleet, splits: Iterable[CycleSplit]) -> None:
    """
    Replace each split vessel type's increments with their parts, joined if unchanged.

    Neighbouring parts of an increment join where they still carry one technology
    package, one charter rate and as many vessels per year of age: a retrofit changes
    the package and charter rate of a part at a cycle, a conversion its vessels.

    Parameters
    ----------
    fleet
        Fleet holding the split vessel types; their increment lists are replaced.
    splits
        Splits whose parts the decisions have acted on; the fleet's increment lists
        of their vessel types have not changed since the split.
    """
    for split in splits:
        joined = []

        for increment, parts in zip(split.originals, split.parts, strict=True):
            joined += _join_unchanged(increment, parts)

        fleet.increments[split.vessel_idx] = sort_oldest_first(joined)


def _join_unchanged(
    increment: VesselIncrement, parts: list[VesselIncrement]
) -> list[VesselIncrement]:
    """
    Join the neighbouring parts of an increment that no decision changed.

    An increment whose parts all join keeps its entry time and span as they were,
    which the sum of its parts can miss in the last digit, and takes their count,
    which a conversion too small to keep the parts apart may have reduced.

    Parameters
    ----------
    increment
        Increment as it was before the split.
    parts
        Its parts, youngest first.

    Returns
    -------
    list[VesselIncrement]
        The joined parts, youngest first.
    """
    joined = [parts[0]]

    for older in parts[1:]:
        if _is_unchanged(joined[-1], older):
            joined[-1] = _join(joined[-1], older)
        else:
            joined.append(older)

    if len(joined) == 1:
        return [replace(increment, count=joined[0].count)]

    return joined


def _cycle_parts(
    increment: VesselIncrement,
    time: float,
    time_step: float,
    interval: float,
    lifetime: float,
    minimum_age: float,
) -> list[tuple[float, bool]]:
    """
    Divide an increment's age span into parts at a retrofit cycle and parts not.

    A vessel is at a cycle in the time-step in which its age reached a positive
    multiple k * f of the retrofit interval f: at the end of the step its age lies in
    ``[k * f, k * f + min(time_step, f))``, the windows no longer than f so that they
    do not overlap and a vessel counts once per step. The vessels at a cycle are those
    the increment holds in a window, below the lifetime and at or above the minimum
    age.

    The time axis resolves days, so a part shorter than a day, such as one a calendar
    date's offset from an anniversary cuts off, holds no vessels of its own: it joins
    the part older than it, the oldest part the one younger.

    Parameters
    ----------
    increment
        Increment of a vessel type.
    time
        Time at the end of the time-step, in years.
    time_step
        Time-step size, in years.
    interval
        Interval between retrofit opportunities, in years.
    lifetime
        Lifetime of the vessel type, in years.
    minimum_age
        Age below which a vessel is not eligible, in years.

    Returns
    -------
    list[tuple[float, bool]]
        The oldest age of each part, in years, and whether its vessels are at a cycle,
        youngest part first; the last part ends at the oldest age of the span.
    """
    youngest = increment.youngest_age(time)
    oldest = increment.oldest_age(time)
    lower = max(youngest, minimum_age)
    upper = min(oldest, lifetime)

    parts = []
    bound = youngest

    if upper > lower:
        window_starts, window_ends = _cycle_windows(lower, upper, time_step, interval)
        starts = np.maximum(window_starts, lower)
        ends = np.minimum(window_ends, upper)

        for start, end in zip(starts.tolist(), ends.tolist(), strict=True):
            if end <= start:
                continue

            if start > bound:
                parts.append((start, False))

            parts.append((end, True))
            bound = end

    if oldest > bound:
        parts.append((oldest, False))

    return _join_short_parts(parts, youngest)


def _join_short_parts(
    parts: list[tuple[float, bool]], youngest: float
) -> list[tuple[float, bool]]:
    """
    Join each part shorter than a day to a neighbour, and neighbours of one kind.

    A short part joins the part older than it, and the oldest part the one younger,
    keeping the kind of the part it joins; an oldest part with none before it stands
    alone, so that a cohort shorter than a day is at a cycle with its oldest vessels.

    Parameters
    ----------
    parts
        The oldest age of each part, in years, and whether it is at a cycle, youngest
        part first; each part is longer than none.
    youngest
        Youngest age of the first part, in years.

    Returns
    -------
    list[tuple[float, bool]]
        The parts after joining, in the same form.
    """
    day = 1.0 / DAYS_PER_YEAR

    joined: list[tuple[float, bool]] = []
    lower = youngest

    for k, (oldest, is_at_cycle) in enumerate(parts):
        is_short = oldest - lower < day
        if is_short and k < len(parts) - 1:
            continue

        if joined and (is_short or joined[-1][1] == is_at_cycle):
            joined[-1] = (oldest, joined[-1][1])
        else:
            joined.append((oldest, is_at_cycle))

        lower = oldest

    return joined


def _cut(
    increment: VesselIncrement, ages: list[float], time: float
) -> list[VesselIncrement]:
    """
    Cut an increment at ages inside its span.

    Parameters
    ----------
    increment
        Increment cut.
    ages
        Ages the increment is cut at, in years, youngest first.
    time
        Time the ages are read at, in years.

    Returns
    -------
    list[VesselIncrement]
        The parts between the ages, youngest first.
    """
    parts = []
    rest = increment

    for age in ages:
        younger, rest = split_at_age(rest, age, time)
        parts.append(younger)

    parts.append(rest)

    return parts


def _is_unchanged(younger: VesselIncrement, older: VesselIncrement) -> bool:
    """
    Test whether two neighbouring parts of an increment can join as they were cut.

    Parameters
    ----------
    younger
        Younger part.
    older
        Older part.

    Returns
    -------
    bool
        Whether the parts carry one package, charter rate and density of vessels.
    """
    # the older part's count is a difference of the increment's, which keeps its scale
    expected_count = younger.count / younger.age_span * older.age_span
    scale = younger.count + older.count

    return (
        np.array_equal(younger.package_uptake, older.package_uptake)
        and younger.technology_charter_rate == older.technology_charter_rate
        and bool(is_negligible(older.count - expected_count, scale))
    )


def _join(younger: VesselIncrement, older: VesselIncrement) -> VesselIncrement:
    """
    Join two neighbouring parts of an increment into one.

    Parameters
    ----------
    younger
        Younger part.
    older
        Older part, carrying the younger part's package and charter rate.

    Returns
    -------
    VesselIncrement
        The joined increment, entered with the younger part.
    """
    count = younger.count + older.count
    span = younger.age_span + older.age_span

    return replace(younger, count=count, age_span=span)


def _cycle_windows(
    lower: float, upper: float, time_step: float, interval: float
) -> tuple[FloatArray, FloatArray]:
    """
    Return the retrofit-cycle windows that may overlap an age interval.

    Parameters
    ----------
    lower
        Youngest age of the interval, in years.
    upper
        Oldest age of the interval, in years; not below ``lower``.
    time_step
        Time-step size, in years.
    interval
        Interval between retrofit opportunities, in years.

    Returns
    -------
    tuple[FloatArray, FloatArray]
        Start and end age of each window, in years.
    """
    # windows as long as the retrofit interval join into one from the first cycle on
    if time_step >= interval:
        return np.array([interval]), np.array([np.inf])

    # windows shorter than the retrofit interval, one per cycle: the age interval meets
    # at most two more than its length over the retrofit interval
    first_cycle = max(1, math.floor(lower / interval))
    last_cycle = math.ceil(upper / interval)
    starts = interval * np.arange(first_cycle, last_cycle + 1, dtype=np.float64)

    return starts, starts + time_step


def consolidate_increments(fleet: Fleet, population: float) -> None:
    """
    Merge increments holding vessels of the same ages, drop those negligible.

    The simulation's CPU time grows with the number of increments per vessel type.
    Increments hold the same ages where they entered service at the same time over
    the same span, a vintage. An entry time is set once and copied, never
    accumulated, so the increments of a vintage share it exactly; a span is computed
    by the cuts of the scrapping and the splits, so two histories that cut the same
    ages can leave spans a rounding residual apart.

    Parameters
    ----------
    fleet
        Fleet whose increments are consolidated.
    population
        Number of vessels the fleet counts in the time-step, newbuilds included.
    """
    for v, increments in enumerate(fleet.increments):
        consolidated: list[VesselIncrement] = []

        # the increments are sorted by entry, so those entered together are neighbours
        for _, entrants in groupby(increments, key=attrgetter("entered")):
            for vintage in _group_by_span(list(entrants)):
                count = sum(increment.count for increment in vintage)
                if not is_negligible(count, population):
                    consolidated.append(_merge(vintage))

        fleet.increments[v] = consolidated


def _group_by_span(entrants: list[VesselIncrement]) -> list[list[VesselIncrement]]:
    """
    Group increments entered together into vintages, by their span to rounding.

    An increment joins the first vintage whose first increment, the one ``_merge``
    keeps, spans its ages, so that a vintage cannot drift.

    Parameters
    ----------
    entrants
        Increments of one vessel type that entered service at the same time, in
        fleet order.

    Returns
    -------
    list[list[VesselIncrement]]
        The vintages, each in fleet order, in the order of their first increment.
    """
    vintages: list[list[VesselIncrement]] = []

    for increment in entrants:
        for vintage in vintages:
            if subtract(increment.age_span, vintage[0].age_span) == 0.0:
                vintage.append(increment)
                break
        else:
            vintages.append([increment])

    return vintages


def _merge(vintage: list[VesselIncrement]) -> VesselIncrement:
    """
    Fold the increments of one vintage into the first, weighting by count.

    Parameters
    ----------
    vintage
        Increments of one vessel type and vintage, in fleet order.

    Returns
    -------
    VesselIncrement
        The first increment, holding the vintage's total count and its count-weighted
        package uptake and technology charter rate.
    """
    survivor = vintage[0]

    if len(vintage) == 1:
        return survivor

    counts = [increment.count for increment in vintage]
    uptakes = [increment.package_uptake for increment in vintage]
    charter_rates = [increment.technology_charter_rate for increment in vintage]

    survivor.count = sum(counts)
    survivor.package_uptake = np.average(uptakes, axis=0, weights=counts)
    survivor.technology_charter_rate = float(np.average(charter_rates, weights=counts))

    return survivor
