# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Vintage-stock accounting over asset cohorts, shared by the fleet and fuel domains.

The functions read Increment fields and plain numbers only; each domain builds its
own Increment subclass from what they return.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.nodes.curve import Curve
from navigate.util import find_nearest, find_nearest_index

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.increment import Increment
    from navigate.core.types_ import CurveTableInput
    from navigate.util.types_ import FloatArray, IntArray


def split_by_age(
    count: float, distribution: CurveTableInput, age_range: float
) -> list[tuple[float, float, float]]:
    """
    Split an initial number of assets into age bins, oldest first.

    A Curve distribution sets the ages and the share of each; a number spreads the
    assets evenly over yearly bins across the age range, and an age range under a
    year leaves no bin.

    Parameters
    ----------
    count
        Number of assets split.
    distribution
        Initial age distribution of the assets.
    age_range
        Age range the even spread covers, in years.

    Returns
    -------
    list[tuple[float, float, float]]
        The age and width of each bin, in years, and the number of assets in it.
    """
    if isinstance(distribution, Curve):
        ages = distribution.x[::-1]
        multipliers = count * distribution.y[::-1]

    else:
        bins = int(age_range)
        ages = np.linspace(age_range - 1.0, 0.0, bins)
        multipliers = [count / bins for _ in range(bins)]

    if not ages.size:
        return []

    # the oldest bin is assumed to have entered over a year
    spans = np.insert(ages[:-1] - ages[1:], 0, 1.0)

    return list(zip(ages, spans, multipliers, strict=True))


def extends_past(increment: Increment, boundary: float) -> bool:
    """
    Return whether an increment's age span reaches past an age boundary.

    Parameters
    ----------
    increment
        Increment tested.
    boundary
        Age the increment is split at, in years.

    Returns
    -------
    bool
        Whether the oldest end of the span lies past the boundary.
    """
    return increment.age + increment.age_span > boundary


def calculate_share_below(increment: Increment, boundary: float) -> float:
    """
    Return the share of an increment younger than an age boundary it extends past.

    The assets of an increment are spread uniformly over its age span.

    Parameters
    ----------
    increment
        Increment split.
    boundary
        Age the increment is split at, in years.

    Returns
    -------
    float
        Share of the increment's assets younger than the boundary.
    """
    return (boundary - increment.age) / increment.age_span


def find_insertion_index(increments: Sequence[Increment], age: float) -> int:
    """
    Return where an increment of an age goes in an oldest-first increment list.

    It goes after the increments of equal age, so the list stays sorted.

    Parameters
    ----------
    increments
        Increments sorted oldest first.
    age
        Age of the increment inserted, in years.

    Returns
    -------
    int
        Index to insert the increment at.
    """
    if not increments:
        return 0

    ages = np.array([increment.age for increment in increments])
    return int(np.searchsorted(-ages, -age, side="right"))


def get_increment_origin_index(
    years: FloatArray, current_year: float, age: float
) -> int:
    """
    Find the time-step index at which an increment entered the simulation.

    The increment (vessel or plant) is treated as having entered 'age' years
    before current_year. An entity present at the initialization of the node
    gets index 0 - the best available approximation, as historical data is
    unavailable.

    Parameters
    ----------
    years
        Simulation timeline in years.
    current_year
        The current year (years[idx]).
    age
        Age of the increment in years.

    Returns
    -------
    int
        Time-step index.
    """
    return find_nearest_index(years, current_year - age)


def get_increment_origin_indexes(
    years: FloatArray, current_year: float, ages: FloatArray
) -> IntArray:
    """
    Find the time-step indexes at which increments entered the simulation.

    Array counterpart of `get_increment_origin_index`, one index per age.

    Parameters
    ----------
    years
        Simulation timeline in years.
    current_year
        The current year (years[idx]).
    ages
        Ages of the increments in years.

    Returns
    -------
    IntArray
        Time-step indexes, one per age.
    """
    return find_nearest(years, current_year - ages)
