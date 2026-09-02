# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import logging

from navigate.core.enum_ import ExtrapolateID
from navigate.core.node import Node
from navigate.core.node_type import SURFACE
from navigate.core.nodes._table2d import _Table2D, check_table2d_input
from navigate.core.table_data import TableData, build_table_2d
from navigate.exceptions import no_value_assigned_error

logger = logging.getLogger(__name__)


class Surface(Node, _Table2D):
    def __init__(self, name: str) -> None:
        Node.__init__(self, name, SURFACE)
        _Table2D.__init__(self)

    def initialize(self) -> None:
        if self._table is None:
            no_value_assigned_error(self, 'Table')

        if self.extrapolate == ExtrapolateID.FLAT:
            if self._outside is None:
                raise ValueError("{}: 'Outside' must be defined when 'Extrapolate' is set to FLAT.")

        else:
            if self._outside is not None:
                logger.warning("{}: 'Outside' is defined, but ignored since 'Extrapolate' is set to LINEAR.")

    def get(self, x: float, y: float) -> float:
        return self.calculate(x, y)

    def set_table(self, table: TableData) -> None:
        x, y, z = build_table_2d(table)
        check_table2d_input(x, y, z)
        self._set_table(x, y, z)
