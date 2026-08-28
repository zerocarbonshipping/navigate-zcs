# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import logging

import numpy as np
from scipy.interpolate import interpn

from navigate.core import assign_id, assign_value
from navigate.core.enum_ import ExtrapolateID, Interpolate2DID
from navigate.core.nodes._calculator import _Calculator
from navigate.logging_ import log_extrapolate_bounds
from navigate.util import find_nearest, is_strictly_increasing

logger = logging.getLogger(__name__)


class _Table2D(_Calculator):
    def __init__(self):
        _Calculator.__init__(self)

        # interpolation
        self._interpolate = Interpolate2DID.LINEAR

        # extrapolation
        self.extrapolate = ExtrapolateID.LINEAR
        self._outside = None

        self.x = None
        self.y = None
        self._z = None
        self._table = None
        self._is_convex = None

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_table'] = None  # local closure is not picklable
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        if self.x is not None and self.y is not None and self._z is not None:
            self._set_table(self.x, self.y, self._z)

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_interpolate(self, interpolate):
        self._interpolate = assign_id(interpolate, Interpolate2DID)

    def set_extrapolate(self, extrapolate):
        self.extrapolate = assign_id(extrapolate, ExtrapolateID)

    def set_outside(self, outside):
        self._outside = assign_value(outside)

    # internal methods -------------------------------------------------------------------------------------------------
    def get_table_limits(self):
        return np.min(self._z), np.max(self._z)

    def is_convex(self):
        return self._is_convex

    def calculate(self, x, y):
        return self._truncate(self.multiplier * (self._table(x, y) + self.addition))

    def reverse_lookup(self, z, y=None, interpolate=True):
        if y is None:
            y = self.y

        return self._reverse_lookup_x(y, z, interpolate)

    def _reverse_lookup_x(self, y, z, interpolate=True):
        """
        Perform a reverse lookup in the table defined by (xp, yp, zp), finding the x-value which is closest to 'z'.
        along a z-slice defined by y.

        This lookup is only applicable to strictly increasing functions such as exponential functions.

        Parameters
        ----------
        y : np.ndarray
            Values along which to calculate z-slices.
        z : np.ndarray
            z-values to reverse calculate x-values for.
        interpolate : bool
            Whether to interpolate or use the nearest value.

        Returns
        -------
        np.ndarray
            Interpolated or exact 'x' value corresponding to the given 'z' along a z-slice defined by 'y'.
        """

        x = []

        if interpolate:

            for yp in y:

                # extract a z-slice for the given y
                zp = self.calculate(self.x, yp)

                if not is_strictly_increasing(zp):
                    return None

                # then reverse calculate along
                # the x-axis using the z-slice
                x.append(np.interp(z, zp, self.x))

        else:

            for yp in y:

                # extract a z-slice for the given y
                zp = self.calculate(self.x, yp)

                idx = find_nearest(zp, z)
                x.append(self.x[idx])

        return np.array(x)

    def _check_extrapolation(self, x, y):
        x_range = self.x[-1] - self.x[0]
        y_range = self.y[-1] - self.y[0]
        x_atol = max(x_range * 1e-4, 1e-9)
        y_atol = max(y_range * 1e-4, 1e-9)

        x_oob = np.any(x < self.x[0] - x_atol) or np.any(x > self.x[-1] + x_atol)
        y_oob = np.any(y < self.y[0] - y_atol) or np.any(y > self.y[-1] + y_atol)

        if x_oob or y_oob:
            if not self._extrapolation_warned:
                if x_oob:
                    log_extrapolate_bounds(logger, self, x, *self._get_x_limits())
                if y_oob:
                    log_extrapolate_bounds(logger, self, y, *self._get_y_limits())
                self._extrapolation_warned = True
            else:
                logger.debug(f"{self}: Extrapolating beyond table limits (suppressed repeat).")

    def _get_x_limits(self):
        return self.x[0], self.x[-1]

    def _get_y_limits(self):
        return self.y[0], self.y[-1]

    def _get_interpolate_internal(self):
        if self._interpolate == Interpolate2DID.LINEAR:
            return 'linear'

        elif self._interpolate == Interpolate2DID.NEAREST:
            return 'nearest'

    def _get_allow_extrapolate_internal(self):
        return True if self.extrapolate == ExtrapolateID.FALSE else False

    def _get_extrapolate_internal(self):
        if self.extrapolate == ExtrapolateID.FLAT:
            return self._outside

        elif self.extrapolate == ExtrapolateID.LINEAR:
            return None

    def _set_table(self, x, y, z):
        self.x = x
        self.y = y
        self._z = z

        # if all linear paths in the x-direction
        # on the surface are convex, then it is
        # guaranteed to be convex in the x-direction
        self._is_convex = np.all([self._test_convexity(x, z[:, i]) for i, _ in enumerate(y)])

        method = self._get_interpolate_internal()
        bounds_error = self._get_allow_extrapolate_internal()
        fill_value = self._get_extrapolate_internal()

        def interp(x_, y_):
            x_ = np.asarray(x_)
            y_ = np.asarray(y_)

            scalar_inputs = (x_.ndim == 0) and (y_.ndim == 0)

            if scalar_inputs:
                # xi must be (npoints, ndim) for a single point -> (1, 2)
                xi = np.array([[x_.item(), y_.item()]], dtype=float)
                return interpn((x, y), z, xi,
                               method=method,
                               bounds_error=bounds_error,
                               fill_value=fill_value)[0]  # -> np.float64

            # For arrays (including scalar/array mix): broadcast + stack into (..., 2)
            xb, yb = np.broadcast_arrays(x_, y_)
            xi = np.stack([xb, yb], axis=-1)

            return interpn((x, y), z, xi,
                           method=method,
                           bounds_error=bounds_error,
                           fill_value=fill_value)

        self._table = interp


def check_table2D_input(x, y, z):
    """

    Parameters
    ----------
    x : np.ndarray
        'x' values in table.
    y : np.ndarray
        'y' values in table
    z : np.ndarray
        Array of array with z-values.
    """

    if (x.size * y.size) != z.size:
        raise ValueError("'z' ({}) must have a length equal to the product of 'x' ({}) and 'y' ({}) ."
                         .format(z.size, x.size, y.size))

    if not is_strictly_increasing(x):
        raise ValueError("'x' must be strictly increasing.")

    if not is_strictly_increasing(y):
        raise ValueError("'y' must be strictly increasing.")
