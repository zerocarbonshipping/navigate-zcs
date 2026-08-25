# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core import Scalar, as_scalar, assign_id, assign_value, command_assignment_to_dict
from navigate.core.enum_ import FuelTypeID
from navigate.core.id_ import FUEL, VARIABLE
from navigate.core.node import Node
from navigate.exceptions import no_value_assigned_error


class Fuel(Node):
    def __init__(self, name):
        super().__init__(name)

        self._type = FUEL

        # definition
        self.fuel_type = None              # enum, fuel type ID

        # physical properties
        self.lower_heating_value = None    # float, lower heating value GJ/ton
        self.mass_density = None           # float, mass density ton/m3 (equivalent to g/cm3)

        # emissions
        self.TTW = {}                      # dict, emission factor in ton of emission per ton of fuel

        # internal attributes
        self.liquid_market = False         # bool, whether the fuel belongs to a liquid market

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_fuel_type(self, fuel_type):
        """
        Set the fuel type of the fuel.

        Examples
        --------
        - OIL
        - AMMONIA
        - METHANOL

        Parameters
        ----------
        fuel_type : str
            Type of fuel.
        """

        self.fuel_type = assign_id(fuel_type, FuelTypeID)

    def set_lower_heating_value(self, lower_heating_value):
        """
        Set the lower heating value of the fuel in GJ/ton.

        Examples
        --------
        - 42.6

        Parameters
        ----------
        lower_heating_value : float | NodeReference
            The lower heating value of the fuel in GJ/ton.
        """

        self.lower_heating_value = assign_value(as_scalar(lower_heating_value), type_=VARIABLE, lower=0.)

    def set_mass_density(self, mass_density):
        """
        Set the mass density of the fuel.

        Examples
        --------
        - 0.96

        Parameters
        ----------
        mass_density : float | NodeReference
            The mass density of the fuel.
        """

        self.mass_density = assign_value(as_scalar(mass_density), type_=VARIABLE, lower=0.)

    # external commands called in the input deck -----------------------------------------------------------------------
    def set_ttw(self, emission_name, TTW):
        """
        Set the TTW emission factor during a stoichiometric process of fuel conversion to energy.

        Examples
        --------
        - "emission_name", 2.75
        - "emission_name", Variable("name")

        Parameters
        ----------
        emission_name : str
            Name of emission emitted.
        TTW : float | NodeReference
            Ton of emissions per ton of fuel.
        """

        command_assignment_to_dict(emission_name, TTW, self.TTW, type_=VARIABLE, lower=0.)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):
        if self.fuel_type is None:
            no_value_assigned_error(self, 'FuelType')

        if (self.lower_heating_value is None) or (self.lower_heating_value.get() == 0.):
            raise ValueError("{}: Attribute 'LowerHeatingValue' must be defined and greater than zero.".format(self))

        if (self.mass_density is None) or (self.mass_density.get() == 0.):
            raise ValueError("{}: Attribute 'MassDensity' must be defined and greater than zero.".format(self))

        for emission_name in self.TTW:
            if self.TTW[emission_name] is None:
                self.TTW[emission_name] = Scalar(0.)

    def initialize_dependencies(self, emissions):

        for emission_name in emissions:
            self.TTW.setdefault(emission_name, None)

    def belongs_to_liquid_market(self):
        return self.liquid_market

    def get_TTW(self, emission_name):
        return self.TTW[emission_name]
