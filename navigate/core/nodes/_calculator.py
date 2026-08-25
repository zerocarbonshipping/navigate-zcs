# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import logging

import numpy as np

from navigate.core import assign_id, assign_value
from navigate.util import ROUND_OFF

logger = logging.getLogger(__name__)

BOUNDS_MAP = {'-INF': -np.inf,
              'INF': np.inf}


class _Calculator:
    def __init__(self):

        self._addition = 0.
        self._multiplier = 1.
        self._lower_bound = -np.inf
        self._upper_bound = np.inf

        # extrapolation warning
        self._extrapolation_warned = False

        # internal bounds are assigned when setting
        # attributes which have certain limits
        self._internal_lower_bound = -np.inf
        self._internal_upper_bound = np.inf

        # applied bounds used in truncating
        self._applied_lower_bound = -np.inf
        self._applied_upper_bound = np.inf

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_addition(self, addition):
        """
        Set the addition of the calculator.

        Parameters
        ----------
        addition : float
            Addition to the calculated value.
        """

        self._addition = assign_value(addition)

    def set_multiplier(self, multiplier):
        """
        Set the multiplier of the calculator.

        Parameters
        ----------
        multiplier : float
            Multiplier of the calculated value.
        """

        self._multiplier = assign_value(multiplier)

    def set_lower_bound(self, lower_bound):
        """
        Set the publicly defined lower bound of the calculator.

        Parameters
        ----------
        lower_bound : float, str
            Lower bound of calculated value.
        """

        if isinstance(lower_bound, float):
            self._lower_bound = assign_value(lower_bound)

        else:
            self._lower_bound = assign_id(lower_bound, BOUNDS_MAP)

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

        if isinstance(upper_bound, float):
            self._upper_bound = assign_value(upper_bound)

        else:
            self._upper_bound = assign_id(upper_bound, BOUNDS_MAP)

        # called here in case the upper bound is changed during time-stepping
        self._assign_applied_bounds()

    # internal methods -------------------------------------------------------------------------------------------------
    def transfer_internal_bounds(self, reference):
        """
        Update internal bounds if appropriate.

        Parameters
        ----------
        reference : NodeReference
            Class NodeReference to a calculator.
        """

        lower, upper = reference.internal_bounds
        # reference.get_inclus...
        # if npt inclusive,
        # Then the actual node has to be tighter
        # then the node itsself needs to have an applied lower/upper bound that is
        # make exception.

        if lower > -np.inf:

            if self._internal_lower_bound == -np.inf:
                self._internal_lower_bound = lower

            elif lower > self._internal_lower_bound:
                logger.warning("{}: Internal lower bound tightened from {} to {}."
                               .format(reference, self._internal_lower_bound, lower))

                self._internal_lower_bound = lower

        if upper < np.inf:

            if self._internal_upper_bound == np.inf:
                self._internal_upper_bound = upper

            elif upper < self._internal_upper_bound:
                logger.warning("{}: Internal upper bound tightened from {} to {}."
                               .format(reference, self._internal_upper_bound, upper))

                self._internal_upper_bound = upper

        # called here in case internal bounds are set after the lower/upper bound
        self._assign_applied_bounds()

    def set_internal_lower_bound(self, internal_lower_bound):
        """
        Set the internal lower bound of the calculator. This is not accessible through the deck, but is set by the
        setter of Nodes and GeneralNodes which have a lower bound.

        Parameters
        ----------
        internal_lower_bound : float
            Internally applied lower bound.
        """

        self._internal_lower_bound = internal_lower_bound

    def set_internal_upper_bound(self, internal_upper_bound):
        """
        Set the internal upper bound of the calculator. This is not accessible through the deck, but is set by the
        setter of Nodes and GeneralNodes which have an upper bound.

        Parameters
        ----------
        internal_upper_bound : float
            Internally applied lower bound.
        """

        self._internal_upper_bound = internal_upper_bound

    def get_bounds(self):
        return self._lower_bound, self._upper_bound

    def get_addition(self):
        return self._addition

    def get_multiplier(self):
        return self._multiplier

    def get_internal_lower_bound(self):
        return self._internal_lower_bound

    def get_internal_upper_bound(self):
        return self._internal_upper_bound

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

        return np.maximum(np.minimum(value, self._applied_upper_bound), self._applied_lower_bound)

    def _assign_applied_bounds(self):
        """
        Assign concrete bounds based on an internal and external bounding logic.

        This method calculates the applied lower and upper bounds by comparing the
        user-defined bounds with internal ones. It ensures the applied bounds take
        the minimum or maximum values based on the respective constraints.
        """

        self._applied_lower_bound = np.maximum(self._lower_bound, self._internal_lower_bound)
        self._applied_upper_bound = np.minimum(self._upper_bound, self._internal_upper_bound)

    @staticmethod
    def _test_convexity(x, y):
        """
        Test whether the piecewise linear function made up by the set (x, y) is a convex function.

        This test is only applicable to non-strictly increasing functions such as exponential functions.

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
        return not np.any(np.round(d2y_d2x, ROUND_OFF) < 0.)
