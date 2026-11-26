# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The fleet's increments: vessel counts, retrofit cycles and the trade they carry."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from navigate.util import is_negligible, snap_to_whole, subtract

if TYPE_CHECKING:
    from navigate.core.increment import VesselIncrement
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import BoolArray, FloatArray


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


def is_retrofit_cycle(age: float, retrofit_frequency: float, time_step: float) -> bool:
    """
    Return whether an increment is at a retrofit cycle.

    It is when the time-step that brought it to its age reached or passed a multiple
    of the retrofit frequency, and it is older than one time-step. An age a
    floating-point residual short of a multiple counts as on it.

    Parameters
    ----------
    age
        Age of the increment, in years.
    retrofit_frequency
        Interval between retrofit opportunities, in years.
    time_step
        Time-step size, in years.

    Returns
    -------
    bool
        Whether the increment is at a retrofit cycle.
    """
    if float(subtract(age, time_step)) <= 0.0:
        return False

    scale = age / retrofit_frequency
    cycles_at_start = snap_to_whole((age - time_step) / retrofit_frequency, scale)
    cycles_at_end = snap_to_whole(age / retrofit_frequency, scale)
    return math.floor(cycles_at_end) > math.floor(cycles_at_start)


def consolidate_increments(fleet: Fleet) -> None:
    """
    Merge increments of one vintage, drop those below 1e-3 vessels.

    The simulation's CPU time grows with the number of increments per vessel type.
    Increments are of one vintage where they entered service at the same time over
    the same span: both are set once and copied, never accumulated, so they are equal
    floats.

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
