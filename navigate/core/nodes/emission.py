# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core import Scalar, as_scalar, assign_id, assign_value
from navigate.core.enum_ import FuelTypeID
from navigate.core.node import Node
from navigate.core.node_type import CURVE, EMISSION, VARIABLE


class Emission(Node):
    def __init__(self, name):
        super().__init__(name, EMISSION)

        self.global_warming_potential = None
        self.fuel_type = None

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_global_warming_potential(self, global_warming_potential):
        """
        Set the Global Warming Potential (GWP) of the emission.

        Examples
        --------
        - 36.6
        - Curve("name")

        Parameters
        ----------
        global_warming_potential : float | NodeReference
            The Global Warming Potential of the emission.
        """

        self.global_warming_potential = assign_value(as_scalar(global_warming_potential), type_=(CURVE, VARIABLE), lower=0.)

    def set_fuel_type(self, fuel_type):
        """
        Set the fuel type associated with this emission for slip gating.

        When set, this emission will only receive slip contributions from fuels
        whose fuel type matches this value.

        Examples
        --------
        - METHANE

        Parameters
        ----------
        fuel_type : str
            The fuel type that produces this emission when slipping.
        """

        self.fuel_type = assign_id(fuel_type, FuelTypeID)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):
        if self.global_warming_potential is None:
            self.global_warming_potential = Scalar(0.)
