# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np
from scipy.interpolate import interpn

from navigate.core import assign_id, assign_value
from navigate.core.enum_ import ExtrapolateID, Interpolate2DID
from navigate.core.nodes._calculator import _Calculator, evaluate_number
from navigate.util import is_strictly_increasing

if TYPE_CHECKING:
    from collections.abc import Callable

    from navigate.core.types_ import NumberInput
    from navigate.util import FloatArray, FloatLike


class _Table2D(_Calculator):
    def __init__(self) -> None:
        _Calculator.__init__(self)

        # external variables -----------------------------------------------------------
        # interpolation
        self._interpolate: Interpolate2DID = Interpolate2DID.LINEAR

        # extrapolation
        self.extrapolate: ExtrapolateID = ExtrapolateID.LINEAR
        self._outside: NumberInput | None = None

        # internal variables -----------------------------------------------------------
        self.x: FloatArray
        self.y: FloatArray
        self._z: FloatArray
        self._table: Callable[[FloatLike, FloatLike], FloatLike]
        self._is_convex: bool = False  # set with the table

    # external methods (DSL attributes) ------------------------------------------------
    def set_interpolate(self, interpolate: str) -> None:
        """
        Set the interpolation method used within the table.

        Examples
        --------
        - LINEAR
        - NEAREST

        Parameters
        ----------
        interpolate
            Interpolation method.
        """
        self._interpolate = assign_id(interpolate, Interpolate2DID)

    def set_extrapolate(self, extrapolate: str) -> None:
        """
        Set the extrapolation method used beyond the ends of the table.

        Examples
        --------
        - FALSE
        - FLAT
        - LINEAR

        Parameters
        ----------
        extrapolate
            Extrapolation method.
        """
        self.extrapolate = assign_id(extrapolate, ExtrapolateID)

    def set_outside(self, outside: NumberInput) -> None:
        """
        Set the flat extrapolation value used outside the table.

        Required when 'Extrapolate' is FLAT; the node's `check_consistency` rejects
        an unset value in that case. An expression is evaluated, without inputs,
        each time the table is looked up. INF and -INF are accepted here and
        checked by each attribute the calculator is assigned to.

        Parameters
        ----------
        outside
            Flat extrapolation value outside the table.
        """
        self._outside = assign_value(outside, allow_infinite=True)

    # internal methods -----------------------------------------------------------------
    def is_convex(self) -> bool:
        return self._is_convex

    @overload
    def calculate(self, x: float, y: float) -> float: ...

    @overload
    def calculate(self, x: FloatArray, y: FloatLike) -> FloatArray: ...

    @overload
    def calculate(self, x: FloatLike, y: FloatLike) -> FloatLike: ...

    def calculate(self, x: FloatLike, y: FloatLike) -> FloatLike:
        return self._transform(self._table(x, y), x, y)

    def reverse_lookup(
        self, z: FloatLike, y: FloatArray | None = None
    ) -> FloatArray | None:
        if y is None:
            y = self.y

        return self._reverse_lookup_x(y, z)

    def _reverse_lookup_x(self, y: FloatArray, z: FloatLike) -> FloatArray | None:
        """
        Perform a reverse lookup in the table defined by (xp, yp, zp).

        Finds the x-value closest to 'z' along a z-slice defined by y.

        This lookup is only applicable to strictly increasing functions such as
        exponential functions.

        Parameters
        ----------
        y
            Values along which to calculate z-slices.
        z
            z-values to reverse calculate x-values for.

        Returns
        -------
        np.ndarray | None
            Interpolated 'x' value corresponding to the given 'z' along a z-slice
            defined by 'y', or `None` when a z-slice is not strictly increasing.
        """
        x: list[FloatLike] = []

        for yp in y:
            # extract a z-slice for the given y
            zp = self.calculate(self.x, yp)

            if not is_strictly_increasing(zp):
                return None

            # then reverse calculate along
            # the x-axis using the z-slice
            x.append(np.interp(z, zp, self.x))

        return np.array(x)

    def _get_interpolate_internal(self) -> str:
        match self._interpolate:
            case Interpolate2DID.LINEAR:
                return "linear"

            case Interpolate2DID.NEAREST:
                return "nearest"

    def _get_bounds_error_internal(self) -> bool:
        return self.extrapolate == ExtrapolateID.FALSE

    def _get_extrapolate_internal(self) -> NumberInput | None:
        match self.extrapolate:
            case ExtrapolateID.FLAT:
                return self._outside

            case ExtrapolateID.LINEAR | ExtrapolateID.FALSE:
                # interpn extrapolates linearly without a fill value, and raises
                # before reading one when extrapolation is not allowed
                return None

    def _set_table(self, x: FloatArray, y: FloatArray, z: FloatArray) -> None:
        self.x = x
        self.y = y
        self._z = z

        # if all linear paths in the x-direction
        # on the surface are convex, then it is
        # guaranteed to be convex in the x-direction
        self._is_convex = all(self._test_convexity(x, z[:, i]) for i, _ in enumerate(y))

        method = self._get_interpolate_internal()
        bounds_error = self._get_bounds_error_internal()
        fill_number = self._get_extrapolate_internal()

        # copy.deepcopy leaves a function as it is, so a deep copy of a built table
        # shares this closure with its source: its x/y/z arrays and its fill value. The
        # DSL's Copy command can copy a node whose table is already built. This is
        # harmless only because nothing mutates the arrays in place, and the settings
        # captured here can only be assigned in DEFINE.
        def interp(x_: FloatLike, y_: FloatLike) -> FloatLike:
            x_array = np.asarray(x_)
            y_array = np.asarray(y_)

            # evaluated here rather than when the table is built: an expression
            # may read a node whose value changes during the run, such as a
            # Forecast, which holds the value of the current time step
            fill_value = None if fill_number is None else evaluate_number(fill_number)

            scalar_inputs = (x_array.ndim == 0) and (y_array.ndim == 0)

            if scalar_inputs:
                # xi must be (npoints, ndim) for a single point -> (1, 2)
                xi = np.array([[x_array.item(), y_array.item()]], dtype=float)
                value: float = interpn(
                    (x, y),
                    z,
                    xi,
                    method=method,
                    bounds_error=bounds_error,
                    fill_value=fill_value,
                )[0]  # -> np.float64
                return value

            # For arrays (including scalar/array mix): broadcast + stack into (..., 2)
            xb, yb = np.broadcast_arrays(x_array, y_array)
            xi = np.stack([xb, yb], axis=-1)

            values: FloatArray = interpn(
                (x, y),
                z,
                xi,
                method=method,
                bounds_error=bounds_error,
                fill_value=fill_value,
            )
            return values

        self._table = interp


