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
        TimedeltaArray,
    )

YEAR = 365.25  # calendar year in days


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
