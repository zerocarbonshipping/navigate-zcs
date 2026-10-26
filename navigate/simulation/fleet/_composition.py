# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The fleet's increments: vessel counts, retrofit cycles and the trade they carry."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from navigate.core.increment import VesselIncrement
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray


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
        Trade capacity of the fleet, cargo-miles/year.
    """
    multipliers = get_multipliers(fleet)
    cargo_miles = extract_cargo_miles(fleet.vessels, idx)

    return float(np.dot(multipliers, cargo_miles))


def get_multipliers(fleet: Fleet) -> list[float]:
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
    return [get_multiplier(fleet, v) for v in range(len(fleet.increments))]


def get_multiplier(fleet: Fleet, vessel_idx: int) -> float:
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
    return sum(inc.multiplier for inc in fleet.increments[vessel_idx])


def extract_cargo_miles(vessels: list[Vessel], idx: int) -> FloatArray:
    """
    Extract each vessel's cargo-miles at a single time-step index.

    Parameters
    ----------
    vessels
        Vessels to extract cargo-miles for.
    idx
        Time-step index.

    Returns
    -------
    FloatArray
        Cargo-miles of one vessel of each type, cargo-miles/year.
    """
    return np.array([vessel.expectation.get_cargo_miles(idx) for vessel in vessels])


def extract_cargo_miles_timeline(vessels: list[Vessel], idx: slice) -> list[FloatArray]:
    """
    Extract each vessel's cargo-miles across a slice of the timeline.

    Parameters
    ----------
    vessels
        Vessels to extract cargo-miles for.
    idx
        Timeline slice.

    Returns
    -------
    list[FloatArray]
        Cargo-miles of one vessel of each type over the slice, cargo-miles/year.
    """
    return [np.asarray(vessel.expectation.get_cargo_miles(idx)) for vessel in vessels]


def is_retrofit_cycle(age: float, retrofit_frequency: float, time_step: float) -> bool:
    """
    Return whether an increment is at a retrofit cycle.

    It is when its age lies within one time-step past a multiple of the retrofit
    frequency, and it is older than one time-step. The age and time-step are compared
    at two decimals.

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
    age = round(age, 2)
    time_step = round(time_step, 2)
    return age > time_step and age % retrofit_frequency < time_step


def consolidate_increments(fleet: Fleet) -> None:
    """
    Merge increments of equal age and age span, and drop those below 1e-3 vessels.

    The simulation's CPU time grows with the number of increments per vessel type.

    Parameters
    ----------
    fleet
        Fleet whose increments are consolidated.
    """
    for v, increments in enumerate(fleet.increments):
        cohorts: dict[tuple[float, float], list[VesselIncrement]] = {}

        for increment in increments:
            key = (increment.age, increment.age_span)
            cohorts.setdefault(key, []).append(increment)

        consolidated: list[VesselIncrement] = []

        for cohort in cohorts.values():
            if sum(inc.multiplier for inc in cohort) >= 1e-3:
                consolidated.append(_merge(cohort))

        fleet.increments[v] = consolidated


def _merge(cohort: list[VesselIncrement]) -> VesselIncrement:
    """
    Fold a cohort into its first increment, weighting by multiplier.

    Parameters
    ----------
    cohort
        Increments of one vessel type with equal age and age span, in fleet order.

    Returns
    -------
    VesselIncrement
        The first increment, holding the cohort's total multiplier and its
        multiplier-weighted package uptake and technology charter rate.
    """
    survivor = cohort[0]

    if len(cohort) == 1:
        return survivor

    weights = [inc.multiplier for inc in cohort]
    uptakes = [inc.package_uptake for inc in cohort]
    charter_rates = [inc.technology_charter_rate for inc in cohort]

    survivor.multiplier = sum(weights)
    survivor.package_uptake = np.average(uptakes, axis=0, weights=weights)
    survivor.technology_charter_rate = float(np.average(charter_rates, weights=weights))

    return survivor