def check_table2d_input(x: FloatArray, y: FloatArray, z: FloatArray) -> None:
    """
    Validate the x, y, and z arrays used to build a 2D table.

    'x' and 'y' must each hold at least two finite values, both strictly
    increasing, and 'z' must be a 2-D array of shape ('x'.size, 'y'.size). A 'z'
    may be INF, and is checked by each attribute the table is assigned to when
    it is evaluated, but never NaN, which no bound can reject.

    Parameters
    ----------
    x
        'x' values in table.
    y
        'y' values in table
    z
        Array of array with z-values.
    """
    if (x.size < 2) or (y.size < 2):
        raise ValueError(
            f"'x' ({x.size}) and 'y' ({y.size}) must each be at least of length 2."
        )

    if z.shape != (x.size, y.size):
        raise ValueError(
            f"'z' (shape {z.shape}) must have shape ({x.size}, {y.size}), matching"
            " the length of 'x' and 'y'."
        )

    if not np.all(np.isfinite(x)):
        raise ValueError("'x' must be finite.")

    if not np.all(np.isfinite(y)):
        raise ValueError("'y' must be finite.")

    if np.any(np.isnan(z)):
        raise ValueError("'z' must not be NaN.")

    if not is_strictly_increasing(x):
        raise ValueError("'x' must be strictly increasing.")

    if not is_strictly_increasing(y):
        raise ValueError("'y' must be strictly increasing.")
