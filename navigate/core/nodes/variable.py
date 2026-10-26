# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Variable node, a single number read through the calculator getter."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np

from navigate.core import assign_value, deck_attribute
from navigate.core.node import Node
from navigate.core.node_type import VARIABLE
from navigate.core.nodes._calculator import _Calculator

if TYPE_CHECKING:
    from navigate.core.types_ import NumberInput
    from navigate.util.types_ import FloatArray, FloatLike


class Variable(Node, _Calculator):
    """
    A single number, scaled and bounded like the value of any calculator.

    Parameters
    ----------
    name
        Node name.
    """

    type = VARIABLE

    def __init__(self, name: str) -> None:
        Node.__init__(self, name)
        _Calculator.__init__(self)

        # external variables -----------------------------------------------------------
        self.value: NumberInput

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(required=True)
    def set_value(self, value: NumberInput) -> None:
        """Set the value of the variable."""
        self.value = assign_value(value, allow_infinite=True)

    # internal methods -----------------------------------------------------------------
    @overload
    def get(self, x: float | None = None, y: FloatLike | None = None) -> float: ...

    @overload
    def get(self, x: FloatArray, y: FloatLike | None = None) -> FloatArray: ...

    def get(self, x: FloatLike | None = None, y: FloatLike | None = None) -> FloatLike:
        """
        Return the bounded value, broadcast to the shape of an array input.

        Parameters
        ----------
        x
            Dummy first input matching the calculator getters; an array sets
            the output shape.
        y
            Dummy second input matching the calculator getters.

        Returns
        -------
        float or FloatArray
            The bounded value, or an array of it in the shape of ``x``.
        """
        value = self._transform(self._evaluate_number(self.value))

        # broadcasting is what keeps a Variable substitutable for a calculator
        # node, whose getter answers an array input with an array
        if isinstance(x, np.ndarray):
            return np.full_like(x, value)

        return value
