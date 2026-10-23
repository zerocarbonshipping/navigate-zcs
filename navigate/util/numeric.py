# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Numeric helpers: safe division, index lookup, growth, smoothing."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

from navigate.util.dates import YEAR

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray, IntArray

ROUND_OFF = 5  # decimals
TOLERANCE = 10 ** (-ROUND_OFF)


def divide_nonzero(
    numerator: npt.ArrayLike, denominator: npt.ArrayLike, default: float = 0.0
) -> FloatArray:
    """
    Divide the numerator by the denominator where it is positive, defaults elsewhere.

    Parameters
    ----------
    numerator
        Numerator, scalar or array.
    denominator
        Denominator, scalar or array.
    default
        Value used where the denominator is not positive.

    Returns
    -------
    FloatArray
        Quotients with the broadcast shape of the inputs (0-d for scalar inputs).
    """
    numerator = np.asarray(numerator)
    denominator = np.asarray(denominator)

    # allocate the broadcast shape of both inputs so it fits np.divide's out=
    dtype = np.result_type(numerator, denominator)
    shape = np.broadcast(numerator, denominator).shape
    quotients = np.full(shape, default, dtype=dtype)

    # entries excluded by where= keep the prefilled default
    np.divide(numerator, denominator, out=quotients, where=denominator > 0.0)
    return quotients


def step_lengths(timeline: FloatArray) -> FloatArray:
    """
    Length of the time step ending at each date, the first a year long as in the run.

    Parameters
    ----------
    timeline
        Dates of the simulation, in years.

    Returns
    -------
    FloatArray
        Length of each step, in years, one per date.
    """
    return np.insert(np.diff(timeline), 0, 1.0)


def is_strictly_increasing(values: FloatArray) -> bool:
    """
    Test whether every value exceeds the one before it.

    Parameters
    ----------
    values
        Values to test, in order, such as the points of a table axis.

    Returns
    -------
    bool
        Whether ``values`` is strictly increasing.
    """
    return not np.any(np.diff(values) <= 0)


def is_nondecreasing(values: FloatArray) -> bool:
    """
    Test whether no value falls below the one before it.

    Parameters
    ----------
    values
        Values to test, in order.

    Returns
    -------
    bool
        Whether ``values`` is nondecreasing.
    """
    return not np.any(np.diff(values) < 0)


def interpolate_yearly_flow(yearly_flow: FloatArray, age: float) -> float:
    """
    Interpolate a flow given per whole year of age at a fractional age.

    Parameters
    ----------
    yearly_flow
        Flow at the ages 0, 1, 2, ... years.
    age
        Age to interpolate at, in years; clamped to the flow's ends.

    Returns
    -------
    float
        Flow interpolated at ``age``.
    """
    return np.interp(age, np.arange(yearly_flow.size), yearly_flow)


def find_nearest(grid: FloatArray, queries: FloatArray) -> IntArray:
    """
    Find the index of the grid point nearest to each query.

    Reference: https://stackoverflow.com/questions/2566412/find-nearest-value-in-numpy-array
    Answer by "anthonybell".

    Parameters
    ----------
    grid
        Points to search, sorted ascending.
    queries
        Values to find the nearest grid point of.

    Returns
    -------
    IntArray
        Index of the nearest grid point, one per query; a tie goes to the higher.
    """
    last = len(grid) - 1

    indices = np.searchsorted(grid, queries, side="left")
    previous = grid[np.maximum(indices - 1, 0)]
    current = grid[np.minimum(indices, last)]

    is_past_end = indices > last
    is_previous_closer = np.fabs(queries - previous) < np.fabs(queries - current)
    return indices - (is_past_end | is_previous_closer)


def find_nearest_index(grid: FloatArray, query: float) -> int:
    """
    Find the index of the grid point nearest to the query.

    Scalar counterpart of ``find_nearest``.

    Parameters
    ----------
    grid
        Points to search, sorted ascending.
    query
        Value to find the nearest grid point of.

    Returns
    -------
    int
        Index of the nearest grid point.
    """
    return int(find_nearest(grid, np.array([query]))[0])


def derive_smoothing_alpha(idx: int, horizon: float, timeline: FloatArray) -> float:
    """
    Derive the exponential smoothing weight of a time step from a decision horizon.

    A shorter horizon gives a larger alpha, a more responsive belief: with 1-year steps,
    a 5-year horizon gives alpha ~ 0.17 and a 3-year horizon alpha ~ 0.25.

    Parameters
    ----------
    idx
        Current time-step index.
    horizon
        Characteristic decision horizon, in years.
    timeline
        Dates of the simulation, in days.

    Returns
    -------
    float
        Smoothing weight; 1.0, adopting the projection in full, at ``idx = 0``, which
        has no preceding step.
    """
    if idx == 0:
        return 1.0

    dt: float = (timeline[idx] - timeline[idx - 1]) / YEAR
    return 1.0 / (1.0 + horizon / dt)


def update_belief_path(
    raw_path: FloatArray, belief: FloatArray, alpha: float, idx: int
) -> None:
    """
    Smooth a belief path towards the latest raw path, entry by calendar date.

    Match is by calendar index, not look-ahead position, so a given future year's belief
    evolves coherently as successive projections refine it. A belief that has never
    been updated bootstraps to the raw path; every later call blends the new projection
    with the prior, including a prior that is exactly zero, so a price that appears
    after a stretch of zeros ramps up from ``alpha * raw`` rather than being adopted in
    full.

    A NaN entry of ``belief[idx:]`` adopts the raw value and any other entry is
    smoothed, so a caller allocates ``belief`` NaN-filled and passes a ``raw_path``
    without NaN.

    Parameters
    ----------
    raw_path
        Raw forward path from the latest LP solve; entries before ``idx`` are ignored.
    belief
        Previous belief path, NaN where never updated, the length of ``raw_path``;
        updated in place.
    alpha
        Smoothing weight: 1 adopts the raw path in full, 0 keeps the belief.
    idx
        Current time-step index; only entries from it onward are updated.
    """
    forward = np.s_[idx:]
    raw = raw_path[forward]
    prior = belief[forward]

    # exponential smoothing, where an entry with no prior (NaN) adopts the raw value
    smoothed = alpha * raw + (1.0 - alpha) * prior
    belief[forward] = np.where(np.isnan(prior), raw, smoothed)


def calculate_step_inertia(inertia: float, time_step: float) -> float:
    """
    Calculate the fraction of a value continued over one time step.

    Parameters
    ----------
    inertia
        Fraction of a value continued over a year, in fraction/year.
    time_step
        Length of the time step, in days.

    Returns
    -------
    float
        Fraction of the value continued over the time step.
    """
    return math.pow(inertia, time_step / YEAR)


def calculate_compound_growth(
    initial: float, growth: FloatArray, timeline: FloatArray
) -> FloatArray:
    """
    Calculate a value compounding continuously at a yearly growth rate.

    The growth at index t applies over the step from t to t+1.

    Parameters
    ----------
    initial
        Value at the first date.
    growth
        Growth rate at each date of the timeline, in fraction/year.
    timeline
        Dates of the simulation, in days.

    Returns
    -------
    FloatArray
        Value at each date of the timeline.
    """
    rates = np.log(1.0 + growth)
    dt = np.diff(timeline) / YEAR
    exponents = np.cumsum(rates[:-1] * dt)

    values = np.full_like(timeline, initial)
    values[1:] *= np.exp(exponents)

    return values
