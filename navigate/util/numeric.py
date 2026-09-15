# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Numeric helpers: safe division, index lookup, growth, smoothing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, overload

import numpy as np
import numpy.typing as npt

from navigate.util.dates import YEAR

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.util.arrays import FloatArray, FloatLike, IntArray

ROUND_OFF = 5  # decimals
TOLERANCE = 10 ** (-ROUND_OFF)


class _SupportsGet(Protocol):
    """Calculator duck type: anything this module evaluates via .get(None, None)."""

    def get(self, x: None, y: None, /) -> FloatLike: ...


type _FloatOrCalculator = float | _SupportsGet


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
    np.divide(numerator, denominator, out=quotients, where=(denominator > 0.0))
    return quotients


def to_numpy(scalars: Iterable[_FloatOrCalculator]) -> FloatArray:
    """
    Evaluate a collection of floats and/or calculators into a numpy array.

    Parameters
    ----------
    scalars
        Floats and/or calculator nodes to evaluate.

    Returns
    -------
    FloatArray
        Evaluated values.
    """
    return np.array([_to_value(scalar) for scalar in scalars])


def _to_value(scalar: _FloatOrCalculator) -> FloatLike:
    return scalar if isinstance(scalar, float) else scalar.get(None, None)


def is_strictly_increasing(values: FloatArray) -> bool:
    """
    Test whether values are strictly increasing.

    Parameters
    ----------
    values
        Vector.

    Returns
    -------
    bool
        Whether 'values' is strictly increasing.
    """
    return not np.any(np.diff(values) <= 0)


def is_non_strictly_increasing(values: FloatArray) -> bool:
    """
    Test whether values are non-strictly increasing.

    Parameters
    ----------
    values
        Vector.

    Returns
    -------
    bool
        Whether 'values' is non-strictly increasing.
    """
    return not np.any(np.diff(values) < 0)


def interpolate_yearly_flow(yearly_flow: FloatArray, age: float) -> float:
    """
    Interpolate a per-year flow at a fractional age in years.

    Parameters
    ----------
    yearly_flow
        Flow values at whole years 0, 1, 2, ...
    age
        Query age in years; clamped to the flow's ends.

    Returns
    -------
    float
        Flow value interpolated at the given age.
    """
    time_flow = np.arange(0, yearly_flow.size) * YEAR
    return np.interp(age * YEAR, time_flow, yearly_flow)


@overload
def get_increment_origin_index(
    years: FloatArray, current_year: float, age: float
) -> np.signedinteger: ...
@overload
def get_increment_origin_index(
    years: FloatArray, current_year: float, age: FloatArray
) -> IntArray: ...
def get_increment_origin_index(
    years: FloatArray, current_year: float, age: FloatLike
) -> np.signedinteger | IntArray:
    """
    Find the time-step index(es) at which increments entered the simulation.

    Each increment (vessel or plant) is treated as having entered 'age' years
    before current_year. An entity present at the initialization of the node
    gets index 0 — the best available approximation, as historical data is
    unavailable.

    Parameters
    ----------
    years
        Simulation timeline in years.
    current_year
        The current year (years[idx]).
    age
        Age(s) of the increment(s) in years.

    Returns
    -------
    np.signedinteger | IntArray
        Time-step index(es), mirroring the scalar- or arrayness of 'age'.
    """
    return find_nearest(years, current_year - age)


@overload
def find_nearest(array: npt.ArrayLike, values: float) -> np.signedinteger: ...
@overload
def find_nearest(array: npt.ArrayLike, values: FloatArray) -> IntArray: ...
def find_nearest(
    array: npt.ArrayLike, values: FloatLike
) -> np.signedinteger | IntArray:
    """
    Find the index of the entry in 'array' nearest to each of 'values'.

    Reference: https://stackoverflow.com/questions/2566412/find-nearest-value-in-numpy-array
    Answer by "anthonybell".

    Parameters
    ----------
    array
        Values to search, assumed sorted ascending.
    values
        Query value or values.

    Returns
    -------
    np.signedinteger | IntArray
        Indexes of the nearest entries, mirroring the arrayness of 'values'.
    """
    array = np.asarray(array)

    idxs = np.searchsorted(array, values, side="left")

    # where the previous entry is closer, or the query fell past the end,
    # step one index back; booleans subtract as 0/1 for scalars and arrays
    prev_idx_is_less = (idxs == len(array)) | (
        np.fabs(values - array[np.maximum(idxs - 1, 0)])
        < np.fabs(values - array[np.minimum(idxs, len(array) - 1)])
    )
    idxs -= prev_idx_is_less

    nearest: np.signedinteger | IntArray = idxs
    return nearest


