# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Vintage-stock accounting over the asset cohorts of the fleet and fuel domains.

What a domain adds to its cohorts, such as the vessels scrapped past the lifetime or
the time a plant was decided, and building its Increment subclass stay in that
domain.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.nodes.curve import Curve
from navigate.util import drop_negligible

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.increment import Increment
    from navigate.core.types_ import CurveTableInput
    from navigate.util.types_ import FloatArray, FloatLike


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


def calculate_share_below(increment: Increment, boundary: float, time: float) -> float:
    """
    Return the share of an increment younger than an age boundary at a time.

    The assets of an increment are spread uniformly over its age span. Its age at the
    time carries the rounding of the subtraction it is read off, and a pipeline
    plant's entry that of the lead time it was planned ahead by, so a boundary within
    rounding of either end of the span, against the larger of the ends, splits
    nothing off.

    Parameters
    ----------
    increment
        Increment split.
    boundary
        Age the increment is split at, in years.
    time
        Time the increment's age is read at, in years.

    Returns
    -------
    float
        Share of the increment's assets younger than the boundary: 0.0 for an
        increment at or past it, 1.0 for one wholly younger.
    """
    youngest = increment.age(time)
    oldest = youngest + increment.age_span
    scale = max(abs(youngest), abs(oldest))

    below = float(drop_negligible(boundary - youngest, scale))
    if below <= 0.0:
        return 0.0

    above = float(drop_negligible(oldest - boundary, scale))
    if above <= 0.0:
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
    start = retirement - window
    scale = np.maximum(np.abs(start), np.abs(retirement))

    elapsed = drop_negligible(times - start, scale)
    remaining = drop_negligible(retirement - times, scale)

    if window == 0.0:
        return np.heaviside(elapsed, 1.0)

    retired = np.where(remaining > 0.0, elapsed / window, 1.0)
    return np.clip(retired, 0.0, 1.0)


def find_insertion_index(increments: Sequence[Increment], entered: float) -> int:
    """
    Find where an increment goes in a list sorted oldest first, by its entry time.

    It goes after any increment that entered at the same time.

    Parameters
    ----------
    increments
        Increments sorted oldest first.
    entered
        Time the increment inserted entered service, in years.

    Returns
    -------
    int
        Index to insert the increment at.
    """
    entries = np.array([increment.entered for increment in increments])
    return int(np.searchsorted(entries, entered, side="right"))
