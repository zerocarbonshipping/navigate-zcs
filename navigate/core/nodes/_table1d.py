# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import logging

import numpy as np
from scipy.interpolate import interp1d

from navigate.core import assign_id, assign_value
from navigate.core.enum_ import ExtrapolateID, Interpolate1DID
from navigate.core.nodes._calculator import _Calculator
from navigate.logging_ import log_extrapolate_bounds
from navigate.util import find_nearest, is_strictly_increasing

logger = logging.getLogger(__name__)


class _Table1D(_Calculator):
    def __init__(self):
        _Calculator.__init__(self)

        # interpolation
        self._interpolate = Interpolate1DID.LINEAR

        # extrapolation
        self.extrapolate = ExtrapolateID.LINEAR
        self._below = None
        self._above = None

        self.x = None
        self.y = None
        self._table = None
        self._is_convex = None

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_table'] = None  # interp1d is not picklable
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        if self.x is not None and self.y is not None:
            self._set_table(self.x, self.y)

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_interpolate(self, interpolate):
        self._interpolate = assign_id(interpolate, Interpolate1DID)

    def set_extrapolate(self, extrapolate):
        self.extrapolate = assign_id(extrapolate, ExtrapolateID)

    def set_below(self, below):
        self._below = assign_value(below)

    def set_above(self, above):
        self._above = assign_value(above)

    # internal methods -------------------------------------------------------------------------------------------------
    def get_table_limits(self):
        return np.min(self.y), np.max(self.y)

    def is_convex(self):
        return self._is_convex

    def calculate(self, x):
        return self._truncate(self.multiplier * (self._table(x) + self.addition))

    def reverse_lookup(self, y, interpolate=True):
        """
        Perform a reverse lookup in the table defined by (xp, yp), finding the x-value which is closest to 'y'.

        This lookup is only applicable to strictly increasing functions such as exponential functions.

        Parameters
        ----------
        y : float | np.ndarray

        xp : np.ndarray
            x-values of a piecewise linear function.
        yp : np.ndarray
            y-values of a piecewise linear function.
        interpolate : bool
            Whether to interpolate or use the nearest value.

        Returns
        -------
        bool
            Interpolated or exact 'x' value corresponding to the given 'y'.
        """

        yp = self.calculate(self.x)

        if not is_strictly_increasing(yp):
            return None

        if interpolate:
            x = np.interp(y, yp, self.x)
        else:
            idx = find_nearest(yp, y)
            x = self.x[idx]

        return x

    def _check_extrapolation(self, x):
        x_range = self.x[-1] - self.x[0]
        atol = max(x_range * 1e-4, 1e-9)

        if np.any(x < self.x[0] - atol) or np.any(x > self.x[-1] + atol):
            if not self._extrapolation_warned:
                log_extrapolate_bounds(logger, self, x, *self._get_x_limits())
                self._extrapolation_warned = True
            else:
                logger.debug(f"{self}: Extrapolating beyond table limits (suppressed repeat).")

    def _get_x_limits(self):
        return self.x[0], self.x[-1]

    def _check_interpolate_extrapolate_consistency(self):

        if (self._interpolate in (Interpolate1DID.PREVIOUS, Interpolate1DID.NEXT))\
           and (self.extrapolate == ExtrapolateID.LINEAR):

            raise ValueError("'Extrapolate' must not be LINEAR when 'Interpolate' is {}. This can lead to"
                             " non-numeric extrapolations yielding erroneous results."
                             .format(self._interpolate.name))

    def _get_interpolate_internal(self):
        if self._interpolate == Interpolate1DID.LINEAR:
            return 'linear'

        elif self._interpolate == Interpolate1DID.PREVIOUS:
            return 'previous'

        elif self._interpolate == Interpolate1DID.NEXT:
            return 'next'

        elif self._interpolate == Interpolate1DID.NEAREST:
            return 'nearest'

        elif self._interpolate == Interpolate1DID.NEAREST_UP:
            return 'nearest-up'

    def _get_allow_extrapolate_internal(self):
        return True if self.extrapolate == ExtrapolateID.FALSE else False

    def _get_extrapolate_internal(self):
        if self.extrapolate == ExtrapolateID.FLAT:

            below = self._below if self._below is not None else self.y[0]
            above = self._above if self._above is not None else self.y[-1]

            return below, above

        elif self.extrapolate == ExtrapolateID.LINEAR:
            return 'extrapolate'

    def _set_table(self, x, y):

        self._check_interpolate_extrapolate_consistency()

        self.x = x
        self.y = y

        self._is_convex = self._test_convexity(x, y)

        self._table = interp1d(x, y,
                               kind=self._get_interpolate_internal(),
                               bounds_error=self._get_allow_extrapolate_internal(),
                               fill_value=self._get_extrapolate_internal())


def check_table1D_input(x, y):
    """

    Parameters
    ----------
    x : np.ndarray
        'x' values in table.
    y : np.ndarray
        'y' values in table
    """

    if (x.size < 2) or (y.size < 2) or (x.size != y.size):
        raise ValueError("'x' ({}) and 'y' ({}) must be at least of length 2 and the same size.".format(x.size, y.size))

    if not is_strictly_increasing(x):
        raise ValueError("'x' must be strictly increasing.")
