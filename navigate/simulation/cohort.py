# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Vintage-stock accounting over the asset cohorts of the fleet and fuel domains.

What a domain adds to its cohorts, such as the vessels scrapped past the lifetime or
the time since a plant was decided, and building its Increment subclass stay in that
domain.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.nodes.curve import Curve
from navigate.util import find_nearest_index, find_nearest_indices, is_negligible

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.increment import Increment
    from navigate.core.types_ import CurveTableInput
    from navigate.util.types_ import FloatArray, FloatLike, IntArray


def split_by_age(
    total_count: float, distribution: CurveTableInput, age_range: float
) -> list[tuple[float, float, float]]:
    """
    Split an initial number of assets into age bins, oldest first.

    A Curve distribution sets the ages and the share of each; a number spreads the
    assets evenly over yearly bins across the age range, and an age range under a
    year leaves no bin.

    Parameters
    ----------
    total_count
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
        counts = total_count * distribution.y[::-1]

    else:
        bins = int(age_range)
        ages = np.linspace(age_range - 1.0, 0.0, bins)
        counts = [total_count / bins for _ in range(bins)]

    if not ages.size:
        return []

    # the oldest bin is assumed to have entered over a year
    spans = np.insert(ages[:-1] - ages[1:], 0, 1.0)

    return list(zip(ages, spans, counts, strict=True))


def calculate_share_below(increment: Increment, boundary: float) -> float:
    """
    Return the share of an increment younger than an age boundary.

    The assets of an increment are spread uniformly over its age span. The ages carry
    the rounding of the steps they were aged by, so a boundary within rounding of
    either end of the span, against the larger of the ends, splits nothing off.

    Parameters
    ----------
    increment
        Increment split.
    boundary
        Age the increment is split at, in years.

    Returns
    -------
    float
        Share of the increment's assets younger than the boundary: 0.0 for an
        increment at or past it, 1.0 for one wholly younger.
    """
    youngest = increment.age
    oldest = increment.age + increment.age_span
    scale = max(abs(youngest), abs(oldest))

    below = boundary - youngest
    above = oldest - boundary

    if below <= 0.0 or is_negligible(below, scale):
        return 0.0

    if above <= 0.0 or is_negligible(above, scale):
        return 1.0

    # the boundary lies inside the span, which is then positive
    return below / increment.age_span


def calculate_retired_share(
    retirement: FloatLike, window: float, times: FloatLike
) -> FloatArray:
    """
    Calculate the share of a cohort retired by the given times.

    The cohort retires uniformly over the window up to its retirement; a window of
    zero retires it at once at the retirement. The times carry the rounding of the
    steps they were advanced by, so a time within rounding of either end of the
    window, against the larger of the ends, retires none or all of the cohort.

    Parameters
    ----------
    retirement
        Time the last of the cohort retires at: one for all times, or one per time.
    window
        Window over which the cohort retires, in the units of the retirement.
    times
        Times the share is evaluated at, in the units of the retirement.

    Returns
    -------
    FloatArray
        Share of the cohort retired by each of the times.
    """
    if window == 0.0:
        return np.heaviside(times - retirement, 1.0)

    start = retirement - window
    scale = np.maximum(np.abs(start), np.abs(retirement))

    elapsed = times - start
    remaining = retirement - times

    retired = np.clip(elapsed / window, 0.0, 1.0)
    retired = np.where(is_negligible(remaining, scale), 1.0, retired)

    return np.where(is_negligible(elapsed, scale), 0.0, retired)


def find_insertion_index(increments: Sequence[Increment], age: float) -> int:
    """
    Find where an increment of a given age goes in a list sorted oldest first.

    It goes after any increment of equal age.

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
    ages = np.array([increment.age for increment in increments])
    return int(np.searchsorted(-ages, -age, side="right"))


def find_origin_index(years: FloatArray, current_year: float, age: float) -> int:
    """
    Find the time-step index at which an increment entered the simulation.

    The increment is treated as having entered 'age' years before current_year.
    An increment of the initial cohorts gets index 0 - the best available
    approximation, as historical data is unavailable.

    Parameters
    ----------
    years
        Simulation timeline, in years.
    current_year
        Current year of the simulation.
    age
        Age of the increment, in years.

    Returns
    -------
    int
        Time-step index.
    """
    return find_nearest_index(years, current_year - age)


def find_origin_indexes(
    years: FloatArray, current_year: float, ages: FloatArray
) -> IntArray:
    """
    Find the time-step indexes at which increments entered the simulation.

    Array counterpart of `find_origin_index`, one index per age.

    Parameters
    ----------
    years
        Simulation timeline, in years.
    current_year
        Current year of the simulation.
    ages
        Ages of the increments, in years.

    Returns
    -------
    IntArray
        Time-step indexes, one per age.
    """
    return find_nearest_indices(years, current_year - ages)
