# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, overload

import numpy as np
from scipy.interpolate import interpn

from navigate.core import assign_id, assign_value
from navigate.core.enum_ import ExtrapolateID, Interpolate2DID
from navigate.core.nodes._calculator import _Calculator, evaluate_number
from navigate.logging_ import log_extrapolate_bounds
from navigate.util import is_strictly_increasing

if TYPE_CHECKING:
    from collections.abc import Callable

    from navigate.core.nodes.input_kinds import NumberInput
    from navigate.util import FloatArray, FloatLike

logger = logging.getLogger(__name__)


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

    def __getstate__(self) -> dict[str, object]:
        state = self.__dict__.copy()
        state.pop("_table", None)  # local closure is not picklable
        return state

    def __setstate__(self, state: dict[str, object]) -> None:
        self.__dict__.update(state)
        # the arrays are set together, and only once the table is
        if "x" in state:
            self._set_table(self.x, self.y, self._z)

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
        each time the table is looked up.

        Parameters
        ----------
        outside
            Flat extrapolation value outside the table.
        """
        self._outside = assign_value(outside)

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

    def _check_extrapolation(self, x: FloatArray, y: FloatArray) -> None:
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
                logger.debug(
                    "%s: Extrapolating beyond table limits (suppressed repeat).", self
                )

    def _get_x_limits(self) -> tuple[float, float]:
        return self.x[0], self.x[-1]

    def _get_y_limits(self) -> tuple[float, float]:
        return self.y[0], self.y[-1]

    def _get_interpolate_internal(self) -> str:
        match self._interpolate:
            case Interpolate2DID.LINEAR:
                return "linear"

            case Interpolate2DID.NEAREST:
                return "nearest"

    def _get_allow_extrapolate_internal(self) -> bool:
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
        bounds_error = self._get_allow_extrapolate_internal()
        fill_number = self._get_extrapolate_internal()

        def interp(x_: FloatLike, y_: FloatLike) -> FloatLike:
            x_array = np.asarray(x_)
            y_array = np.asarray(y_)

            # evaluated here rather than when the table is built: a Surface
            # builds its table as the deck is read, before the deck's
            # expressions are resolved
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

    Parameters
    ----------
    x
        'x' values in table.
    y
        'y' values in table
    z
        Array of array with z-values.
    """
    if (x.size * y.size) != z.size:
        raise ValueError(
            f"'z' ({z.size}) must have a length equal to the product of 'x' ({x.size})"
            f" and 'y' ({y.size}) ."
        )

    if not is_strictly_increasing(x):
        raise ValueError("'x' must be strictly increasing.")

    if not is_strictly_increasing(y):
        raise ValueError("'y' must be strictly increasing.")
