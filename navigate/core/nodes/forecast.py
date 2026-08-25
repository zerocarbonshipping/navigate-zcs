# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.id_ import FORECAST
from navigate.core.node import Node
from navigate.core.nodes._table1d import _Table1D, check_table1D_input
from navigate.core.table_data import TableData, build_table_1d
from navigate.exceptions import no_value_assigned_error
from navigate.util import timedelta_to_days


class Forecast(Node, _Table1D):
    def __init__(self, name: str) -> None:
        Node.__init__(self, name)
        _Table1D.__init__(self)

        self._type = FORECAST

        self.allow_dates_in_table = True

        # temporarily stored variables at current time-step
        self._current_value: float | None = None

        # used for temporary storage of tables during deck parsing
        self._temporary_table: tuple | None = None
        self._x_date: np.ndarray | None = None

    def initialize(self) -> None:
        if self._table is None:
            no_value_assigned_error(self, 'Table')

    def get(self, x: float | None = None, y: float | None = None) -> float:
        """
        Parameters
        ----------
        x
            Dummy input variable for calculations with getters of 1 input.
        y
            Dummy input variable for calculations with getters of 2 input.

        Returns
        -------
        Precalculated value.
        """
        if x is not None:
            return self.calculate(x)
        else:
            return self._current_value

    def get_x_date(self) -> np.ndarray | None:
        return self._x_date

    def precalculate(self, time: float | np.ndarray) -> None:
        """
        Parameters
        ----------
        time
            Time passed since start date (years).
        """
        self._current_value = self.calculate(time)

    def set_table(self, table: TableData) -> None:
        x, y = build_table_1d(table, allow_date=True)
        self._temporary_table = (x, y)

    def replace_reference_table(self, reference: np.datetime64) -> None:
        if self._temporary_table is None:
            return

        x, y = self._temporary_table
        self._x_date = x

        if np.issubdtype(x.dtype, np.datetime64):
            x = timedelta_to_days(x - reference)

        check_table1D_input(x, y)

        self._set_table(x, y)
        self._temporary_table = None
