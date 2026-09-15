# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Calendar constants and converters from numpy dates to float day and year axes."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np

if TYPE_CHECKING:
    from navigate.util.arrays import (
        DateArray,
        FloatArray,
        FloatLike,
        IntArray,
        TimedeltaArray,
    )

# calendar durations in days
DAY = 1.0
MONTH = 30.4375  # 365.25 / 12
YEAR = 365.25


@overload
def timedelta_to_days(delta: np.timedelta64) -> float: ...
@overload
def timedelta_to_days(delta: TimedeltaArray) -> FloatArray: ...
def timedelta_to_days(delta: np.timedelta64 | TimedeltaArray) -> FloatLike:
    """
    Convert a timedelta to days.

    Parameters
    ----------
    delta
        Difference between two np.datetime64 objects, scalar or array.

    Returns
    -------
    FloatLike
        Timedelta in days, mirroring the input's scalar- or arrayness.
    """
    return delta.astype(np.float64)


def _timedelta_to_years(delta: TimedeltaArray) -> FloatArray:
    """
    Convert a timedelta array to years.

    Parameters
    ----------
    delta
        Differences between np.datetime64 objects.

    Returns
    -------
    FloatArray
        Timedeltas in years.
    """
    return timedelta_to_days(delta) / YEAR


def dates_to_days(dates: DateArray) -> FloatArray:
    """
    Convert a numpy date array to an array of days.

    Parameters
    ----------
    dates
        Array of dates in numpy datetime64[D] format.

    Returns
    -------
    FloatArray
        Array of days since the first date.
    """
    deltas: TimedeltaArray = dates - dates[0]
    return timedelta_to_days(deltas)


def dates_to_years(dates: DateArray) -> FloatArray:
    """
    Convert a numpy date array to an array of years.

    Parameters
    ----------
    dates
        Array of dates in numpy datetime64[D] format.

    Returns
    -------
    FloatArray
        Array of years since the first date.
    """
    deltas: TimedeltaArray = dates - dates[0]
    return _timedelta_to_years(deltas)


def decompose_dates(dates: DateArray) -> tuple[IntArray, IntArray, IntArray]:
    """
    Decompose a numpy date array into three arrays: years, months and days (integers).

    Parameters
    ----------
    dates
        Array of dates in numpy datetime64[D] format.

    Returns
    -------
    tuple[IntArray, IntArray, IntArray]
        Arrays containing years, months and days as integers.
    """
    years = dates.astype("datetime64[Y]").astype(int) + 1970
    months = dates.astype("datetime64[M]").astype(int) % 12 + 1
    days = (dates - dates.astype("datetime64[M]")).astype(int) + 1

    return years, months, days
