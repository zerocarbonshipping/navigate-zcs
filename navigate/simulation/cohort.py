# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Vintage-stock accounting over the asset cohorts of the fleet and fuel domains.

What a domain adds to its cohorts, such as the technology a vessel carries or the time
a plant was decided, and building its Increment subclass stay in that domain.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.nodes.curve import Curve
from navigate.util import divide_nonzero, drop_negligible

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


def calculate_share_below(
    lower: FloatLike, upper: FloatLike, point: FloatLike
) -> FloatArray:
    """
    Calculate the share of a uniform interval lying below a point.

    The ends and the point carry the rounding of the arithmetic they came from, such
    as an age read off an entry time or a time advanced by steps, so a point within
    rounding of either end, against the larger of the ends, splits nothing off. An
    interval whose ends both lie within rounding of the point has none of it below.

    Parameters
    ----------
    lower
        Lower end of the interval, scalar or array.
    upper
        Upper end of the interval, scalar or array, in the units of the lower end;
        not below it.
    point
        Point the interval is split at, scalar or array, in the units of the ends.

    Returns
    -------
    FloatArray
        Share of the interval below the point: 0.0 at or below the lower end, 1.0
        at or above the upper end, with the broadcast shape of the inputs (0-d for
        scalar inputs).
    """
    scale = np.maximum(np.abs(lower), np.abs(upper))
    below = drop_negligible(point - lower, scale)
    above = drop_negligible(upper - point, scale)

    # the point lies inside an interval only where the interval is positive
    inside = divide_nonzero(below, upper - lower)
    shares: FloatArray = np.select([below <= 0.0, above <= 0.0], [0.0, 1.0], inside)

    return shares


def calculate_share_younger(increment: Increment, age: float, time: float) -> float:
    """
    Calculate the share of an increment younger than an age at a time.

    The assets of an increment are spread uniformly over its age span. Its ages carry
    the rounding of the subtraction they are read off, and a pipeline plant's entry
    that of the lead time it was planned ahead by, so an age within rounding of
    either end of the span splits nothing off.

    Parameters
    ----------
    increment
        Increment split.
    age
        Age the increment is split at, in years.
    time
        Time the increment's ages are read at, in years.

    Returns
    -------
    float
        Share of the increment's assets younger than the age: 0.0 for an increment
        at or past it, 1.0 for one wholly younger.
    """
    youngest = increment.youngest_age(time)
    oldest = increment.oldest_age(time)

    return float(calculate_share_below(youngest, oldest, age))


def split_at_age[I: Increment](increment: I, age: float, time: float) -> tuple[I, I]:
    """
    Split an increment at an age inside its span into its younger and older part.

    The assets are spread uniformly over the span, so each part holds the share of
    the count its ages span, and both carry the increment's other fields.

    Parameters
    ----------
    increment
        Increment split.
    age
        Age the increment is split at, in years.
    time
        Time the age is read at, in years.

    Returns
    -------
    tuple[I, I]
        The part younger than the age and the part older.
    """
    younger_span = age - increment.youngest_age(time)
    share = younger_span / increment.age_span

    younger = replace(increment, count=increment.count * share, age_span=younger_span)
    older = replace(
        increment,
        count=increment.count - younger.count,
        entered=time - age,
        age_span=increment.age_span - younger_span,
    )

    return younger, older


def retire_past_age[I: Increment](
    increments: list[I], age: float, time: float
) -> tuple[list[I], float]:
    """
    Retire the assets of increments past an age, such as their lifetime.

    An increment spanning the age keeps its part younger than the age, its span then
    ending at the age; one at or past the age, to rounding, retires whole.

    Parameters
    ----------
    increments
        Increments of one asset type.
    age
        Age the assets retire at, in years.
    time
        Time the ages are read at, in years.

    Returns
    -------
    tuple[list[I], float]
        The increments left, in their order, and the number of assets retired.
    """
    kept = []
    retired = 0.0

    for increment in increments:
        share = calculate_share_younger(increment, age, time)

        if share == 1.0:
            kept.append(increment)

        elif share == 0.0:
            retired += increment.count

        else:
            younger, older = split_at_age(increment, age, time)
            kept.append(younger)
            retired += older.count

    return kept, retired


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
