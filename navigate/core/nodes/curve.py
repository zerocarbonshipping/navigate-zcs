# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core.node import Node
from navigate.core.node_type import CURVE
from navigate.core.nodes._table1d import _Table1D, check_table1d_input
from navigate.core.table_data import TableData, build_table_1d
from navigate.exceptions import no_value_assigned_error


class Curve(Node, _Table1D):
    def __init__(self, name: str) -> None:
        Node.__init__(self, name)
        _Table1D.__init__(self)

        self.type = CURVE

    def initialize(self) -> None:
        if self._table is None:
            no_value_assigned_error(self, 'Table')

    def get(self, x: float, y: float | None = None) -> float:
        """
        Parameters
        ----------
        x
            Input variable.
        y
            Dummy input variable for calculations with getters of 2 input.

        Returns
        -------
        Response variable.
        """
        return self.calculate(x)

    def set_table(self, table: TableData) -> None:
        x, y = build_table_1d(table)
        check_table1d_input(x, y)
        self._set_table(x, y)
