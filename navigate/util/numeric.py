# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Numeric helpers: safe division, normalization, index lookup, growth, smoothing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast, overload

import numpy as np
import numpy.typing as npt

from navigate.util.dates import YEAR

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.util.arrays import FloatArray, FloatLike, IntArray

ROUND_OFF = 5  # decimals
TOLERANCE = 10 ** (-ROUND_OFF)


class _SupportsGet(Protocol):
    """Calculator duck type: anything evaluated through a two-argument .get."""

    def get(self, x: FloatLike | None, y: FloatLike | None, /) -> FloatLike: ...


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

    if default == 0.0:
        quotients = np.zeros(shape, dtype=dtype)
    else:
        quotients = np.empty(shape, dtype=dtype)
        quotients.fill(default)

    # entries excluded by where= keep the prefilled default
    np.divide(numerator, denominator, out=quotients, where=(denominator > 0.0))
    return quotients


def to_numpy(
    scalars: Iterable[_FloatOrCalculator],
    x: FloatLike | None = None,
    y: FloatLike | None = None,
    length: int | None = None,
) -> FloatArray:
    """
    Evaluate a collection of floats and/or calculators into a numpy array.

    Parameters
    ----------
    scalars
        Floats and/or calculator nodes to evaluate.
    x
        First argument passed to the calculators' get.
    y
        Second argument passed to the calculators' get.
    length
        When given, each evaluated value is tiled to this length, producing a
        2-D array with one row per scalar.

    Returns
    -------
    FloatArray
        Evaluated values.
    """
    values = np.array([_to_value(scalar, x, y) for scalar in scalars])

    if length is not None:
        values = np.array([np.full(length, value) for value in values])

    return values


def _to_value(
    scalar: _FloatOrCalculator,
    x: FloatLike | None = None,
    y: FloatLike | None = None,
) -> FloatLike:
    return scalar if isinstance(scalar, float) else scalar.get(x, y)


def is_strictly_increasing(values: FloatArray) -> bool:
    """
    Test whether values are strictly increasing via np.any, which is faster than np.all.

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
    Test whether values are non-strictly increasing via np.any, faster than np.all.

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


def normalize_fractional[K](
    values: dict[K, _FloatOrCalculator], times: FloatLike | None
) -> dict[K, FloatArray]:
    """
    Normalize fractional values to sum to unity, splitting equally at zero total.

    Parameters
    ----------
    values
        Dict of floats and/or calculator nodes.
    times
        Times to pass to potential calculator nodes.

    Returns
    -------
    dict[K, FloatArray]
        Normalized version of values.
    """
    count = len(values)

    evaluated = {key: _to_value(value, x=times) for key, value in values.items()}
    total = np.round(np.sum(list(evaluated.values()), axis=0), ROUND_OFF)

    return {
        key: divide_nonzero(value, total, default=1.0 / count)
        for key, value in evaluated.items()
    }


def interpolate_tied_capital(tied_capital_flow: FloatArray, age: float) -> float:
    """
    Interpolate an increment's remaining tied-up capital at a given age.

    Uses its yearly tied-capital flow.

    Parameters
    ----------
    tied_capital_flow
        Remaining tied-up capital per year over the increment's life.
    age
        Age of the increment in years.

    Returns
    -------
    float
        Remaining tied-up capital at the given age.
    """
    time_flow = np.arange(0, tied_capital_flow.size) * YEAR
    return np.interp(age * YEAR, time_flow, tied_capital_flow)


def get_increments_origin_index(
    years: FloatArray, current_year: float, ages: FloatArray
) -> IntArray:
    """
    Find the time-step indexes at which increments entered the simulation.

    Each increment (vessel or plant) is treated as having entered 'ages' years before
    current_year. Notice here that if the entity was part of the initialization of the
    node index 0 is used. This is the best available approximation as historical data
    is unavailable.

    Parameters
    ----------
    years
        Simulation timeline in years.
    current_year
        The current year (years[idx]).
    ages
        The ages of the increments.

    Returns
    -------
    IntArray
        Time-step indexes at which increments were added to the simulation.
    """
    return find_nearest(years, (current_year - ages)[::-1])[::-1]


def get_increment_origin_index(
    years: FloatArray, current_year: float, age: float
) -> np.signedinteger:
    """
    Find the time-step index at which an increment entered the simulation.

    The increment (vessel or plant) is treated as having entered 'age' years before
    current_year. Notice here that if the entity was part of the initialization of the
    node index 0 is used. This is the best available approximation as historical data
    is unavailable.

    Parameters
    ----------
    years
        Simulation timeline in years.
    current_year
        The current year (years[idx]).
    age
        The age of the increment.

    Returns
    -------
    np.signedinteger
        Time-step index at which an increment was added to the simulation.
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
    array = np.array(array)

    idxs = np.searchsorted(array, values, side="left")

    # find indexes where the previous index is closer
    prev_idx_is_less = (idxs == len(array)) | (
        np.fabs(values - array[np.maximum(idxs - 1, 0)])
        < np.fabs(values - array[np.minimum(idxs, len(array) - 1)])
    )

    if isinstance(values, float):
        idxs -= 1 if prev_idx_is_less else 0
    else:
        # searchsorted mirrors the arrayness of 'values': array in, array out
        idxs = cast("IntArray", idxs)
        idxs[prev_idx_is_less] -= 1

    return idxs


def update_belief_path(
    raw_path: FloatArray, belief: FloatArray, alpha: FloatLike, idx: int
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
