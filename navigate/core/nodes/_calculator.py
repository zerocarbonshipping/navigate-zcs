# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core import assign_bound, assign_value
from navigate.util import ROUND_OFF

if TYPE_CHECKING:
    from navigate.core.nodes.input_kinds import NumberInput
    from navigate.util import FloatArray

logger = logging.getLogger(__name__)


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
        # extrapolation warning
        self._extrapolation_warned: bool = False

        # internal bounds are assigned when setting
        # attributes which have certain limits
        self._internal_lower_bound: float = -np.inf
        self._internal_upper_bound: float = np.inf

        # applied bounds used in truncating
        self._applied_lower_bound: float = -np.inf
        self._applied_upper_bound: float = np.inf

    # external methods (DSL attributes) ------------------------------------------------
    def set_addition(self, addition):
        """
        Set the addition of the calculator.

        Parameters
        ----------
        addition : float
            Addition to the calculated value.
        """
        self.addition = assign_value(addition)

    def set_multiplier(self, multiplier):
        """
        Set the multiplier of the calculator.

        Parameters
        ----------
        multiplier : float
            Multiplier of the calculated value.
        """
        self.multiplier = assign_value(multiplier)

    def set_lower_bound(self, lower_bound):
        """
        Set the publicly defined lower bound of the calculator.

        Parameters
        ----------
        lower_bound : float, str
            Lower bound of calculated value.
        """
        self.lower_bound = assign_bound(lower_bound)

        # called here in case the lower bound is changed during time-stepping
        self._assign_applied_bounds()

    def set_upper_bound(self, upper_bound):
        """
        Set the publicly defined upper bound of the calculator.

        Parameters
        ----------
        upper_bound : float, str
            Upper bound of calculated value.
        """
        self.upper_bound = assign_bound(upper_bound)

        # called here in case the upper bound is changed during time-stepping
        self._assign_applied_bounds()

    # internal methods -----------------------------------------------------------------
    @property
    def internal_bounds(self):
        """
        The tightest bounds any referencing attribute has imposed so far.

        Returns
        -------
        tuple[float, float]
            Lower and upper internal bound.
        """
        return self._internal_lower_bound, self._internal_upper_bound

    def set_internal_bounds(self, lower, upper):
        """
        Tighten the internal bounds of the calculator.

        Every attribute referencing the calculator offers its own bounds, so the
        tightest offer across all of them wins and a looser one is ignored.

        Parameters
        ----------
        lower : float
            Internally applied lower bound.
        upper : float
            Internally applied upper bound.
        """
        if lower > -np.inf:
            if self._internal_lower_bound == -np.inf:
                self._internal_lower_bound = lower

            elif lower > self._internal_lower_bound:
                logger.warning(
                    "%s: Internal lower bound tightened from %s to %s.",
                    self,
                    self._internal_lower_bound,
                    lower,
                )

                self._internal_lower_bound = lower

        if upper < np.inf:
            if self._internal_upper_bound == np.inf:
                self._internal_upper_bound = upper

            elif upper < self._internal_upper_bound:
                logger.warning(
                    "%s: Internal upper bound tightened from %s to %s.",
                    self,
                    self._internal_upper_bound,
                    upper,
                )

                self._internal_upper_bound = upper

        # called here in case internal bounds are set after the lower/upper bound
        self._assign_applied_bounds()

    def _truncate(self, value):
        """
        Truncate a calculated value.

        Parameters
        ----------
        value : float | np.ndarray
            Calculated value.

        Returns
        -------
        float | np.ndarray :
            Truncated value.
        """
        return np.maximum(
            np.minimum(value, self._applied_upper_bound), self._applied_lower_bound
        )

    def _assign_applied_bounds(self):
        """
        Assign concrete bounds based on an internal and external bounding logic.

        This method calculates the applied lower and upper bounds by comparing the
        user-defined bounds with internal ones. It ensures the applied bounds take
        the minimum or maximum values based on the respective constraints.
        """
        self._applied_lower_bound = np.maximum(
            self.lower_bound, self._internal_lower_bound
        )
        self._applied_upper_bound = np.minimum(
            self.upper_bound, self._internal_upper_bound
        )

    @staticmethod
    def _test_convexity(x: FloatArray, y: FloatArray) -> bool:
        """
        Test whether the piecewise linear function made up by (x, y) is convex.

        This test is only applicable to non-strictly increasing functions such as
        exponential functions.

        Parameters
        ----------
        x : np.ndarray
            x-values of a piecewise linear function.
        y : np.ndarray
            y-values of a piecewise linear function.

        Returns
        -------
        bool
            Whether the piecewise linear function is convex.
        """
        if x.size < 3:
            return True

        dy_dx = (y[1:] - y[:-1]) / (x[1:] - x[:-1])
        d2y_d2x = (dy_dx[1:] - dy_dx[:-1]) / (x[2:] - x[1:-1])
        return not np.any(np.round(d2y_d2x, ROUND_OFF) < 0.0)
