# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Surface node, a two-input table lookup read through its getter."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from navigate.core.enum_ import ExtrapolateID
from navigate.core.node import Node
from navigate.core.node_type import SURFACE
from navigate.core.nodes._table2d import _Table2D, check_table2d_input
from navigate.core.table_data import TableData, build_table_2d

if TYPE_CHECKING:
    from navigate.util import FloatArray, FloatLike

logger = logging.getLogger(__name__)


class Surface(Node, _Table2D):
    """
    A table of z against x and y, interpolated at the inputs it is evaluated with.

    Parameters
    ----------
    name
        Node name.
    """

    def __init__(self, name: str) -> None:
        Node.__init__(self, name, SURFACE)
        _Table2D.__init__(self)

        # used for temporary storage of the table during deck parsing
        self._temporary_table: tuple[FloatArray, FloatArray, FloatArray] | None = None

    def set_table(self, table: TableData) -> None:
        """
        Set the table of x-, y- and z-values the surface interpolates in.

        Both the x-values and the y-values must be strictly increasing, and the
        number of z-values must equal the number of x-values times the number of
        y-values. The table is built once the whole definition has been read, so
        the order of the attributes within the definition does not matter.

        Parameters
        ----------
        table
            Parsed table: y-values in the header row, x-values down the first
            column of every row below it, z-values filling the rest.
        """
        x, y, z = build_table_2d(table)
        check_table2d_input(x, y, z)
        self._temporary_table = (x, y, z)

    def build_table(self) -> None:
        """Build the pending table with the interpolation and extrapolation set."""
        if self._temporary_table is None:
            return

        x, y, z = self._temporary_table
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

    def get(self, x: FloatLike | None, y: FloatLike | None) -> FloatLike:
        """
        Return the interpolated surface value at (x, y).

        Parameters
        ----------
        x
            First input variable. None, which an expression passes on when it
            is evaluated without input, is rejected.
        y
            Second input variable, rejected when None like ``x``.

        Returns
        -------
        float or FloatArray
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
