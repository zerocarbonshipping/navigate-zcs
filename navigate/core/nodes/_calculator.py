# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from dataclasses import replace
from typing import TYPE_CHECKING, overload

import numpy as np

from navigate.core import assign_bound, assign_value, deck_attribute
from navigate.core.bounds import Bounds
from navigate.core.expression import Expression
from navigate.util import ROUND_OFF

if TYPE_CHECKING:
    from navigate.core.types_ import NumberInput
    from navigate.util.types_ import FloatArray, FloatLike

logger = logging.getLogger(__name__)


@overload
def evaluate_number(number: NumberInput) -> float: ...


@overload
def evaluate_number(
    number: NumberInput, x: FloatLike | None, y: FloatLike | None = None
) -> FloatLike: ...


def evaluate_number(
    number: NumberInput, x: FloatLike | None = None, y: FloatLike | None = None
) -> FloatLike:
    """
    Evaluate a number a calculator attribute holds, expression or not.

    Parameters
    ----------
    number
        Number or deck expression the attribute holds.
    x
        First input variable an expression is evaluated with.
    y
        Second input variable an expression is evaluated with.

    Returns
    -------
    FloatLike
        The number, or the expression's value in the shape of the inputs.
    """
    if isinstance(number, Expression):
        return number.get(x, y)

    return number


