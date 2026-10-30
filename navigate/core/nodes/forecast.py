# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Forecast node, a dated table lookup evaluated at the current time."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np

from navigate.core import deck_attribute
from navigate.core.node import Node
from navigate.core.node_type import FORECAST
from navigate.core.nodes._table1d import _Table1D
from navigate.core.table_data import TableData, build_table_1d_dated
from navigate.util import is_date_array, timedelta_to_days

if TYPE_CHECKING:
    from navigate.util.types_ import DateArray, FloatArray, FloatLike


class Forecast(Node, _Table1D):
    """
    A table of y against time, precalculated once per time-step.

    Parameters
    ----------
    name
        Node name.
    """

    type = FORECAST

    def __init__(self, name: str) -> None:
        Node.__init__(self, name)
        _Table1D.__init__(self)

        # internal variables -----------------------------------------------------------
        # nan until the first time-step precalculates the value
        self._current_value: float = np.nan

        # the table read from the deck, pending until it is built
        self._pending_table: tuple[FloatArray | DateArray, FloatArray] | None = None

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(required=True)
    def set_table(self, table: TableData) -> None:
        """Set the table of x- and y-values the forecast interpolates in."""
        self._pending_table = build_table_1d_dated(table)

    # internal methods -----------------------------------------------------------------
    def check_consistency(self) -> None:
        self._check_bounds_consistency()

    def build_table(self, start_date: np.datetime64) -> None:
        """Build the pending table, its dates counted in days from the start date."""
        if self._pending_table is None:
            return

        x, y = self._pending_table

        if is_date_array(x):
            x = timedelta_to_days(x - start_date)

        self._check_table(x, y)

        self._set_table(x, y)
        self._pending_table = None

    def precalculate(self, time: float) -> None:
        """
        Precalculate and cache the forecast value at the given time.

        Parameters
        ----------
        time
            Time passed since start date, in days.
        """
        self._current_value = self.calculate(time)

    @overload
    def get(self, x: float | None = None, y: FloatLike | None = None) -> float: ...

    @overload
    def get(self, x: FloatArray, y: FloatLike | None = None) -> FloatArray: ...

    def get(self, x: FloatLike | None = None, y: FloatLike | None = None) -> FloatLike:
        """
        Return the forecast value: recalculated at ``x`` if given, else cached.

        Parameters
        ----------
        x
            Time passed since start date to recalculate at, in days; the cached
            value is returned when None.
        y
            Ignored; it exists because expressions call every getter with two inputs.

        Returns
        -------
        FloatLike
            Forecast value, in the shape of ``x``.
        """
        if x is None:
            return self._current_value

        return self.calculate(x)
