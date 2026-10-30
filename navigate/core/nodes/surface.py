# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Surface node, a two-input table lookup read through its getter."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

from navigate.core import deck_attribute
from navigate.core.node import Node
from navigate.core.node_type import SURFACE
from navigate.core.nodes._table2d import _Table2D
from navigate.core.table_data import TableData, build_table_2d

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray, FloatLike


class Surface(Node, _Table2D):
    """
    A table of z against x and y, interpolated at the inputs it is evaluated with.

    Parameters
    ----------
    name
        Node name.
    """

    type = SURFACE

    def __init__(self, name: str) -> None:
        Node.__init__(self, name)
        _Table2D.__init__(self)

        # internal variables -----------------------------------------------------------
        # the table read from the deck, pending until it is built
        self._pending_table: tuple[FloatArray, FloatArray, FloatArray] | None = None

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(required=True)
    def set_table(self, table: TableData) -> None:
        """Set the table of x-, y- and z-values the surface interpolates in."""
        x, y, z = build_table_2d(table)
        self._check_table(x, y, z)
        self._pending_table = (x, y, z)

    # internal methods -----------------------------------------------------------------
    def check_consistency(self) -> None:
        self._check_extrapolate_consistency()
        self._check_bounds_consistency()

    def build_table(self) -> None:
        """Build the pending table with the interpolation and extrapolation set."""
        if self._pending_table is None:
            return

        x, y, z = self._pending_table
        self._set_table(x, y, z)
        self._pending_table = None

    @overload
    def get(self, x: float | None, y: float | None) -> float: ...

    @overload
    def get(self, x: FloatArray, y: FloatLike | None) -> FloatArray: ...

    @overload
    def get(self, x: FloatLike | None, y: FloatLike | None) -> FloatLike: ...

    def get(self, x: FloatLike | None, y: FloatLike | None) -> FloatLike:
        """
        Return the interpolated table value at (x, y).

        Parameters
        ----------
        x
            First input variable. None, which an expression passes on when it
            is evaluated without input, is rejected.
        y
            Second input variable. None, which an expression passes on when it
            is evaluated without input, is rejected.

        Returns
        -------
        FloatLike
            Response variable, in the broadcast shape of ``x`` and ``y``.

        Raises
        ------
        ValueError
            If ``x`` or ``y`` is None.
        """
        if x is None or y is None:
            raise ValueError(
                f"{self}: Evaluating a Surface requires both inputs 'x' and 'y'."
            )

        return self.calculate(x, y)
