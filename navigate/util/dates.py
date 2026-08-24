# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

DAY = 1.
MONTH = 30.4375   # equivalent to 365.25/12 = 30.4375 days
YEAR = 365.25    # equivalent to 365.25 days


def timedelta_to_days(delta):
    """

    Parameters
    ----------
    delta : np.timedelta64
        Difference between two np.datetime64 objects.

    Returns
    -------
    np.ndarray :
        Timedelta in years.
    """

    return delta.astype(np.float64)


def _timedelta_to_years(delta):
    """

    Parameters
    ----------
    delta : np.timedelta64
        Difference between two np.datetime64 objects.

    Returns
    -------
    np.ndarray :
        Timedelta in years.
    """

    return timedelta_to_days(delta) / YEAR


def dates_to_days(dates):
    """
    Converts a numpy date array to an array of days.

    Parameters
    ----------
    dates : np.ndarray
        Array of dates in numpy datetime64[D] format.

    Returns
    -------
    np.ndarray
        Array of days in numpy float64 format.
    """

    return timedelta_to_days(dates - dates[0])


def dates_to_years(dates):
    """
    Converts a numpy date array to an array of days.

    Parameters
    ----------
    dates : np.ndarray
        Array of dates in numpy datetime64[D] format.

    Returns
    -------
    np.ndarray
        Array of days in numpy float64 format.
    """

    return _timedelta_to_years(dates - dates[0])


def decompose_dates(dates):
    """
    Decompose a numpy date array into three arrays containing the years, months and days (integers).

    Parameters
    ----------
    dates : np.ndarray
        Array of dates in numpy datetime64[D] format.

    Returns
    -------
    tuple[np.ndarray, np.ndarray, np.ndarray]
        Arrays containing years, months and days as integers.
    """

    years = dates.astype('datetime64[Y]').astype(int) + 1970
    months = dates.astype('datetime64[M]').astype(int) % 12 + 1
    days = (dates - dates.astype('datetime64[M]')).astype(int) + 1

    return years, months, days
