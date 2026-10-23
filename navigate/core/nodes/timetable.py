# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Timetable node, a dated two-input table lookup."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, overload

from navigate.core import deck_attribute
from navigate.core.enum_ import ExtrapolateID
from navigate.core.node import Node
from navigate.core.node_type import TIMETABLE
from navigate.core.nodes._table2d import _Table2D, check_table2d_input
from navigate.core.table_data import TableData, build_table_2d_dated
from navigate.util import is_date_array, timedelta_to_days

if TYPE_CHECKING:
    import numpy as np

    from navigate.util import DateArray, FloatArray, FloatLike

logger = logging.getLogger(__name__)


class Timetable(Node, _Table2D):
    """
    A table of z against time and y, evaluated at the current time by default.

    Parameters
    ----------
    name
        Node name.
    """

    type = TIMETABLE

    def __init__(self, name: str) -> None:
        Node.__init__(self, name)
        _Table2D.__init__(self)

        # None until the first time-step sets the time
        self._current_time: float | None = None

        # the table read from the deck, pending until it is built
        self._pending_table: (
            tuple[FloatArray | DateArray, FloatArray, FloatArray] | None
        ) = None

    @deck_attribute(required=True)
    def set_table(self, table: TableData) -> None:
        """Set the table of x-, y- and z-values the timetable interpolates in."""
        self._pending_table = build_table_2d_dated(table)

    def build_table(self, start_date: np.datetime64) -> None:
        """Build the pending table, its dates counted in days from the start date."""
        if self._pending_table is None:
            return

        x, y, z = self._pending_table

        if is_date_array(x):
            x = timedelta_to_days(x - start_date)

        check_table2d_input(x, y, z)

        self._set_table(x, y, z)
        self._pending_table = None

    def check_consistency(self) -> None:
        if self.extrapolate == ExtrapolateID.FLAT and self._outside is None:
            raise ValueError(
                f"{self}: 'Outside' must be defined when 'Extrapolate' is set to FLAT."
            )

        if self.extrapolate != ExtrapolateID.FLAT and self._outside is not None:
            logger.warning(
                "%s: 'Outside' is defined, but ignored since 'Extrapolate' is set"
                " to %s.",
                self,
                self.extrapolate.name,
            )

    def set_current_time(self, time: float) -> None:
        """
        Set the current time, read by 'get' when no explicit x-value is given.

        Parameters
        ----------
        time
            Time passed since start date, in days.
        """
        self._current_time = time

    @overload
    def get(self, x: float | None = None, y: float | None = None) -> float: ...

    @overload
    def get(self, x: FloatArray, y: FloatLike | None = None) -> FloatArray: ...

    @overload
    def get(
        self, x: FloatLike | None = None, y: FloatLike | None = None
    ) -> FloatLike: ...

    def get(self, x: FloatLike | None = None, y: FloatLike | None = None) -> FloatLike:
        """
        Return the timetable value at (x, y), with x defaulting to the current time.

        Parameters
        ----------
        x
            Time passed since start date, in days; None reads the current time.
        y
            Second input variable. None, which an expression passes on when it
            is evaluated without input, is rejected.

        Returns
        -------
        float or FloatArray
            Response variable, in the shape of the inputs.

        Raises
        ------
        ValueError
            If ``y`` is None, or if ``x`` is None before the first time-step.
        """
        if y is None:
            raise ValueError(f"{self}: Evaluating a Timetable requires an input 'y'.")

        if x is None:
            x = self._current_time

        if x is None:
            raise ValueError(
                f"{self}: Evaluating a Timetable requires a time, unset before the"
                " first time-step."
            )

        return self.calculate(x, y)
