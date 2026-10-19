# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Vessel counts per type in the fleet's increments and the trade they can carry."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
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


def clean_up_multipliers(fleet: Fleet) -> None:
    """
    Merge increments of equal age and age span, and drop those below 1e-3 vessels.

    The simulation's CPU time grows with the number of increments per vessel type.

    Parameters
    ----------
    fleet
        Fleet whose increments are cleaned up.
    """
    for v in range(len(fleet.vessels)):
        incs = fleet.increments[v]
        n = len(incs)
        available = [True] * n

        for i in range(n):
            if not available[i]:
                continue

            age_i = incs[i].age
            dt_i = incs[i].age_span

            matching = [
                j
                for j in range(n)
                if j != i
                and available[j]
                and incs[j].age == age_i
                and incs[j].age_span == dt_i
            ]

            if matching:
                merge_indices = [*matching, i]
                package_uptake = np.zeros_like(fleet.newbuild_package_uptake[v])
                charter_rate = 0.0

                for j in merge_indices:
                    package_uptake += incs[j].multiplier * incs[j].package_uptake
                    charter_rate += incs[j].multiplier * incs[j].technology_charter_rate

                incs[i].multiplier += sum(incs[j].multiplier for j in matching)
                incs[i].package_uptake = package_uptake / incs[i].multiplier
                incs[i].technology_charter_rate = charter_rate / incs[i].multiplier

                # a zeroed increment is dropped by the filter below
                for j in matching:
                    incs[j].multiplier = 0.0
                    available[j] = False

    for v in range(len(fleet.vessels)):
        fleet.increments[v] = [
            inc for inc in fleet.increments[v] if inc.multiplier >= 1e-3
        ]
