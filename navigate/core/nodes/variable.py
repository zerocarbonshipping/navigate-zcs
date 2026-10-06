# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Variable node, a single number read through the calculator getter."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np

from navigate.core import assign_value
from navigate.core.node import Node
from navigate.core.node_type import VARIABLE
from navigate.core.nodes._calculator import _Calculator, evaluate_number
from navigate.exceptions import UnassignedAttributeError

if TYPE_CHECKING:
    from navigate.core.types_ import NumberInput
    from navigate.util import FloatArray, FloatLike


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

        An expression is evaluated each time the variable is read, without
        inputs. INF and -INF are accepted here and checked, like any value, by
        each attribute the variable is assigned to.

        Parameters
        ----------
        value
            Value of the variable.
        """
        self._value = assign_value(value, allow_infinite=True)

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:
        if self._value is None:
            raise UnassignedAttributeError(str(self), "Value")

    @overload
    def get(self, x: FloatArray, y: FloatLike | None = None) -> FloatArray: ...

    @overload
    def get(self, x: float | None = None, y: FloatLike | None = None) -> float: ...

    def get(self, x: FloatLike | None = None, y: FloatLike | None = None) -> FloatLike:
        """
        Return the variable value with the multiplier, addition, and truncation.

        Parameters
        ----------
        x
            Dummy first input matching the calculator getters; an array sets
            the output shape.
        y
            Dummy input variable for calculations with getters of 2 input.

        Returns
        -------
        float or FloatArray
            Response variable, or an array of it in the shape of ``x``.
        """
        # unset only on a variable read before check_requirements has run
        if self._value is None:
            raise UnassignedAttributeError(str(self), "Value")

        # the inputs are dummies, so every expression is evaluated without them
        value = self._transform(evaluate_number(self._value))

        # broadcasting is what keeps a Variable substitutable for a calculator
        # node, whose getter answers an array input with an array
        if isinstance(x, np.ndarray):
            return np.full_like(x, value)

        return value
