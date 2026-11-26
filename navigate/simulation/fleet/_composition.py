# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The fleet's increments: vessel counts, retrofit cycles and the trade they carry."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.util import drop_negligible, is_negligible

if TYPE_CHECKING:
    from navigate.core.increment import VesselIncrement
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import BoolArray, FloatArray


@dataclass(frozen=True, slots=True)
class CycleSlice:
    """
    The vessels of an increment at a retrofit cycle.

    They lie within the lifetime and at or above a minimum age.

    Parameters
    ----------
    share
        Share of the increment's vessels in the slice.
    mean_age
        Mean age of those vessels, in years.
    """

    share: float
    mean_age: float


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


def calculate_cycle_slice(
    increment: VesselIncrement,
    time: float,
    time_step: float,
    frequency: float,
    lifetime: float,
    minimum_age: float,
) -> CycleSlice | None:
    """
    Calculate the slice of an increment's vessels at a retrofit cycle.

    A vessel is at a cycle in the time-step in which its age reached a positive
    multiple k * f of the retrofit frequency f: at the end of the step its age lies in
    ``[k * f, k * f + min(time_step, f))``, the windows no longer than f so that they
    do not overlap and a vessel counts once per step. The slice is the part of the
    increment's age span in a window, below the lifetime and at or above the minimum
    age. An overlap within rounding of an end of a window, against the larger of the
    span's ends, holds no vessels.

    The increment's size before scrapping past the lifetime is spread uniformly over
    its age span (``calculate_survivors`` in ``fleet/scrapping.py``), so the slice
    holds its length's share of that size, whether or not this time-step's scrapping
    has run.

    Parameters
    ----------
    increment
        Increment of a vessel type.
    time
        Time at the end of the time-step, in years.
    time_step
        Time-step size, in years.
    frequency
        Interval between retrofit opportunities, in years.
    lifetime
        Lifetime of the vessel type, in years.
    minimum_age
        Age below which a vessel is not eligible, in years.

    Returns
    -------
    CycleSlice | None
        Share and mean age of the slice, or None where it holds no vessels.
    """
    if increment.count <= 0.0:
        return None

    span = increment.age_span
    youngest = increment.youngest_age(time)
    oldest = youngest + span
    scale = max(abs(youngest), abs(oldest))

    lower = max(youngest, minimum_age)
    upper = min(oldest, lifetime)
    if drop_negligible(upper - lower, scale) <= 0.0:
        return None

    window_starts, window_ends = _cycle_windows(lower, upper, time_step, frequency)
    starts = np.maximum(window_starts, lower)
    ends = np.minimum(window_ends, upper)
    lengths = np.maximum(drop_negligible(ends - starts, scale), 0.0)

    length = float(np.sum(lengths))
    if length <= 0.0:
        return None

    # a slice within rounding of the whole span holds all of its vessels
    missing = float(drop_negligible(span - length, scale))
    size = increment.count + increment.scrapped_past_lifetime
    eligible = size * (1.0 - missing / span)
    mean_age = float(np.sum(lengths * (starts + ends))) / (2.0 * length)

    # converted vessels, and round-off, can leave the increment scrapped beyond this
    # lifetime's share, as in calculate_survivors, so the slice is capped at its count
    share = min(eligible / increment.count, 1.0)

    return CycleSlice(share, mean_age)


def _cycle_windows(
    lower: float, upper: float, time_step: float, frequency: float
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
    frequency
        Interval between retrofit opportunities, in years.

    Returns
    -------
    tuple[FloatArray, FloatArray]
        Start and end age of each window, in years.
    """
    # windows as long as the frequency join into one from the first cycle on
    if time_step >= frequency:
        return np.array([frequency]), np.array([np.inf])

    # windows shorter than the frequency, one per cycle: the interval meets at most
    # two more than its length over the frequency
    first_cycle = max(1, math.floor(lower / frequency))
    last_cycle = math.ceil(upper / frequency)
    starts = frequency * np.arange(first_cycle, last_cycle + 1, dtype=np.float64)

    return starts, starts + time_step


def consolidate_increments(fleet: Fleet) -> None:
    """
    Merge increments of one vintage, drop those below 1e-3 vessels.

    The simulation's CPU time grows with the number of increments per vessel type.
    Increments are of one vintage where they entered service at the same time over
    the same span: both are set once and copied, never accumulated, and the initial
    vintages are aligned across vessel types, so they are equal floats.

    Parameters
    ----------
    fleet
        Fleet whose increments are consolidated.
    """
    for v, increments in enumerate(fleet.increments):
        # cohorts in fleet order, each folded into its first increment
        cohorts: dict[tuple[float, float], list[VesselIncrement]] = {}

        for increment in increments:
            vintage = (increment.entered, increment.age_span)
            cohorts.setdefault(vintage, []).append(increment)

        consolidated: list[VesselIncrement] = []

        for cohort in cohorts.values():
            if sum(increment.count for increment in cohort) >= 1e-3:
                consolidated.append(_merge(cohort))

        fleet.increments[v] = consolidated


def _merge(cohort: list[VesselIncrement]) -> VesselIncrement:
    """
    Fold a cohort into its first increment, weighting by count.

    Parameters
    ----------
    cohort
        Increments of one vessel type and vintage, in fleet order.

    Returns
    -------
    VesselIncrement
        The first increment, holding the cohort's total count and vessels scrapped
        past the lifetime, and its count-weighted package uptake and technology
        charter rate.
    """
    survivor = cohort[0]

    if len(cohort) == 1:
        return survivor

    counts = [increment.count for increment in cohort]
    uptakes = [increment.package_uptake for increment in cohort]
    charter_rates = [increment.technology_charter_rate for increment in cohort]
    scrapped = [increment.scrapped_past_lifetime for increment in cohort]

    survivor.count = sum(counts)
    survivor.scrapped_past_lifetime = sum(scrapped)
    survivor.package_uptake = np.average(uptakes, axis=0, weights=counts)
    survivor.technology_charter_rate = float(np.average(charter_rates, weights=counts))

    return survivor
