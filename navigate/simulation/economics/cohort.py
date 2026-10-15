# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The initial asset cohorts, split by age for the fleet and fuel domains."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.nodes.curve import Curve

if TYPE_CHECKING:
    from navigate.core import Scalar


def discretize_initial_cohorts(
    distribution: Scalar | Curve | None, lifetime: float, total: float
) -> list[tuple[float, float, float]]:
    """
    Split an initial asset count into cohorts by age, oldest first.

    A Curve distribution gives the cohort ages (x) and their shares of the total (y).
    Without one, the total is spread evenly over one cohort per whole year of
    lifetime.

    Parameters
    ----------
    distribution
        Initial age distribution of the asset type, if one is given.
    lifetime
        Lifetime the even split spreads the cohorts over, in years.
    total
        Number of assets to split.

    Returns
    -------
    list[tuple[float, float, float]]
        Age and age span, in years, and multiplier of each cohort.
    """
    # the positive form also gives no cohorts for a NaN total
    if not total > 0.0:
        return []

    if isinstance(distribution, Curve):
        ages = distribution.x[::-1]
        multipliers = [total * share for share in distribution.y[::-1]]

    else:
        count = int(lifetime)

        # a lifetime under one year holds no whole cohort
        if count == 0:
            return []

        ages = np.linspace(lifetime - 1.0, 0.0, count)
        multipliers = [total / count] * count

    # the oldest cohort is taken to have entered service over one year
    spans = np.insert(ages[:-1] - ages[1:], 0, 1.0)

    return list(zip(ages.tolist(), spans.tolist(), multipliers, strict=True))
