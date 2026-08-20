# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

import navigate.core.id_ as id_
from navigate.core import Node, Scalar, as_list, as_scalar, assign_id, assign_list, assign_value
from navigate.core.enum_ import FuelTypeID
from navigate.core.expectations import VesselExpectation
from navigate.core.profiles import VesselProfile
from navigate.exceptions import no_value_assigned_error
from navigate.util import to_numpy, unique_list
from navigate.vessel.tank import Tank

if TYPE_CHECKING:
    from navigate.fuel import Emission, Fuel

logger = logging.getLogger(__name__)


class Vessel(Node):
    def __init__(self, name):
        super().__init__(name)

        self._type = id_.VESSEL

        # power demand
        self.propulsion_load = None          # float, Curve or Surface, load in MW (at sea)
        self.electrical_load_at_sea = None   # float, Curve or Surface, load in MW (at sea)
        self.electrical_load_in_port = None  # float, load in MW (in port)
        self.heat_load_at_sea = None         # float, Curve or Surface, load in MW (at sea)
        self.heat_load_in_port = None        # float, load in MW (in port)

        # fuel based power
        self.power_system = None   # class PowerSystem
        self.tanks: list[Tank] = []

        # voyage
        self.route = None              # class Route
        self.nominal_capacity = None   # float, nominal capacity of the vessel in TEU/DWT/GT

        # base cost
        self.CAPEX = None              # float, base CAPEX of vessel. Hull, etc.
        self.OPEX = None               # float, base OPEX of vessel. Hull, etc.
        self.lifetime = None           # float, lifetime of vessel
        self.lead_time = None          # float, lead time of vessel (only relevant for cost calculations)
        self.cost_of_capital = None    # float, cost of capital

        # tag
        self.fuel_type = None          # int, ID of primary fuel type

        # convenience properties
        self.usable_fuel_types = []    # list[FuelTypeID], list of fuel types usable in the power system of the vessel
        self.usable_fuels = {}         # dict[Fuel], dictionary of fuels usable in the power system of the vessel

        # cross-check properties
        self.fleet_assignment = None   # name of fleet vessel is assigned to

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_propulsion_load(self, propulsion_load):
        """
        Set the propulsion load in MW.
        This is the power required to propel the vessel at a given speed and draft (cargo utilization used as proxy).

        If a Curve is assigned it should return power (MW) as a function of speed (knots).
        If a Surface is assigned it should return power (MW) as a function of speed (knots) and cargo utilization (-).

        Examples
        --------
        - 16.5
        - Curve("name")
        - Surface("name")

        Parameters
        ----------
        propulsion_load : float
            The propulsion load  in MW.
        """

        self.propulsion_load = assign_value(as_scalar(propulsion_load),
                                            type_=(id_.CURVE, id_.SURFACE, id_.VARIABLE),
                                            lower=0.)

    def set_electrical_load_at_sea(self, electrical_load_at_sea):
        """
        Set the electrical load at sea in MW.
        This is the power required to run auxiliary systems on the vessel at sea at a given speed and cargo utilization.

        If a Curve is assigned it should return power (MW) as a function of speed (knots).
        If a Surface is assigned it should return power (MW) as a function of speed (knots) and cargo utilization (-).

        Examples
        --------
        - 16.5
        - Curve("name")
        - Surface("name")

        Parameters
        ----------
        electrical_load_at_sea : float
            The electrical load at sea in MW.
        """

        self.electrical_load_at_sea = assign_value(as_scalar(electrical_load_at_sea),
                                                   type_=(id_.CURVE, id_.SURFACE, id_.VARIABLE),
                                                   lower=0.)

    def set_electrical_load_in_port(self, electrical_load_in_port):
        """
        Set the electrical load in port in MW.
        This is the power required to run auxiliary systems on the vessel in port.

        Examples
        --------
        - 16.5

        Parameters
        ----------
        electrical_load_in_port : float
            The electrical load in port in MW.
        """

        self.electrical_load_in_port = assign_value(as_scalar(electrical_load_in_port),
                                                    type_=id_.VARIABLE,
                                                    lower=0.)

    def set_heat_load_at_sea(self, heat_load_at_sea):
        """
        Set the heat load at sea in MW.
        This is the power required to produce heat on the vessel at sea at a given speed and cargo utilization.

        If a Curve is assigned it should return power (MW) as a function of speed (knots).
        If a Surface is assigned it should return power (MW) as a function of speed (knots) and cargo utilization (-).

        Examples
        --------
        - 16.5
        - Curve("name")
        - Surface("name")

        Parameters
        ----------
        heat_load_at_sea : float
            The heating load at sea in MW.
        """

        self.heat_load_at_sea = assign_value(as_scalar(heat_load_at_sea),
                                             type_=(id_.CURVE, id_.SURFACE, id_.VARIABLE),
                                             lower=0.)

    def set_heat_load_in_port(self, heat_load_in_port):
        """
        Set the heating load in port in MW.
        This is the power required to produce heat on the vessel in port.

        Examples
        --------
        - 16.5

        Parameters
        ----------
        heat_load_in_port : float
            The heating load in port in MW.
        """

        self.heat_load_in_port = assign_value(as_scalar(heat_load_in_port), type_=id_.VARIABLE, lower=0.)

    def set_fuel_type(self, fuel_type):
        """
        Set the primary main fuel type of the vessel.

        If not assigned, the value is defaulted during initialization based on the assigned PowerSystem.

        Examples
        --------
        - OIL
        - AMMONIA
        - METHANOL

        Parameters
        ----------
        fuel_type : str
            Primary type of main fuel.
        """

        self.fuel_type = assign_id(fuel_type, FuelTypeID)

    def set_power_system(self, power_system):
        """
        Set the PowerSystem used to convert fuel to energy.

        Examples
        --------
        - PowerSystem("name")

        Parameters
        ----------
        power_system : NodeReference
            The powersystem used to convert fuel to energy.
        """

        self.power_system = assign_value(power_system, scalar=False, type_=id_.POWER_SYSTEM)

    def set_tanks(self, tanks):
        """
        Set the list of tanks used for onboard fuel storage.

        Examples
        --------
        - Tank("name")
        - [Tank("name1"), Tank("name2")]

        Parameters
        ----------
        tanks : list[NodeReference]
            List of node references to tanks.
        """

        self.tanks = assign_list(as_list(tanks), unique=True, scalar=False, type_=id_.TANK)

    def set_route(self, route):
        """
        Set the Route the vessel is sailing on.

        Examples
        --------
        - Route("name")

        Parameters
        ----------
        route : NodeReference
            The route the vessel is sailing on.
        """

        self.route = assign_value(route, scalar=False, type_=id_.ROUTE)

    def set_nominal_capacity(self, nominal_capacity):
        """
        Set the nominal cargo carrying capacity of the vessel.

        There is not a well-defined unit, it just has to match with the
        'Trade' attribute of the Fleet node the vessel is assigned to.
        In general the most logical unit for the vessel segment is applied:
        - Container: TEU (twenty-foot equivalent unit)
        - RoRo: CEU (car equivalent unit)
        - Bulk Carrier: DWT (dead weight tonnes)
        - etc.

        Examples
        --------
        - 8000

        Parameters
        ----------
        nominal_capacity : float | NodeReference
            The nominal cargo carrying capacity of the vessel.
        """

        self.nominal_capacity = assign_value(as_scalar(nominal_capacity), type_=id_.VARIABLE, lower=0.)

    def set_lifetime(self, lifetime):
        """
        Set the lifetime of the vessel in years.

        The vessel is scrapped when it surpasses its lifetime.

        Examples
        --------
        - 25

        Parameters
        ----------
        lifetime : float | NodeReference
            Lifetime of the vessel in years.
        """

        self.lifetime = assign_value(as_scalar(lifetime), type_=(id_.FORECAST, id_.VARIABLE),
                                     lower=0., inclusive_lower=False)

    def set_lead_time(self, lead_time):
        """
        Set the lead time of the vessel in years.

        The lead time is only used for the calculation of the levelized cost of a vessel (charter rate) and does
        not impact the delivery of vessels.

        Examples
        --------
        - 2

        Parameters
        ----------
        lead_time : float | NodeReference
            Lead time of the vessel in years.
        """

        self.lead_time = assign_value(as_scalar(lead_time), type_=(id_.FORECAST, id_.VARIABLE), lower=0.)

    def set_CAPEX(self, CAPEX):
        """
        Set the base CAPEX of building the vessel in USD.

        Examples
        --------
        - 100e6
        - Forecast("name")

        Parameters
        ----------
        CAPEX : float | NodeReference
            The base CAPEX of building the vessel in USD.
        """

        self.CAPEX = assign_value(as_scalar(CAPEX), type_=(id_.FORECAST, id_.VARIABLE), lower=0.)

    def set_OPEX(self, OPEX):
        """
        Set the base OPEX of maintaining the vessel in USD/year.

        Examples
        --------
        - 10e6
        - Forecast("name")

        Parameters
        ----------
        OPEX : float | NodeReference
            The base OPEX of maintaining the vessel in USD/year.
        """

        self.OPEX = assign_value(as_scalar(OPEX), type_=(id_.FORECAST, id_.VARIABLE), lower=0.)

    def set_cost_of_capital(self, cost_of_capital):
        """
        Set the cost of capital used in calculating the finance costs of the vessel.

        Also used as the discount rate for net present cost calculations for investment decisions.

        Examples
        --------
        - 0.1
        - Forecast("name")

        Parameters
        ----------
        cost_of_capital : float | NodeReference
            Cost of capital.
        """

        self.cost_of_capital = assign_value(as_scalar(cost_of_capital), type_=(id_.FORECAST, id_.VARIABLE), lower=0.)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):

        if self.propulsion_load is None:
            self.propulsion_load = Scalar(0.)

        if self.electrical_load_at_sea is None:
            self.electrical_load_at_sea = Scalar(0.)

        if self.electrical_load_in_port is None:
            self.electrical_load_in_port = Scalar(0.)

        if self.heat_load_at_sea is None:
            self.heat_load_at_sea = Scalar(0.)

        if self.heat_load_in_port is None:
            self.heat_load_in_port = Scalar(0.)

        if self.power_system is None:
            no_value_assigned_error(self, 'PowerSystem')

        if not self.tanks:
            no_value_assigned_error(self, 'Tanks')

        if self.route is None:
            no_value_assigned_error(self, 'Route')

        if self.nominal_capacity is None:
            no_value_assigned_error(self, 'NominalCapacity')

        if self.lifetime is None:
            self.lifetime = Scalar(25)

        if self.lead_time is None:
            self.lead_time = Scalar(0)

        if self.CAPEX is None:
            self.CAPEX = Scalar(0)

        if self.OPEX is None:
            self.OPEX = Scalar(0)

        if self.cost_of_capital is None:
            self.cost_of_capital = Scalar(0)

    def initialize_expectation(self, length: int, fuels: dict[str, Fuel]) -> None:

        self.expectation = VesselExpectation()
        self.expectation.initialize(length, self.route, fuels)

    def initialize_profile(self, timeline: np.ndarray, emissions: dict[str, Emission],
                           fuels: dict[str, Fuel], emissions_lifetime: float,
                           regulation_names: list[str] = (), levy_names: list[str] = ()) -> None:

        self.profile = VesselProfile()
        self.profile.initialize(timeline, emissions, fuels, emissions_lifetime, regulation_names, levy_names)

    def calculate_expectation(self, idx):
        self.expectation.set_speeds(idx, to_numpy(self.route.speeds))

    def calculate_profile(self, idx):
        """

        Parameters
        ----------
        idx : int
            Current time-step index.
        """

        self.profile.set_lifetime(idx, self.lifetime.get())
        self.profile.set_lead_time(idx, self.lead_time.get())

    def determine_usable_fuel_types(self):

        if self.usable_fuel_types:
            return

        tank_fuel_types = [fuel_type for tank in self.tanks for fuel_type in tank.get_fuel_types()]

        power_system_fuel_types = [fuel_type for converter in self.power_system.get_converters()
                                   for fuel_type in converter.get_fuel_types()]

        # check the tanks allow for storage of fuels used in the converters
        for converter in self.power_system.get_converters():

            main_fuel_types = converter.main_fuel_types
            pilot_fuel_types = converter.pilot_fuel_types

            if converter.is_dual_fuel():

                if converter.minimum_pilot_fuel.get() > 0.:

                    if not any((fuel_type in tank_fuel_types for fuel_type in pilot_fuel_types)):
                        raise ValueError("{}: Missing a tank which can store fuel of"
                                         " type(s) {} required as pilot fuel for {}."
                                         .format(self,
                                                 ', '.join(FuelTypeID(f).name for f in pilot_fuel_types),
                                                 converter))

            else:
                if not any((fuel_type in tank_fuel_types for fuel_type in main_fuel_types)):
                    raise ValueError("{}: Missing a tank which can store fuel of type(s) {} for {}."
                                     .format(self, ', '.join(FuelTypeID(f).name for f in main_fuel_types), converter))

        self.usable_fuel_types = unique_list(tank_fuel_types + power_system_fuel_types)

    def determine_usable_fuels(self, fuels_by_fuel_type):
        """

        Parameters
        ----------
        fuels_by_fuel_type : dict[FuelTypeID: list[Fuel]]
            All fuels in the simulation grouped by fuel type.
        """

        for fuel_type in self.usable_fuel_types:

            fuels = fuels_by_fuel_type[fuel_type]

            for fuel in fuels:

                self.usable_fuels.setdefault(fuel.get_name(), fuel)

        # check that the vessel can bunker
        if not self.usable_fuels:
            raise ValueError("{}: No overlap between the fuel types of the PowerSystem, Tanks and Fuels.".format(self))

    def determine_fuel_type(self):
        """
        The representative fuel type of a vessel is decided based on the sum of power capacity for the main fuel types
        across all converters in the power system. If multiple fuel types have the same power capacity, the one
        with the largest tank is chosen.

        TODO: The tank size should optimally be weighted by the LHV, but it might vary within a given fuel type
        """

        if self.fuel_type is not None:
            return

        power_system = self.power_system
        fuel_type_power = {}

        for converter in power_system.get_converters():

            main_fuel_types = converter.main_fuel_types
            power_capacity = converter.power_capacity.get()

            for fuel_type in main_fuel_types:

                if fuel_type in fuel_type_power:

                    fuel_type_power[fuel_type] += power_capacity

                else:

                    fuel_type_power[fuel_type] = power_capacity

        # reverse the list
        power_capacities = unique_list(fuel_type_power.values())
        power_fuel_type = {}

        for power in power_capacities:
            power_fuel_type[power] = [key for key, value in fuel_type_power.items() if value == power]

        # find the fuel types with the highest power
        max_power = max(power_capacities)

        if len(power_fuel_type[max_power]) > 1:

            # if multiple fuel types with same power
            # base the primary type on the tank size
            tanks = self.tanks
            fuel_type_size = {fuel_type: tank.size.get() for tank in tanks for fuel_type in tank.get_fuel_types()}

            # reduce the list of possibly fuel types
            usable_fuel_types = [fuel_type for fuel_type in power_fuel_type[max_power] if fuel_type in fuel_type_size]
            fuel_type = usable_fuel_types[0]

            for type_ in usable_fuel_types:

                if type_ not in fuel_type_size:
                    continue

                # notice that if multiple tanks have the same size
                # the first encountered fuel type is chosen
                if fuel_type_size[type_] > fuel_type_size[fuel_type]:
                    fuel_type = type_

            logger.info("{}: Has a power system with multiple main fuel types "
                        "({}) of equal power. {} was chosen as the primary."
                        .format(self,
                                ', '.join([FuelTypeID(f).name for f in power_fuel_type[max_power]]),
                                FuelTypeID(fuel_type).name))

        else:

            fuel_type = power_fuel_type[max_power][0]

        self.fuel_type = fuel_type

    def set_fleet_assignment(self, fleet_name):
        if self.fleet_assignment is not None:
            raise ValueError("Fleet(\"{}\"): {} is already assigned to a different fleet, Fleet(\"{}\")."
                             .format(fleet_name, self, self.fleet_assignment))

        self.fleet_assignment = fleet_name

    def is_assigned_to_fleet(self):
        return self.fleet_assignment is not None
