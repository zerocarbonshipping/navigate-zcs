# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Forecast node, a dated table lookup evaluated at the current time."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np

from navigate.core.node import Node
from navigate.core.node_type import FORECAST
from navigate.core.nodes._table1d import _Table1D, check_table1d_input
from navigate.core.table_data import TableData, build_table_1d_dated
from navigate.util import is_date_array, timedelta_to_days

if TYPE_CHECKING:
    from navigate.util import DateArray, FloatArray, FloatLike


class Forecast(Node, _Table1D):
    """
    A table of y against time, precalculated once per time-step.

    Parameters
    ----------
    name
        Node name.
    """

    def __init__(self, name: str) -> None:
        Node.__init__(self, name, FORECAST)
        _Table1D.__init__(self)

        # temporarily stored variables at current time-step; nan
        # until the first time step precalculates the value
        self._current_value: float = np.nan

        # used for temporary storage of tables during deck parsing
        self._temporary_table: tuple[FloatArray | DateArray, FloatArray] | None = None

    def set_table(self, table: TableData) -> None:
        """
        Set the table of x- and y-values the forecast interpolates in.

        The x-values are dates, or days since the start of the simulation. The
        table is held until 'replace_reference_table' rebases a dated table to
        the start date and validates it: at that point it must hold at least two
        rows, with x-values strictly increasing.

        Parameters
        ----------
        table
            Parsed table, x-values in the first column and y-values in the second.
        """
        x, y = build_table_1d_dated(table)
        self._temporary_table = (x, y)

    def replace_reference_table(self, reference: np.datetime64) -> None:
        if self._temporary_table is None:
            return

        x, y = self._temporary_table

        if is_date_array(x):
            x = timedelta_to_days(x - reference)

        check_table1d_input(x, y)

        self._set_table(x, y)
        self._temporary_table = None

    def precalculate(self, time: float) -> None:
        """
        Precalculate and cache the forecast value at the given time.

        Parameters
        ----------
        time
            Time passed since start date (days).
        """
        self._current_value = self.calculate(time)

    @overload
    def get(self, x: FloatArray, y: float | None = None) -> FloatArray: ...

    @overload
    def get(self, x: float | None = None, y: float | None = None) -> float: ...

    def get(self, x: FloatLike | None = None, y: float | None = None) -> FloatLike:
        """
        Return the forecast value: recalculated at ``x`` if given, else cached.

        Parameters
        ----------
        x
            Time passed since start date (days) to recalculate at; the cached value
            is returned when None.
        y
            Dummy input variable for calculations with getters of 2 input.

        Returns
        -------
        float or FloatArray
            Forecast value, in the shape of ``x``.
        """
        if x is not None:
            return self.calculate(x)
        else:
            return self._current_value
