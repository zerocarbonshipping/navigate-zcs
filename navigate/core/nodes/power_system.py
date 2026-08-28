# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core import assign_value
from navigate.core.enum_ import EnergyDemandTypeID
from navigate.core.node_type import CONVERTER, POWER_SYSTEM
from navigate.core.nodes._machinery import _Machinery
from navigate.exceptions import no_value_assigned_error
from navigate.util import list_is_unique


class PowerSystem(_Machinery):
    def __init__(self, name):
        super().__init__(name)

        self.type = POWER_SYSTEM
        # converters
        self.propulsion = None   # Converter, main engine delivering propulsion power
        self.electrical = None   # Converter, auxiliary engine delivering electrical power
        self.heat = None         # Converter, boiler delivering heat

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_propulsion(self, propulsion):
        """
        Set the converter used to satisfy the propulsion demand.

        Examples
        --------
        - Converter("name")

        Parameters
        ----------
        propulsion : NodeReference
            A converter used to satisfy the propulsion demand.
        """

        self.propulsion = assign_value(propulsion, scalar=False, type_=CONVERTER)

    def set_electrical(self, electrical):
        """
        Set the converter used to satisfy the electrical demand.

        Examples
        --------
        - Converter("name")

        Parameters
        ----------
        electrical : NodeReference
            A converter used to satisfy the electrical demand.
        """

        self.electrical = assign_value(electrical, scalar=False, type_=CONVERTER)

    def set_heat(self, heat):
        """
        Set the converter used to satisfy the heat demand.

        Examples
        --------
        - Converter("name")

        Parameters
        ----------
        heat : NodeReference
            A converter used to satisfy the heat demand.
        """

        self.heat = assign_value(heat, scalar=False, type_=CONVERTER)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):

        if not self.propulsion:
            no_value_assigned_error(self, 'Propulsion')

        if not self.electrical:
            no_value_assigned_error(self, 'Electrical')

        if not self.heat:
            no_value_assigned_error(self, 'Heat')

        # downstream code sums over the converters (installed power, cost, fuel demand); a shared one would double-count
        names = (self.propulsion.name, self.electrical.name, self.heat.name)
        if not list_is_unique(names):
            raise ValueError("{}: 'Propulsion', 'Electrical' and 'Heat' must be three distinct"
                             " converters, got {}.".format(self, names))

        self._initialize_machinery()

    def get_converters(self):
        return self.propulsion, self.electrical, self.heat

    def get_converter_by_energy_type(self, demand_type):
        match demand_type:
            case EnergyDemandTypeID.PROPULSION:
                return self.propulsion
            case EnergyDemandTypeID.ELECTRICAL:
                return self.electrical
            case EnergyDemandTypeID.HEAT:
                return self.heat
