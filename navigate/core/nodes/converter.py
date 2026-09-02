# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core import (
    Scalar,
    as_list,
    as_scalar,
    assign_id,
    assign_id_list,
    assign_value,
    command_assignment_to_dict,
    command_assignment_to_tuple_dict,
)
from navigate.core.enum_ import FuelTypeID
from navigate.core.node_type import CONVERTER, FORECAST, VARIABLE
from navigate.core.nodes._machinery import _Machinery
from navigate.exceptions import no_value_assigned_error
from navigate.util import list_is_unique


class Converter(_Machinery):
    def __init__(self, name):
        super().__init__(name, CONVERTER)

        # power
        self.power_capacity = None         # float, power capacity of the Converter, MW
        self.minimum_load = None           # float, minimum load, fraction of power capacity

        # fuels
        self.main_fuel_types = []          # list of int, IDs to fuel types
        self.pilot_fuel_types = []         # list of int, IDs to fuel types
        self.minimum_pilot_fuel = None     # list of floats, minimum pilot fuel fraction

        # performance
        self.efficiency = None             # float, conversion efficiency from potential to kinetic energy

        # emissions
        self.consumption_ttw = {}          # dict of floats, emissions from consumption in the engine, ton/ton
        self.slip_fraction = {}            # dict[FuelTypeID, Scalar], fraction of fuel mass escaping unburned

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_power_capacity(self, power_capacity):
        """
        Set the maximum power capacity of the converter.

        Examples
        --------
        - 50.0
        - Variable("name")

        Parameters
        ----------
        power_capacity : float | NodeReference
            The maximum power capacity of the converter.
        """

        self.power_capacity = assign_value(as_scalar(power_capacity), type_=VARIABLE, lower=0.)

    def set_minimum_load(self, minimum_load):
        """
        Set the minimum load as a fraction of power capacity.

        Examples
        --------
        - 0.3
        - Variable("name")

        Parameters
        ----------
        minimum_load : float | NodeReference
            The minimum load as a fraction of power capacity.
        """

        self.minimum_load = assign_value(as_scalar(minimum_load), type_=VARIABLE, lower=0., upper=1.)

    def set_main_fuel_types(self, main_fuel_types):
        """
        Set the main fuel types of the converter.

        Examples
        --------
        - OIL
        - [METHANOL, OIL]

        Parameters
        ----------
        main_fuel_types : list[str]
            List of main fuel types of the converter.
        """

        self.main_fuel_types = assign_id_list(as_list(main_fuel_types), FuelTypeID, length=(1, None))

    def set_pilot_fuel_types(self, pilot_fuel_types):
        """
        Set the pilot fuel types of the converter.

        Examples
        --------
        - OIL
        - [METHANOL, OIL]

        Parameters
        ----------
        pilot_fuel_types : list[str]
            List of pilot fuel types of the converter.
        """

        self.pilot_fuel_types = assign_id_list(as_list(pilot_fuel_types), FuelTypeID, length=(1, None))

    def set_minimum_pilot_fuel(self, minimum_pilot_fuel):
        """
        Set the minimum pilot fuel fraction required to utilize the converter in GJ/GJ.

        Examples
        --------
        - 0.05
        - Forecast("name")

        Parameters
        ----------
        minimum_pilot_fuel : float | NodeReference
            Minimum pilot fuel fraction.
        """

        self.minimum_pilot_fuel = assign_value(as_scalar(minimum_pilot_fuel), type_=(VARIABLE, FORECAST), lower=0., upper=1.)

    def set_efficiency(self, efficiency):
        """
        Set the energy conversion efficiency from the potential energy in the fuel to the kinetic energy required.

        Examples
        --------
        - 0.3
        - Variable("name")

        Parameters
        ----------
        efficiency : float | NodeReference
            The energy conversion efficiency.
        """

        self.efficiency = assign_value(as_scalar(efficiency), type_=VARIABLE, lower=0., upper=1.)

    # external commands called in the input deck -----------------------------------------------------------------------
    def set_slip_fraction(self, fuel_type, value):
        """
        Set the fraction of fuel mass that escapes unburned (slip) when using a specific fuel type.

        Examples
        --------
        - METHANE, 0.03
        - METHANE, Variable("methane_slip")

        Parameters
        ----------
        fuel_type : str
            Type of fuel which has slip when used.
        value : float | NodeReference
            Fraction of fuel mass escaping unburned.
        """

        id_ = assign_id(fuel_type, FuelTypeID)

        if id_ not in self.get_fuel_types():
            raise ValueError(f"received {fuel_type} which is not available for {self}.")

        command_assignment_to_dict(id_, value, self.slip_fraction, type_=VARIABLE, lower=0., upper=1.)

    def set_consumption_ttw(self, fuel_type, emission_name, value):
        """
        Set a consumption related emission of a specific emission when using a specific fuel type in the converter.

        Notice that this number is given in the unit ton emission / ton fuel into the engine. I.e., if the engine
        has slip (e.g., methane slip) then this number is already adjusted for this.

        Examples
        --------
        - OIL, "nitrous_oxide", 0.001
        - OIL, "carbon_dioxide", Variable("name")

        Parameters
        ----------
        fuel_type : str
            Type of fuel which has a consumption related emission when used.
        emission_name : str
            Name of emission emitted as particles.
        value : float | NodeReference
            Ton of emission emitted per ton of fuel consumed.
        """

        id_ = assign_id(fuel_type, FuelTypeID)

        if id_ not in self.get_fuel_types():
            raise ValueError(f"received {fuel_type} which is not available for {self}.")

        # neccesary due to incoherent error thrown if
        # passing a non-existing key to an empty dict
        key = (id_, emission_name)
        if key not in self.consumption_ttw:
            raise KeyError(f"{emission_name}")

        command_assignment_to_tuple_dict(key, value, self.consumption_ttw, type_=VARIABLE, lower=0.)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):

        if self.power_capacity is None:
            no_value_assigned_error(self, 'PowerCapacity')

        if not self.main_fuel_types:
            no_value_assigned_error(self, 'MainFuelTypes')

        if not list_is_unique(self.main_fuel_types):
            raise ValueError("{}: All 'MainFuelTypes' must be unique.".format(self))

        if self.pilot_fuel_types:

            if not list_is_unique(self.main_fuel_types + self.pilot_fuel_types):
                raise ValueError("{}: All fuel types across 'MainFuelTypes' and 'PilotFuelTypes' must be unique."
                                 .format(self))

            if self.minimum_pilot_fuel is None:
                self.minimum_pilot_fuel = Scalar(0)

        if not self.efficiency:
            no_value_assigned_error(self, 'Efficiency')

        self._initialize_machinery()

        # default slip fractions
        for fuel_type in self.slip_fraction:
            if not self.slip_fraction[fuel_type]:
                self.slip_fraction[fuel_type] = Scalar(0)

        # default emissions from consumption in the engine
        for fuel_type, emission_name in self.consumption_ttw:
            if not self.consumption_ttw[(fuel_type, emission_name)]:
                self.consumption_ttw[(fuel_type, emission_name)] = Scalar(0)

    def initialize_dependencies(self, emissions):
        """
        Initialize emissions parameters with relevant keys.

        Parameters
        ----------
        emissions : dict[str, Emission]
            Dict of class Emission.
        """

        if not self.slip_fraction:
            self.slip_fraction = {fuel_type: None for fuel_type in self.get_fuel_types()}

        if not self.consumption_ttw:
            self.consumption_ttw = {(fuel_type, emission_name): None
                                    for fuel_type in self.get_fuel_types()
                                    for emission_name in emissions}

    def get_fuel_types(self):
        return self.main_fuel_types + self.pilot_fuel_types

    def is_dual_fuel(self):
        return self.pilot_fuel_types
