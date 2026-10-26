# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the table base shared by the Surface and Timetable nodes."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, overload

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from navigate.core import SECTION_DEFINE, assign_id, assign_value, deck_attribute
from navigate.core.enum_ import ExtrapolateID, Interpolate2DID
from navigate.core.nodes._calculator import _Calculator
from navigate.util import is_strictly_increasing

if TYPE_CHECKING:
    from navigate.core.types_ import NumberInput
    from navigate.util.types_ import FloatArray, FloatLike

logger = logging.getLogger(__name__)


class _Table2D(_Calculator):
    """The two-input table lookup common to the Surface and Timetable nodes."""

    def __init__(self) -> None:
        _Calculator.__init__(self)

        # external variables -----------------------------------------------------------
        # interpolation
        self.interpolate: Interpolate2DID = Interpolate2DID.LINEAR

        # extrapolation
        self.extrapolate: ExtrapolateID = ExtrapolateID.LINEAR
        self.outside: NumberInput | None = None

        # internal variables -----------------------------------------------------------
        self.x: FloatArray
        self.y: FloatArray
        self.is_convex: bool
        self._table: RegularGridInterpolator
        self._fill_value: NumberInput | None

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(SECTION_DEFINE)
    def set_interpolate(self, interpolate: str) -> None:
        """Set the interpolation method used within the table."""
        self.interpolate = assign_id(interpolate, Interpolate2DID)

    @deck_attribute(SECTION_DEFINE)
    def set_extrapolate(self, extrapolate: str) -> None:
        """Set the extrapolation method used beyond the ends of the table."""
        self.extrapolate = assign_id(extrapolate, ExtrapolateID)

    @deck_attribute(SECTION_DEFINE)
    def set_outside(self, outside: NumberInput) -> None:
        """Set the flat extrapolation value used outside the table."""
        self.outside = assign_value(outside, allow_infinite=True)

    # internal methods -----------------------------------------------------------------
    @overload
    def calculate(self, x: float, y: float) -> float: ...

    @overload
    def calculate(self, x: FloatArray, y: FloatLike) -> FloatArray: ...

    @overload
    def calculate(self, x: FloatLike, y: FloatLike) -> FloatLike: ...

    def calculate(self, x: FloatLike, y: FloatLike) -> FloatLike:
        # RegularGridInterpolator is untyped; it answers in the broadcast shape of x
        # and y, as a 0-d array for two scalars, which '_transform' unwraps
        table_value: FloatLike = self._table((x, y))

        if self._fill_value is not None:
            table_value = self._fill_flat(x, y, table_value, self._fill_value)

        return self._transform(table_value, x, y)

    def reverse_lookup(
        self, z: FloatLike, y: FloatArray | None = None
    ) -> FloatArray | None:
        """
        Perform a reverse lookup in the node's table for the x-values closest to 'z'.

        Each x-value is looked up along the z-slice of the table at one 'y'. This
        lookup is only applicable to strictly increasing functions such as
        exponential functions.

        Parameters
        ----------
        z
            Value to find the corresponding x-values for.
        y
            Values to look up a z-slice at, the table's own y-values by default.

        Returns
        -------
        FloatArray | None
            Interpolated 'x' value for each 'y', or `None` when a z-slice is not
            strictly increasing.
        """
        if y is None:
            y = self.y

        x_values: list[FloatLike] = []

        for y_value in y:
            zp = self.calculate(self.x, y_value)

            if not is_strictly_increasing(zp):
                return None

            x_values.append(np.interp(z, zp, self.x))

        return np.array(x_values)

    def _check_extrapolate_consistency(self) -> None:
        if self.extrapolate == ExtrapolateID.FLAT and self.outside is None:
            raise ValueError(
                f"{self}: 'Outside' must be defined when 'Extrapolate' is set to FLAT."
            )

        if self.extrapolate != ExtrapolateID.FLAT and self.outside is not None:
            logger.warning(
                "%s: 'Outside' is defined, but ignored since 'Extrapolate' is set"
                " to %s.",
                self,
                self.extrapolate.name,
            )

    def _interpolator_method(self) -> str:
        match self.interpolate:
            case Interpolate2DID.LINEAR:
                return "linear"

            case Interpolate2DID.NEAREST:
                return "nearest"

    def _interpolator_fill_value(self) -> float | None:
        match self.extrapolate:
            case ExtrapolateID.FLAT:
                # a placeholder: 'calculate' fills in the flat value
                return np.nan

            case ExtrapolateID.LINEAR | ExtrapolateID.FALSE:
                # the interpolator extrapolates linearly without a fill value, and
                # raises before reading one when extrapolation is not allowed
                return None

    def _flat_fill_value(self) -> NumberInput | None:
        if self.extrapolate != ExtrapolateID.FLAT:
            return None

        return self.outside

    def _fill_flat(
        self,
        x: FloatLike,
        y: FloatLike,
        table_value: FloatLike,
        outside: NumberInput,
    ) -> FloatArray:
        """
        Replace the lookups outside the table with the flat extrapolation value.

        The value is evaluated here rather than handed to RegularGridInterpolator
        when the table is built: an expression may read a node whose value changes
        during the run, such as a Forecast, which holds the value of the current
        time step.

        Parameters
        ----------
        x
            First input the table was looked up at.
        y
            Second input the table was looked up at.
        table_value
            Table lookup at ``x`` and ``y``, undefined outside the table.
        outside
            Flat extrapolation value outside the table.

        Returns
        -------
        FloatArray
            Table lookup with the flat value filled in, in the broadcast shape of
            ``x`` and ``y``.
        """
        outside_x = (x < self.x[0]) | (x > self.x[-1])
        outside_y = (y < self.y[0]) | (y > self.y[-1])
        has_nan = np.isnan(x) | np.isnan(y)

        # a NaN input stays NaN, as the interpolator answers it, even where the
        # other input lies outside the table
        is_outside = (outside_x | outside_y) & ~has_nan
        return np.where(is_outside, self._evaluate_number(outside), table_value)

    def _set_table(self, x: FloatArray, y: FloatArray, z: FloatArray) -> None:
        self.x = x
        self.y = y

        # the surface is convex in x when every slice of it at a fixed y is
        self.is_convex = all(self._test_convexity(x, column) for column in z.T)
        self._fill_value = self._flat_fill_value()

        self._table = RegularGridInterpolator(
            (x, y),
            z,
            method=self._interpolator_method(),
            bounds_error=self.extrapolate == ExtrapolateID.FALSE,
            fill_value=self._interpolator_fill_value(),
        )

    @staticmethod
    def _check_table(x: FloatArray, y: FloatArray, z: FloatArray) -> None:
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
            'y' values in table.
        z
            z-values in table, one row per 'x' and one column per 'y'.
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
