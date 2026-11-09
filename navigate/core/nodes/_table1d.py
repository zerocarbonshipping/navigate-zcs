# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the table base shared by the Curve and Forecast nodes."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, overload

import numpy as np
from scipy.interpolate import interp1d

from navigate.core import SECTION_DEFINE, assign_id, assign_value, deck_attribute
from navigate.core.enum_ import ExtrapolateID, Interpolate1DID
from navigate.core.nodes._calculator import _Calculator
from navigate.util import is_strictly_increasing, points_either_side

if TYPE_CHECKING:
    from navigate.core.types_ import NumberInput
    from navigate.util.types_ import FloatArray, FloatLike

logger = logging.getLogger(__name__)


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
        self._has_infinite: bool

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(SECTION_DEFINE)
    def set_interpolate(self, value: str) -> None:
        """Set the interpolation method used within the table."""
        self.interpolate = assign_id(value, Interpolate1DID)

    @deck_attribute(SECTION_DEFINE)
    def set_extrapolate(self, value: str) -> None:
        """Set the extrapolation method used beyond the ends of the table."""
        self.extrapolate = assign_id(value, ExtrapolateID)

    @deck_attribute(SECTION_DEFINE)
    def set_below(self, value: NumberInput) -> None:
        """Set the flat extrapolation value below the table."""
        self.below = assign_value(value, allow_infinite=True)

    @deck_attribute(SECTION_DEFINE)
    def set_above(self, value: NumberInput) -> None:
        """Set the flat extrapolation value above the table."""
        self.above = assign_value(value, allow_infinite=True)

    # internal methods -----------------------------------------------------------------
    @overload
    def calculate(self, x: float) -> float: ...

    @overload
    def calculate(self, x: FloatArray) -> FloatArray: ...

    def calculate(self, x: FloatLike) -> FloatLike:
        # interp1d is untyped; it answers in the shape of its input
        table_value: FloatLike = self._table(x)

        if self._has_infinite:
            table_value = self._fill_infinite(x, table_value)

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

    def _check_extrapolate_consistency(self) -> None:
        if self.extrapolate == ExtrapolateID.FLAT:
            return

        for name, value in (("Below", self.below), ("Above", self.above)):
            if value is not None:
                logger.warning(
                    "%s: '%s' is defined, but ignored since 'Extrapolate' is set"
                    " to %s.",
                    self,
                    name,
                    self.extrapolate.name,
                )

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

    def _fill_infinite(self, x: FloatLike, table_value: FloatLike) -> FloatLike:
        """
        Put the infinite table values back where a linear lookup weighs them.

        The interpolator holds a finite stand-in for each infinite value, as it
        would weigh an infinite value by zero at its finite neighbour and give
        0 * INF = NaN there. A lookup that gives an infinite point a nonzero weight
        takes its value: between the point and its neighbours, the neighbours
        excluded, and beyond the table where the end point is infinite.

        Parameters
        ----------
        x
            Input the table was looked up at.
        table_value
            Lookup of the finite stand-ins at ``x``.

        Returns
        -------
        FloatLike
            Table lookup with the infinite values put back, in the shape of ``x``.
        """
        below, above = points_either_side(self.x, x)

        # a lookup on a point is its value; the interpolator's slope arithmetic
        # from a stand-in could miss a finite neighbour by a rounding error
        filled = np.where(self.x[below] == x, self.y[below], table_value)
        filled = np.where(np.isinf(self.y[below]), self.y[below], filled)
        filled = np.where(np.isinf(self.y[above]), self.y[above], filled)

        # a NaN input stays NaN, as the interpolator answers it
        filled = np.where(np.isnan(x), table_value, filled)

        # np.where answers a scalar input with a 0-d array
        return filled if isinstance(x, np.ndarray) else float(filled)

    def _check_infinite_neighbours(self, y: FloatArray) -> None:
        """
        Reject a linear table whose infinite values leave a lookup undefined.

        Between INF and -INF, a linear lookup weighs both, and linear extrapolation
        off a finite end continues the slope to its neighbour, infinite when the
        neighbour is.

        Parameters
        ----------
        y
            'y' values in table.
        """
        if np.any(np.isinf(y[:-1]) & np.isinf(y[1:]) & (y[:-1] != y[1:])):
            raise ValueError(
                "'Table' must not hold INF next to -INF when 'Interpolate' is LINEAR,"
                " as the value between them is undefined."
            )

        if self.extrapolate != ExtrapolateID.LINEAR:
            return

        for end, neighbour in ((y[0], y[1]), (y[-1], y[-2])):
            if np.isfinite(end) and np.isinf(neighbour):
                raise ValueError(
                    "'Extrapolate' must not be LINEAR when an end of the table is"
                    " finite and its neighbour infinite, as the extrapolated slope is"
                    " infinite. Use FLAT or FALSE."
                )

    def _warn_infinite_neighbours(self, y: FloatArray) -> None:
        # a finite point next to an infinite one holds only at its own x, which a
        # table meant as a ramp to no limit, or as a step at the infinite point,
        # does not expect
        is_finite = np.isfinite(y)
        if np.any(is_finite[:-1] != is_finite[1:]):
            logger.warning(
                "%s: with 'Interpolate' LINEAR, the table is infinite all the way"
                " from an infinite point to its finite neighbours, which keep their"
                " values only at their own points. Use PREVIOUS or NEXT to set where"
                " the value turns infinite.",
                self,
            )

    def _set_table(self, x: FloatArray, y: FloatArray) -> None:
        self._check_interpolate_extrapolate_consistency()

        # a step interpolation takes a point's value, an infinite one included
        is_linear = self.interpolate == Interpolate1DID.LINEAR
        if is_linear:
            self._check_infinite_neighbours(y)
            self._warn_infinite_neighbours(y)

        self.x = x
        self.y = y

        self.is_convex = self._test_convexity(x, y)
        self._fill_values = self._flat_fill_values()

        self._has_infinite = is_linear and bool(np.any(np.isinf(y)))
        table_y = np.where(np.isinf(y), 0.0, y) if self._has_infinite else y

        self._table = interp1d(
            x,
            table_y,
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
        when it is evaluated, but never NaN, which no bound can reject. Where a
        linear table may hold INF is checked when the table is built.

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
