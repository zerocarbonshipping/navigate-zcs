# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import logging

import numpy as np

from navigate.core.enum_ import ExtrapolateID
from navigate.core.node import Node
from navigate.core.node_type import TIMETABLE
from navigate.core.nodes._table2d import _Table2D, check_table2D_input
from navigate.core.table_data import TableData, build_table_2d
from navigate.exceptions import no_value_assigned_error
from navigate.util import timedelta_to_days

logger = logging.getLogger(__name__)


class Timetable(Node, _Table2D):
    def __init__(self, name: str) -> None:
        Node.__init__(self, name)
        _Table2D.__init__(self)

        self.type = TIMETABLE

        self.allow_dates_in_table = True

        # temporarily stored variables at current time-step
        self._current_time: float | None = None

        # used for temporary storage of tables during deck parsing
        self._temporary_table: tuple | None = None

    def initialize(self) -> None:
        if self._table is None:
            no_value_assigned_error(self, 'Table')

        if self._extrapolate == ExtrapolateID.FLAT:
            if self._outside is None:
                raise ValueError("{}: 'Outside' must be defined when 'Extrapolate' is set to FLAT.")

        else:
            if self._outside is not None:
                logger.warning("{}: 'Outside' is defined, but ignored since 'Extrapolate' is set to LINEAR.")

    def get(self, x: float | None = None, y: float | None = None) -> float:
        if x is None:
            x = self._current_time
        return self.calculate(x, y)

    def set_current_time(self, time: float) -> None:
        self._current_time = time

    def set_table(self, table: TableData) -> None:
        x, y, z = build_table_2d(table, allow_date=True)
        self._temporary_table = (x, y, z)

    def replace_reference_table(self, reference: np.datetime64) -> None:
        if self._temporary_table is None:
            return

        x, y, z = self._temporary_table

        if np.issubdtype(x.dtype, np.datetime64):
            x = timedelta_to_days(x - reference)

        check_table2D_input(x, y, z)

        self._set_table(x, y, z)
        self._temporary_table = None
