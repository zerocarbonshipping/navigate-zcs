# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import assign_value
from navigate.core.node import Node
from navigate.core.node_type import VARIABLE
from navigate.core.nodes._calculator import _Calculator
from navigate.exceptions import no_value_assigned_error

if TYPE_CHECKING:
    from navigate.core.nodes.input_kinds import NumberInput


class Variable(Node, _Calculator):
    def __init__(self, name: str) -> None:
        Node.__init__(self, name, VARIABLE)
        _Calculator.__init__(self)

        # internal variables -----------------------------------------------------------
        self._value: NumberInput | None = None

    # external methods (DSL attributes) ------------------------------------------------
    def set_value(self, value):
        self._value = assign_value(value)

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:
        if self._value is None:
            no_value_assigned_error(self, "Value")

    def get(self, x=None, y=None):
        """
        Return the variable value with the multiplier, addition, and truncation.

        Parameters
        ----------
        x : float
            Dummy input variable for calculations with getters of 1 or 2 input.
        y : float or str
            Dummy input variable for calculations with getters of 2 input.

        Returns
        -------
        float :
            Response variable.
        """
        # a non-float value is an expression and must be evaluated
        value = self._value if isinstance(self._value, float) else self._value.get()

        return self._truncate(self.multiplier * (value + self.addition))