def update_belief_path(
    raw_path: FloatArray, belief: FloatArray, alpha: float, idx: int
) -> None:
    """
    Calendar-date belief update for a single per-leg path.

    Match is by calendar index, not look-ahead position, so a given future
    year's belief evolves coherently as successive projections refine it. On
    the first call the prior belief is all-zero, so the belief bootstraps to
    the raw path; subsequent calls blend the new projection with the prior.

    Precondition: an all-zero forward slice of ``belief`` is indistinguishable
    from an uninitialized one and triggers the bootstrap (full adoption of the
    new path, no smoothing). Callers whose smoothed quantity can legitimately
    be all-zero over the remaining horizon must not use this helper as-is.

    Parameters
    ----------
    raw_path
        Raw forward path from the latest LP solve. Values at ``s < idx`` are
        ignored.
    belief
        Previous belief path. Same length as ``raw_path``. Modified in place.
    alpha
        Smoothing weight. ``alpha = 1`` trusts the new projection fully;
        ``alpha = 0`` ignores it entirely.
    idx
        Current outer time-step index. Only ``s >= idx`` are updated.
    """
    forward_slice = np.s_[idx:]
    belief_forward = belief[forward_slice]
    raw_forward = raw_path[forward_slice]

    if (belief_forward == 0.0).all():
        # bootstrap: no prior evidence, adopt the raw path directly.
        belief[forward_slice] = raw_forward
    else:
        # exponential smoothing: blend new projection with the prior belief.
        belief[forward_slice] = alpha * raw_forward + (1.0 - alpha) * belief_forward


def derive_smoothing_alpha(
    idx: int,
    decision_horizon_years: float,
    timeline: FloatArray,
) -> float:
    """
    Derive the EMA smoothing parameter from the decision horizon.

    Shorter horizons give a larger alpha (more responsive). A 5-year
    horizon with 1-year steps gives alpha ~ 0.17; a 3-year horizon
    with 1-year steps gives alpha ~ 0.25.

    Parameters
    ----------
    idx
        Current outer time-step index.
    decision_horizon_years
        Characteristic decision horizon (years).
    timeline
        Simulation timeline in days.

    Returns
    -------
    float
        Smoothing parameter.
    """
    horizon_idx = timeline.size - 1
    if idx > horizon_idx:
        return 1.0

    outer_step_years: float = (timeline[idx] - timeline[idx - 1]) / YEAR
    if outer_step_years <= 0.0:
        return 1.0

    return 1.0 / (1.0 + decision_horizon_years / outer_step_years)


def calculate_inertia(inertia: float, time_step: float) -> float:
    """
    Calculate the fraction of previous time-steps' value(s) that should be continued.

    Parameters
    ----------
    inertia
        Inertia, fraction/year.
    time_step
        Current time-step size, days.

    Returns
    -------
    float
        Fraction of previous time-steps value(s) that should be continued.
    """
    fraction: float = inertia ** (time_step / YEAR)
    return fraction


def calculate_compound_growth(
    initial: float, growth: FloatArray, timeline: FloatArray
) -> FloatArray:
    """
    Calculate the continuous compound growth of a property.

    The formula assumes that the growth is forward-looking, meaning that the growth at
    index t is applied over the time-step from t to t+1.

    Parameters
    ----------
    initial
        Initial value.
    growth
        Instantaneous growth rate with values corresponding to the timeline,
        fraction/year.
    timeline
        Timeline of the simulation.

    Returns
    -------
    FloatArray
        Resulting compounded growth.
    """
    continuous_growth = np.log(1.0 + growth)
    compound_growth = np.cumsum(continuous_growth[:-1] * np.diff(timeline) / YEAR)

    values = np.full_like(timeline, initial)
    values[1:] *= np.exp(compound_growth)

    return values
