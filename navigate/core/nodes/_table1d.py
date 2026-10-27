# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the table base shared by the Curve and Forecast nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np
from scipy.interpolate import interp1d

from navigate.core import SECTION_DEFINE, assign_id, assign_value, deck_attribute
from navigate.core.enum_ import ExtrapolateID, Interpolate1DID
from navigate.core.nodes._calculator import _Calculator
from navigate.util import is_strictly_increasing

if TYPE_CHECKING:
    from navigate.core.types_ import NumberInput
    from navigate.util.types_ import FloatArray, FloatLike


class _Table1D(_Calculator):
    """The one-input table lookup common to the Curve and Forecast nodes."""

    def __init__(self) -> None:
        _Calculator.__init__(self)

        # external variables -----------------------------------------------------------
        # interpolation
        self.interpolate: Interpolate1DID = Interpolate1DID.LINEAR

        # extrapolation
        self.extrapolate: ExtrapolateID = ExtrapolateID.LINEAR
        self.below: NumberInput | None = None
        self.above: NumberInput | None = None

        # internal variables -----------------------------------------------------------
        self.x: FloatArray
        self.y: FloatArray
        self.is_convex: bool
        self._table: interp1d
        self._fill_values: tuple[NumberInput, NumberInput] | None

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(SECTION_DEFINE)
    def set_interpolate(self, interpolate: str) -> None:
        """Set the interpolation method used within the table."""
        self.interpolate = assign_id(interpolate, Interpolate1DID)

    @deck_attribute(SECTION_DEFINE)
    def set_extrapolate(self, extrapolate: str) -> None:
        """Set the extrapolation method used beyond the ends of the table."""
        self.extrapolate = assign_id(extrapolate, ExtrapolateID)

    @deck_attribute(SECTION_DEFINE)
    def set_below(self, below: NumberInput) -> None:
        """Set the flat extrapolation value below the table."""
        self.below = assign_value(below, allow_infinite=True)

    @deck_attribute(SECTION_DEFINE)
    def set_above(self, above: NumberInput) -> None:
        """Set the flat extrapolation value above the table."""
        self.above = assign_value(above, allow_infinite=True)

    # internal methods -----------------------------------------------------------------
    @overload
    def calculate(self, x: float) -> float: ...

    @overload
    def calculate(self, x: FloatArray) -> FloatArray: ...

    def calculate(self, x: FloatLike) -> FloatLike:
        # interp1d is untyped; it answers in the shape of its input
        table_value: FloatLike = self._table(x)

        if self._fill_values is not None:
            table_value = self._fill_flat(x, table_value, *self._fill_values)

        return self._transform(table_value, x)

    def reverse_lookup(self, y: FloatLike) -> FloatLike | None:
        """
        Perform a reverse lookup in the node's table for the x-value closest to 'y'.

        This lookup is only applicable to strictly increasing functions such as
        exponential functions.

        Parameters
        ----------
        y
            Value to find the corresponding x-value for.

        Returns
        -------
        FloatLike | None
            Interpolated 'x' value corresponding to the given 'y', or `None` when
            the table is not strictly increasing.
        """
        yp = self.calculate(self.x)

        if not is_strictly_increasing(yp):
            return None

        return np.interp(y, yp, self.x)

    def _check_interpolate_extrapolate_consistency(self) -> None:
        is_step = self.interpolate in (Interpolate1DID.PREVIOUS, Interpolate1DID.NEXT)

        if is_step and self.extrapolate == ExtrapolateID.LINEAR:
            raise ValueError(
                "'Extrapolate' must not be LINEAR when 'Interpolate' is"
                f" {self.interpolate.name}. This can lead to non-numeric"
                " extrapolations yielding erroneous results."
            )

    def _interp1d_kind(self) -> str:
        match self.interpolate:
            case Interpolate1DID.LINEAR:
                return "linear"

            case Interpolate1DID.PREVIOUS:
                return "previous"

            case Interpolate1DID.NEXT:
                return "next"

            case Interpolate1DID.NEAREST:
                return "nearest"

            case Interpolate1DID.NEAREST_UP:
                return "nearest-up"

    def _interp1d_fill_value(self) -> float | str | None:
        match self.extrapolate:
            case ExtrapolateID.FLAT:
                # a placeholder: 'calculate' fills in the flat values
                return np.nan

            case ExtrapolateID.LINEAR:
                return "extrapolate"

            case ExtrapolateID.FALSE:
                # out-of-range lookups raise, so no fill value is needed
                return None

    def _flat_fill_values(self) -> tuple[NumberInput, NumberInput] | None:
        if self.extrapolate != ExtrapolateID.FLAT:
            return None

        below = self.below if self.below is not None else float(self.y[0])
        above = self.above if self.above is not None else float(self.y[-1])

        return below, above

    def _fill_flat(
        self,
        x: FloatLike,
        table_value: FloatLike,
        below: NumberInput,
        above: NumberInput,
    ) -> FloatLike:
        """
        Replace the lookups outside the table with the flat extrapolation values.

        The values are evaluated here rather than handed to interp1d when the
        table is built: an expression may read a node whose value changes during
        the run, such as a Forecast, which holds the value of the current time
        step.

        Parameters
        ----------
        x
            Input the table was looked up at.
        table_value
            Table lookup at ``x``, undefined outside the table.
        below
            Flat extrapolation value below the table.
        above
            Flat extrapolation value above the table.

        Returns
        -------
        FloatLike
            Table lookup with the flat values filled in, in the shape of ``x``.
        """
        filled = np.where(x < self.x[0], self._evaluate_number(below), table_value)
        filled = np.where(x > self.x[-1], self._evaluate_number(above), filled)

        # np.where answers a scalar input with a 0-d array
        return filled if isinstance(x, np.ndarray) else float(filled)

    def _set_table(self, x: FloatArray, y: FloatArray) -> None:
        self._check_interpolate_extrapolate_consistency()

        self.x = x
        self.y = y

        self.is_convex = self._test_convexity(x, y)
        self._fill_values = self._flat_fill_values()

        self._table = interp1d(
            x,
            y,
            kind=self._interp1d_kind(),
            bounds_error=self.extrapolate == ExtrapolateID.FALSE,
            fill_value=self._interp1d_fill_value(),
        )

    @staticmethod
    def _check_table(x: FloatArray, y: FloatArray) -> None:
        """
        Validate the x and y arrays used to build a 1D table.

        Every 'x' must be finite, as interpolating across an infinite one gives NaN.
        A 'y' may be INF, and is checked by each attribute the table is assigned to
        when it is evaluated, but never NaN, which no bound can reject.

        Parameters
        ----------
        x
            'x' values in table.
        y
            'y' values in table.
        """
        if (x.size < 2) or (y.size < 2) or (x.size != y.size):
            raise ValueError(
                f"'x' ({x.size}) and 'y' ({y.size}) must be at least of length 2 and"
                " the same size."
            )

        if not np.all(np.isfinite(x)):
            raise ValueError("'x' must be finite.")

        if np.any(np.isnan(y)):
            raise ValueError("'y' must not be NaN.")

        if not is_strictly_increasing(x):
            raise ValueError("'x' must be strictly increasing.")
