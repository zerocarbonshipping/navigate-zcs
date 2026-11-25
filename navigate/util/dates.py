# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The converter from numpy dates to calendar years, and the average days per year."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeIs

import numpy as np

if TYPE_CHECKING:
    from navigate.util.types_ import DateArray, FloatArray

# average days in a year, for a physical rate given per day; never calendar arithmetic
DAYS_PER_YEAR = 365.25


def is_date_array(values: FloatArray | DateArray) -> TypeIs[DateArray]:
    """
    Test whether an array holds dates rather than floats.

    Parameters
    ----------
    values
        Array that is either numeric or of numpy dates.

    Returns
    -------
    TypeIs[DateArray]
        Whether the array holds dates.
    """
    return np.issubdtype(values.dtype, np.datetime64)


def dates_to_years(dates: DateArray, origin: np.datetime64) -> FloatArray:
    """
    Convert dates to calendar years since an origin.

    A date counts as its year plus the fraction of that year passed before it, so
    1 January is a whole year and every calendar year, leap or not, is one year long.

    Parameters
    ----------
    dates
        Dates in numpy ``datetime64`` format.
    origin
        Date counted as zero.

    Returns
    -------
    FloatArray
        Calendar years since the origin.
    """
    years, fractions = _split_years(dates)
    origin_years, origin_fractions = _split_years(np.array([origin]))

    # whole and fractional years are subtracted apart, so whole years stay exact
    return (years - origin_years) + (fractions - origin_fractions)


def _split_years(dates: DateArray) -> tuple[FloatArray, FloatArray]:
    """
    Split dates into their calendar year and the fraction of that year before them.

    The years count from 1970, numpy's epoch, which cancels in the differences that
    ``dates_to_years`` takes.
    """
    years = dates.astype("datetime64[Y]")
    starts = years.astype("datetime64[D]")
    ends = (years + np.timedelta64(1, "Y")).astype("datetime64[D]")

    return years.astype(float), (dates - starts) / (ends - starts)
