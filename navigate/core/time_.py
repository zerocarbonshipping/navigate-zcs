# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.util import YEAR


def calculate_inertia(inertia, time_step):
    """

    Parameters
    ----------
    inertia : float
        Inertia, fraction/year.
    time_step : float
        Current time-step size.

    Returns
    -------
    float
        Fraction of previous time-steps value(s) that should be continued.
    """

    return inertia ** (time_step / YEAR)


def calculate_compound_growth(initial, growth, timeline):
    """
    Calculates the continuous compound growth of a property.
    The formula assumes that the growth is forward-looking, meaning that the growth at index t is applied over the
    time-step from t to t+1.

    Parameters
    ----------
    initial : float
        Initial value.
    growth : np.ndarray
        Instantaneous growth rate with values corresponding to the timeline, fraction/year
    timeline : np.ndarray
        Timeline of the simulation.

    Returns
    -------
    np.ndarray
        Resulting compounded growth.
    """

    # calculate the continuous compound growth
    continuous_growth = np.log(1. + growth)
    compound_growth = np.cumsum(continuous_growth[:-1] * np.diff(timeline) / YEAR)

    value = np.full_like(timeline, initial)
    value[1:] *= np.exp(compound_growth)

    return value
