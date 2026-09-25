# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Curve node, a one-input table lookup read through its getter."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

from navigate.core.node import Node
from navigate.core.node_type import CURVE
from navigate.core.nodes._table1d import _Table1D, check_table1d_input
from navigate.core.table_data import TableData, build_table_1d

if TYPE_CHECKING:
    from navigate.util import FloatArray, FloatLike


class Curve(Node, _Table1D):
    """
    A table of y against x, interpolated at the input it is evaluated with.

    Parameters
    ----------
    name
        Node name.
    """

    def __init__(self, name: str) -> None:
        Node.__init__(self, name, CURVE)
        _Table1D.__init__(self)

    def set_table(self, table: TableData) -> None:
        """
        Set the table of x- and y-values the curve interpolates in.

        The table must hold at least two rows, and its x-values must be strictly
        increasing.

        Parameters
        ----------
        table
            Parsed table, x-values in the first column and y-values in the second.
        """
        x, y = build_table_1d(table)
        check_table1d_input(x, y)
        self._set_table(x, y)

    @overload
    def get(self, x: FloatArray, y: FloatLike | None = None) -> FloatArray: ...

    @overload
    def get(self, x: float, y: FloatLike | None = None) -> float: ...

    def get(self, x: FloatLike | None, y: FloatLike | None = None) -> FloatLike:
        """
        Return the interpolated table value at x.

        Parameters
        ----------
        x
            Input variable. None, which an expression passes on when it is
            evaluated without input, is rejected.
        y
            Dummy input variable for calculations with getters of 2 input.

        Returns
        -------
        float or FloatArray
            Response variable, in the shape of ``x``.

        Raises
        ------
        ValueError
            If ``x`` is None.
        """
        if x is None:
            raise ValueError(f"{self}: Evaluating a Curve requires an input 'x'.")

        return self.calculate(x)
