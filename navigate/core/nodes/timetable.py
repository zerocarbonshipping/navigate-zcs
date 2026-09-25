# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Timetable node, a dated two-input table lookup."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from navigate.core.enum_ import ExtrapolateID
from navigate.core.node import Node
from navigate.core.node_type import TIMETABLE
from navigate.core.nodes._table2d import _Table2D, check_table2d_input
from navigate.core.table_data import TableData, build_table_2d_dated
from navigate.util import is_date_array, timedelta_to_days

if TYPE_CHECKING:
    import numpy as np

    from navigate.util import DateArray, FloatArray

logger = logging.getLogger(__name__)


class Timetable(Node, _Table2D):
    """
    A table of z against time and y, evaluated at the current time by default.

    Parameters
    ----------
    name
        Node name.
    """

    def __init__(self, name: str) -> None:
        Node.__init__(self, name, TIMETABLE)
        _Table2D.__init__(self)

        # temporarily stored variables at current time-step
        self._current_time: float | None = None

        # used for temporary storage of tables during deck parsing
        self._temporary_table: (
            tuple[FloatArray | DateArray, FloatArray, FloatArray] | None
        ) = None

    def set_table(self, table: TableData) -> None:
        """
        Set the table of x-, y- and z-values the timetable interpolates in.

        The x-values are dates, or days since the start of the simulation. The
        table is held until 'replace_reference_table' rebases a dated table to
        the start date and validates it: at that point both the x-values and the
        y-values must be strictly increasing, and the number of z-values must
        equal the number of x-values times the number of y-values.

        Parameters
        ----------
        table
            Parsed table: y-values in the header row, x-values down the first
            column of every row below it, z-values filling the rest.
        """
        x, y, z = build_table_2d_dated(table)
        self._temporary_table = (x, y, z)

    def replace_reference_table(self, reference: np.datetime64) -> None:
        if self._temporary_table is None:
            return

        x, y, z = self._temporary_table

        if is_date_array(x):
            x = timedelta_to_days(x - reference)

        check_table2d_input(x, y, z)

        self._set_table(x, y, z)
        self._temporary_table = None

    def check_consistency(self) -> None:
        if self.extrapolate == ExtrapolateID.FLAT:
            if self._outside is None:
                raise ValueError(
                    f"{self}: 'Outside' must be defined when 'Extrapolate' is set to"
                    " FLAT."
                )

        else:
            if self._outside is not None:
                logger.warning(
                    "%s: 'Outside' is defined, but ignored since 'Extrapolate' is set"
                    " to LINEAR.",
                    self,
                )

    def set_current_time(self, time: float) -> None:
        """
        Set the current time, read by 'get' when no explicit x-value is given.

        Parameters
        ----------
        time
            Time passed since start date (days).
        """
        self._current_time = time

    def get(self, x: float | None = None, y: float | None = None) -> float:
        """
        Return the timetable value at (x, y), with x defaulting to the current time.

        Parameters
        ----------
        x
            Time passed since start date (days); None reads the current time.
        y
            Second input variable. None, which an expression passes on when it
            is evaluated without input, is rejected.

        Returns
        -------
        float
            Response variable.

        Raises
        ------
        ValueError
            If ``y`` is None, or if ``x`` is None before the first time-step.
        """
        if x is None:
            x = self._current_time

        if y is None:
            raise ValueError(f"{self}: Evaluating a Timetable requires an input 'y'.")

        if x is None:
            raise ValueError(
                f"{self}: Evaluating a Timetable requires a time, unset before the"
                " first time-step."
            )

        return self.calculate(x, y)