class _Calculator:
    """
    Bounded, scaled value evaluation for the calculator nodes.

    Mixed into `Node` subclasses only, so the bound warnings can name the node.
    """

    def __init__(self) -> None:
        # external variables -----------------------------------------------------------
        self.addition: NumberInput = 0.0
        self.multiplier: NumberInput = 1.0
        self.lower_bound: float = -np.inf
        self.upper_bound: float = np.inf

        # internal variables -----------------------------------------------------------
        self._internal_bounds: Bounds = Bounds()
        self._applied_bounds: Bounds = Bounds()

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute()
    def set_addition(self, addition: NumberInput) -> None:
        """Set the addition of the calculator."""
        self.addition = assign_value(addition)

    @deck_attribute()
    def set_multiplier(self, multiplier: NumberInput) -> None:
        """Set the multiplier of the calculator."""
        self.multiplier = assign_value(multiplier)

    @deck_attribute()
    def set_lower_bound(self, lower_bound: float | str) -> None:
        """Set the user-defined lower bound of the calculator."""
        self.lower_bound = assign_bound(lower_bound, inclusive_upper=False)

        # called here in case the lower bound is changed during time-stepping
        self._update_applied_bounds()

    @deck_attribute()
    def set_upper_bound(self, upper_bound: float | str) -> None:
        """Set the user-defined upper bound of the calculator."""
        self.upper_bound = assign_bound(upper_bound, inclusive_lower=False)

        # called here in case the upper bound is changed during time-stepping
        self._update_applied_bounds()

    # internal methods -----------------------------------------------------------------
    def set_internal_bounds(
        self,
        lower: float,
        upper: float,
        *,
        inclusive_lower: bool = True,
        inclusive_upper: bool = True,
    ) -> None:
        """
        Tighten the internal bounds of the calculator.

        Every attribute referencing the calculator offers its own bounds, so the
        tightest offer across all of them wins and a looser one is ignored. An
        offer equal to the current bound makes it exclusive if either is.

        Parameters
        ----------
        lower
            Internally applied lower bound.
        upper
            Internally applied upper bound.
        inclusive_lower
            Whether the calculated value may equal the lower bound.
        inclusive_upper
            Whether the calculated value may equal the upper bound.
        """
        bounds = self._internal_bounds

        if lower > bounds.lower:
            if bounds.lower > -np.inf:
                logger.warning(
                    "%s: Internal lower bound tightened from %s to %s.",
                    self,
                    bounds.lower,
                    lower,
                )

            bounds = replace(bounds, lower=lower, inclusive_lower=inclusive_lower)
        elif lower == bounds.lower:
            inclusive = bounds.inclusive_lower and inclusive_lower
            bounds = replace(bounds, inclusive_lower=inclusive)

        if upper < bounds.upper:
            if bounds.upper < np.inf:
                logger.warning(
                    "%s: Internal upper bound tightened from %s to %s.",
                    self,
                    bounds.upper,
                    upper,
                )

            bounds = replace(bounds, upper=upper, inclusive_upper=inclusive_upper)
        elif upper == bounds.upper:
            inclusive = bounds.inclusive_upper and inclusive_upper
            bounds = replace(bounds, inclusive_upper=inclusive)

        self._internal_bounds = bounds

        # called here in case internal bounds are set after the lower/upper bound
        self._update_applied_bounds()

    @overload
    def _transform(
        self, value: float, x: FloatLike | None = None, y: FloatLike | None = None
    ) -> float: ...

    @overload
    def _transform(
        self, value: FloatArray, x: FloatLike | None = None, y: FloatLike | None = None
    ) -> FloatArray: ...

    def _transform(
        self, value: FloatLike, x: FloatLike | None = None, y: FloatLike | None = None
    ) -> FloatLike:
        """
        Apply the addition, the multiplier and the truncation to a calculated value.

        Parameters
        ----------
        value
            Calculated value.
        x
            First input the value was calculated at.
        y
            Second input the value was calculated at.

        Returns
        -------
        FloatLike
            Transformed value, in the shape of ``value``.
        """
        multiplier = evaluate_number(self.multiplier, x, y)
        addition = evaluate_number(self.addition, x, y)
        return self._truncate(multiplier * (value + addition))

    @overload
    def _truncate(self, value: float) -> float: ...

    @overload
    def _truncate(self, value: FloatArray) -> FloatArray: ...

    def _truncate(self, value: FloatLike) -> FloatLike:
        """
        Truncate a calculated value to the applied bounds.

        An inclusive bound clamps the value; one reaching an exclusive bound
        raises instead of being clamped onto a value the bound forbids.

        Parameters
        ----------
        value
            Calculated value.

        Returns
        -------
        FloatLike
            Truncated value, in the shape of ``value``.

        Raises
        ------
        ValueError
            If the value, or any entry of it, is at or beyond an exclusive bound.
        """
        bounds = self._applied_bounds

        # inclusive bounds only clamp, so the check is skipped where both are
        if bounds.exclusive:
            violation = bounds.exclusive_violation(value)
            if violation is not None:
                raise ValueError(f"{self}: {violation}")

        return np.maximum(np.minimum(value, bounds.upper), bounds.lower)

    def _update_applied_bounds(self) -> None:
        """
        Combine the user-defined bounds with the internal ones into the applied bounds.

        An exclusive internal bound stays exclusive only while it is the one applied:
        a user-defined bound strictly inside it clamps inclusively.
        """
        internal = self._internal_bounds
        user_lower_applies = self.lower_bound > internal.lower
        user_upper_applies = self.upper_bound < internal.upper
        self._applied_bounds = Bounds(
            lower=max(self.lower_bound, internal.lower),
            upper=min(self.upper_bound, internal.upper),
            inclusive_lower=internal.inclusive_lower or user_lower_applies,
            inclusive_upper=internal.inclusive_upper or user_upper_applies,
        )

    @staticmethod
    def _test_convexity(x: FloatArray, y: FloatArray) -> bool:
        """
        Test whether the piecewise linear function made up by (x, y) is convex.

        Parameters
        ----------
        x
            x-values of a piecewise linear function.
        y
            y-values of a piecewise linear function.

        Returns
        -------
        bool
            Whether the piecewise linear function is convex.
        """
        if x.size < 3:
            return True

        dy_dx = (y[1:] - y[:-1]) / (x[1:] - x[:-1])
        d2y_dx2 = (dy_dx[1:] - dy_dx[:-1]) / (x[2:] - x[1:-1])
        return not np.any(np.round(d2y_dx2, ROUND_OFF) < 0.0)
