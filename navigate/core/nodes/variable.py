# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Variable node, a single number read through the calculator getter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import assign_value
from navigate.core.node import Node
from navigate.core.node_type import VARIABLE
from navigate.core.nodes._calculator import _Calculator
from navigate.exceptions import no_value_assigned_error

if TYPE_CHECKING:
    from navigate.core.nodes.input_kinds import NumberInput
    from navigate.util import FloatLike


class Variable(Node, _Calculator):
    """
    A single number, scaled and bounded like the value of any calculator.

    Parameters
    ----------
    name
        Node name.
    """

    def __init__(self, name: str) -> None:
        Node.__init__(self, name, VARIABLE)
        _Calculator.__init__(self)

        # internal variables -----------------------------------------------------------
        self._value: NumberInput | None = None

    # external methods (DSL attributes) ------------------------------------------------
    def set_value(self, value: NumberInput) -> None:
        """
        Set the value of the variable.

        Parameters
        ----------
        value
            Value of the variable.
        """
        self._value = assign_value(value)

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:
        if self._value is None:
            no_value_assigned_error(self, "Value")

    def get(self, x: FloatLike | None = None, y: FloatLike | None = None) -> float:
        """
        Return the variable value with the multiplier, addition, and truncation.

        Parameters
        ----------
        x
            Dummy input variable for calculations with getters of 1 or 2 input.
        y
            Dummy input variable for calculations with getters of 2 input.

        Returns
        -------
        float
            Response variable.
        """
        # unset only on a variable read before check_requirements has run
        if self._value is None:
            no_value_assigned_error(self, "Value")

        # a non-float value is an expression and must be evaluated
        value = self._value if isinstance(self._value, float) else self._value.get()

        return self._truncate(self.multiplier * (value + self.addition))
