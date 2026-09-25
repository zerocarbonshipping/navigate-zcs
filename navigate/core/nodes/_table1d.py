# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, overload

import numpy as np
from scipy.interpolate import interp1d

from navigate.core import assign_id, assign_value
from navigate.core.enum_ import ExtrapolateID, Interpolate1DID
from navigate.core.nodes._calculator import _Calculator, evaluate_number
from navigate.logging_ import log_extrapolate_bounds
from navigate.util import is_strictly_increasing

if TYPE_CHECKING:
    from navigate.core.nodes.input_kinds import NumberInput
    from navigate.util import FloatArray, FloatLike

logger = logging.getLogger(__name__)


class _Table1D(_Calculator):
    def __init__(self) -> None:
        _Calculator.__init__(self)

        # external variables -----------------------------------------------------------
        # interpolation
        self._interpolate: Interpolate1DID = Interpolate1DID.LINEAR

        # extrapolation
        self.extrapolate: ExtrapolateID = ExtrapolateID.LINEAR
        self._below: NumberInput | None = None
        self._above: NumberInput | None = None

        # internal variables -----------------------------------------------------------
        self.x: FloatArray
        self.y: FloatArray
        self._table: interp1d
        self._fill_values: tuple[NumberInput, NumberInput] | None = None
        self._is_convex: bool = False  # set with the table

    def __getstate__(self) -> dict[str, object]:
        state = self.__dict__.copy()
        state.pop("_table", None)  # interp1d is not picklable
        return state

    def __setstate__(self, state: dict[str, object]) -> None:
        self.__dict__.update(state)
        # the arrays are set together, and only once the table is
        if "x" in state:
            self._set_table(self.x, self.y)

    # external methods (DSL attributes) ------------------------------------------------
    def set_interpolate(self, interpolate: str) -> None:
        """
        Set the interpolation method used within the table.

        Examples
        --------
        - LINEAR
        - PREVIOUS
        - NEXT
        - NEAREST
        - NEAREST_UP

        Parameters
        ----------
        interpolate
            Interpolation method.
        """
        self._interpolate = assign_id(interpolate, Interpolate1DID)

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

    def set_below(self, below: NumberInput) -> None:
        """
        Set the flat extrapolation value below the table.

        Only read when 'Extrapolate' is FLAT; the first y-value in the table is
        used when this is left unset. An expression is evaluated, without inputs,
        each time the table is looked up below its first x-value.

        Parameters
        ----------
        below
            Flat extrapolation value below the table.
        """
        self._below = assign_value(below)

    def set_above(self, above: NumberInput) -> None:
        """
        Set the flat extrapolation value above the table.

        Only read when 'Extrapolate' is FLAT; the last y-value in the table is
        used when this is left unset. An expression is evaluated, without inputs,
        each time the table is looked up above its last x-value.

        Parameters
        ----------
        above
            Flat extrapolation value above the table.
        """
        self._above = assign_value(above)

    # internal methods -----------------------------------------------------------------
    def is_convex(self) -> bool:
        return self._is_convex

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

    def _check_extrapolation(self, x: FloatArray) -> None:
        x_range = self.x[-1] - self.x[0]
        atol = max(x_range * 1e-4, 1e-9)

        if np.any(x < self.x[0] - atol) or np.any(x > self.x[-1] + atol):
            if not self._extrapolation_warned:
                log_extrapolate_bounds(logger, self, x, *self._get_x_limits())
                self._extrapolation_warned = True
            else:
                logger.debug(
                    "%s: Extrapolating beyond table limits (suppressed repeat).", self
                )

    def _get_x_limits(self) -> tuple[float, float]:
        return self.x[0], self.x[-1]

    def _check_interpolate_extrapolate_consistency(self) -> None:
        if (self._interpolate in (Interpolate1DID.PREVIOUS, Interpolate1DID.NEXT)) and (
            self.extrapolate == ExtrapolateID.LINEAR
        ):
            raise ValueError(
                "'Extrapolate' must not be LINEAR when 'Interpolate' is"
                f" {self._interpolate.name}. This can lead to non-numeric"
                " extrapolations yielding erroneous results."
            )

    def _get_interpolate_internal(self) -> str:
        match self._interpolate:
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

    def _get_allow_extrapolate_internal(self) -> bool:
        return self.extrapolate == ExtrapolateID.FALSE

    def _get_extrapolate_internal(self) -> float | str | None:
        match self.extrapolate:
            case ExtrapolateID.FLAT:
                # a placeholder: 'calculate' fills in the flat values
                return np.nan

            case ExtrapolateID.LINEAR:
                return "extrapolate"

            case ExtrapolateID.FALSE:
                # out-of-range lookups raise, so no fill value is needed
                return None

    def _get_fill_values_internal(self) -> tuple[NumberInput, NumberInput] | None:
        if self.extrapolate != ExtrapolateID.FLAT:
            return None

        below = self._below if self._below is not None else float(self.y[0])
        above = self._above if self._above is not None else float(self.y[-1])

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
        filled = np.where(
            x < self.x[0],
            evaluate_number(below),
            np.where(x > self.x[-1], evaluate_number(above), table_value),
        )

        # np.where answers a scalar input with a 0-d array
        return filled if isinstance(x, np.ndarray) else float(filled)

    def _set_table(self, x: FloatArray, y: FloatArray) -> None:
        self._check_interpolate_extrapolate_consistency()

        self.x = x
        self.y = y

        self._is_convex = self._test_convexity(x, y)
        self._fill_values = self._get_fill_values_internal()

        self._table = interp1d(
            x,
            y,
            kind=self._get_interpolate_internal(),
            bounds_error=self._get_allow_extrapolate_internal(),
            fill_value=self._get_extrapolate_internal(),
        )


def check_table1d_input(x: FloatArray, y: FloatArray) -> None:
    """
    Validate the x and y arrays used to build a 1D table.

    Parameters
    ----------
    x
        'x' values in table.
    y
        'y' values in table
    """
    if (x.size < 2) or (y.size < 2) or (x.size != y.size):
        raise ValueError(
            f"'x' ({x.size}) and 'y' ({y.size}) must be at least of length 2 and the"
            " same size."
        )

    if not is_strictly_increasing(x):
        raise ValueError("'x' must be strictly increasing.")
