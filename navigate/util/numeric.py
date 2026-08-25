# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.util.dates import YEAR

ROUND_OFF = 5   # decimals
TOLERANCE = 10 ** (-ROUND_OFF)


def divide_nonzero(a, b, default=0.):
    """
    Divide 'a' with 'b' where b>0, leaving defaults elsewhere.

    Parameters
    ----------
    a : np.ndarray | float
        Numerator.
    b : np.ndarray | float
        Denominator.
    default : float
        Default value in case b is zero.

    Returns
    -------
    float | np.ndarray
        Result after division.
    """

    a = np.asarray(a)
    b = np.asarray(b)

    if np.isscalar(b):
        if b > 0.0:
            return a / b
        # b <= 0: return default with shape of a
        if np.isscalar(a):
            return default
        out = np.empty_like(a, dtype=np.result_type(a, b))
        out.fill(default)
        return out

    # Allocate output with the BROADCASTED shape (not a.shape, not b.shape)
    dtype = np.result_type(a, b)
    shape = np.broadcast(a, b).shape

    if default == 0.:
        out = np.zeros(shape, dtype=dtype)
    else:
        out = np.empty(shape, dtype=dtype)
        out.fill(default)

    # where must also broadcast; b > 0 broadcasts fine
    np.divide(a, b, out=out, where=(b > 0.0))
    return out


def to_numpy(scalars, x=None, y=None, n=None):
    values = np.array([_to_value(s, x, y) for s in scalars])

    if n is not None:
        values = np.array([np.full(n, v) for v in values])

    return values


def _to_value(scalar, x=None, y=None):
    return scalar if isinstance(scalar, float) else scalar.get(x, y)


def is_strictly_increasing(x):
    """
    Testing by use of np.any as it is faster than np.all.

    Parameters
    ----------
    x : np.ndarray
        Vector.

    Returns
    -------
    bool
        Whether 'x' is strictly increasing.
    """

    return not np.any(np.diff(x) <= 0)


def is_non_strictly_increasing(x):
    """
    Testing by use of np.any as it is faster than np.all.

    Parameters
    ----------
    x : np.ndarray
        Vector.

    Returns
    -------
    bool
        Whether 'x' is non-strictly increasing.
    """

    return not np.any(np.diff(x) < 0)


def normalize_fractional(values, times):
    """
    Ensure values sum to unity and return a normalized container otherwise.

    Parameters
    ----------
    values : list | tuple | dict
        Container with floats and/or calculator nodes.
    times : float | np.ndarray
        Times to pass to potential calculator nodes.

    Returns
    -------
    np.ndarray | dict[float | np.ndarray]
        Normalized version of values.
    """

    n = len(values)

    if isinstance(values, list) or isinstance(values, tuple):

        _values = to_numpy(values, x=times)

        total = np.round(np.sum(_values, axis=0), ROUND_OFF)

        out = np.array([divide_nonzero(v, total, default=1. / n) for v in _values])

    elif isinstance(values, dict):

        _values = {key: _to_value(value, x=times) for key, value in values.items()}
        total = np.round(np.sum(list(_values.values()), axis=0), ROUND_OFF)

        out = {key: divide_nonzero(value, total, default=1. / n) for key, value in _values.items()}

    else:
        raise ValueError("'Values' must be either a list, tuple, or a dict.")

    return out


def get_increments_origin_index(years, current_year, ages):
    """
    Find the time-step indexes at which a increments (vessel or plant) entered the simulation at 'age' years ago.
    Notice here that if the entity was part of the initialization of the node index 0 is used.
    This is the best available approximation as historical data is unavailable.

    years : np.ndarray
        Simulation timeline in years.
    current_year : float
        The current year (years[idx]).
    age : float
        The age of the increment.

    Returns
    -------
    np.ndarray
        Time-step indexes at which increments were added to the simulation.
    """

    return find_nearest(years, (current_year - ages)[::-1])[::-1]


def get_increment_origin_index(years, current_year, age):
    """
    Find the time-step index at which an increment (vessel or plant) entered the simulation at 'age' years ago.
    Notice here that if the entity was part of the initialization of the node index 0 is used.
    This is the best available approximation as historical data is unavailable.

    Parameters
    ----------
    years : np.ndarray
        Simulation timeline in years.
    current_year : float
        The current year (years[idx]).
    age : float
        The age of the increment.

    Returns
    -------
    int
        Time-step index at which an increment was added to the simulation.
    """

    return find_nearest(years, current_year - age)


def find_nearest(array, values):
    """
    Reference: https://stackoverflow.com/questions/2566412/find-nearest-value-in-numpy-array
    Answer by "anthonybell".

    Parameters
    ----------
    array
    values

    Returns
    -------

    """

    # make sure array is a numpy array
    array = np.array(array)

    # get insert positions
    idxs = np.searchsorted(array, values, side="left")

    # find indexes where previous index is closer
    prev_idx_is_less = ((idxs == len(array))
                        | (np.fabs(values - array[np.maximum(idxs - 1, 0)])
                           < np.fabs(values - array[np.minimum(idxs, len(array) - 1)])))

    if isinstance(values, float):
        idxs -= 1 if prev_idx_is_less else 0
    else:
        idxs[prev_idx_is_less] -= 1

    return idxs


def update_belief_path(raw_path: np.ndarray,
                       belief: np.ndarray,
                       alpha: float | np.ndarray,
                       idx: int
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

    if (belief_forward == 0.).all():
        # bootstrap: no prior evidence, adopt the raw path directly.
        belief[forward_slice] = raw_forward
    else:
        # exponential smoothing: blend new projection with the prior belief.
        belief[forward_slice] = alpha * raw_forward + (1. - alpha) * belief_forward


def derive_smoothing_alpha(idx: int,
                           decision_horizon_years: float,
                           timeline: np.ndarray,
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
    Smoothing parameter.
    """

    horizon_idx = timeline.size - 1
    if idx > horizon_idx:
        return 1.

    outer_step_years = (timeline[idx] - timeline[idx - 1]) / YEAR
    if outer_step_years <= 0.:
        return 1.

    return 1. / (1. + decision_horizon_years / outer_step_years)


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
