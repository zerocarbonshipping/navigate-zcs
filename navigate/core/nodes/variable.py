# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core import assign_value
from navigate.core.id_ import VARIABLE
from navigate.core.node import Node
from navigate.core.nodes._calculator import _Calculator
from navigate.exceptions import no_value_assigned_error


class Variable(Node, _Calculator):
    def __init__(self, name):
        Node.__init__(self, name)
        _Calculator.__init__(self)

        self._type = VARIABLE

        self._value = None

    def __repr__(self):
        return str(self.get())

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_value(self, value):
        self._value = assign_value(value)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):
        if self._value is None:
            no_value_assigned_error(self, 'Value')

    def get(self, x=None, y=None):
        """

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

        if isinstance(self._value, float):
            value = self._value
        else:
            # expression
            value = self._value.get()

        return self._truncate(self._multiplier * (value + self._addition))
