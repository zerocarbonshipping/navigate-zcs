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

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.increment import Increment
    from navigate.core.types_ import CurveTableInput
    from navigate.util.types_ import FloatArray


def split_by_age(
    multiplier: float, distribution: CurveTableInput, age_range: float
) -> tuple[FloatArray, FloatArray, FloatArray | list[float]]:
    """
    Split an initial number of assets into age bins, oldest first.

    A Curve distribution sets the ages and the share of each; a number spreads the
    assets evenly over yearly bins across the age range.

    Parameters
    ----------
    multiplier
        Number of assets split.
    distribution
        Initial age distribution of the assets.
    age_range
        Age range the even spread covers, in years.

    Returns
    -------
    tuple[FloatArray, FloatArray, FloatArray | list[float]]
        The age of each bin and its width, in years, and the number of assets in it.
    """
    if isinstance(distribution, Curve):
        ages = distribution.x[::-1]
        multipliers = multiplier * distribution.y[::-1]

    else:
        bins = int(age_range)
        ages = np.linspace(age_range - 1.0, 0.0, bins)
        multipliers = [multiplier / bins for _ in range(bins)]

    # the oldest bin is assumed to have entered over a year
    spans = np.insert(ages[:-1] - ages[1:], 0, 1.0)

    return ages, spans, multipliers


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
