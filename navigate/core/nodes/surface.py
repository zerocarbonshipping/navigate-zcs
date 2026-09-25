# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from navigate.core.enum_ import ExtrapolateID
from navigate.core.node import Node
from navigate.core.node_type import SURFACE
from navigate.core.nodes._table2d import _Table2D, check_table2d_input
from navigate.core.table_data import TableData, build_table_2d

if TYPE_CHECKING:
    from navigate.util import FloatLike

logger = logging.getLogger(__name__)


class Surface(Node, _Table2D):
    def __init__(self, name: str) -> None:
        Node.__init__(self, name, SURFACE)
        _Table2D.__init__(self)

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

    def set_table(self, table: TableData) -> None:
        x, y, z = build_table_2d(table)
        check_table2d_input(x, y, z)
        self._set_table(x, y, z)
