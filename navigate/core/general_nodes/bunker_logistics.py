# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core import Scalar, as_list, assign_list, command_assignment_to_dict, command_assignment_to_tuple_dict
from navigate.core.general_nodes._general_node import _GeneralNode
from navigate.core.node_type import FORECAST, FUEL, VARIABLE


class BunkerLogistics(_GeneralNode):
    def __init__(self):
        super().__init__()

        self.liquid_market_fuels = []  # list[Fuel], list of fuels which belong to a liquid market

        self.distances = {}        # dict[(region_name, port_name): float], distance between regions and ports
        self.transport_costs = {}  # dict[fuel_name: float], cost of transporting fuel
        self.transport_WTT = {}    # dict[(fuel_name, emission_name): float], WTT from transporting fuel

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_liquid_market_fuels(self, fuels: list):
        """
        Set the list of fuels that exists belong to a liquid market.

        Fuels which belong to a liquid market cannot be modelled bottom-up via Plant and Producer nodes but require
        manual assignment of supply, price, and WTT emissions at Port level.

        Examples
        --------
        - Fuel("name")
        - [Fuel("name1"), Fuel("name2")]

        Parameters
        ----------
        fuels
            The list of fuels that belong to a liquid market.
        """

        self.liquid_market_fuels = assign_list(as_list(fuels), unique=True, scalar=False, type_=FUEL)

    # external commands called in the input deck -----------------------------------------------------------------------
    def set_distance(self, region_name: str, port_name: str, distance: float):
        """
        Set the distance between a region and a port in nautical miles.

        Examples
        --------
        - "region_name", "port_name", 1000

        Parameters
        ----------
        region_name
            The name of a region.
        port_name
            The name of a port.
        distance
            The distances between a region and a port in nautical miles.
        """

        command_assignment_to_tuple_dict((region_name, port_name), distance, self.distances, lower=0.)

    def set_transport_cost(self, fuel_name: str, transport_cost: float):
        """
        Set cost of transporting a fuel in ton USD/ton/nautical-mile.

        Examples
        --------
        - "fuel_name", 1.5
        - "fuel_name", Forecast("name")

        Parameters
        ----------
        fuel_name
            The name of a fuel.
        transport_cost
            The cost of transporting a fuel in USD/ton/nautical-mile.
        """

        command_assignment_to_dict(fuel_name, transport_cost, self.transport_costs, type_=(FORECAST, VARIABLE), lower=0.)

    def set_transport_wtt(self, fuel_name: str, emission_name: str, transport_WTT: float):
        """
        Set the WTT emissions from transporting a fuel in ton emissions/ton fuel/nautical-mile.

        Examples
        --------
        - "fuel_name", "emission_name", 1.5
        - "fuel_name", "emission_name", Forecast("name")

        Parameters
        ----------
        fuel_name
            The name of a fuel.
        emission_name
            The name of an emission.
        transport_WTT
            The WTT emissions from transporting a fuel in ton emissions/ton fuel/nautical-mile.
        """

        command_assignment_to_tuple_dict((fuel_name, emission_name), transport_WTT, self.transport_WTT,
                                         type_=(FORECAST, VARIABLE), lower=0.)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):

        for fuel in self.liquid_market_fuels:

            fuel.liquid_market = True

        for (region_name, port_name) in self.distances:

            if self.distances[(region_name, port_name)] is None:

                self.distances[(region_name, port_name)] = Scalar(0.)

        for fuel_name in self.transport_costs:

            if self.transport_costs[fuel_name] is None:

                self.transport_costs[fuel_name] = Scalar(0.)

        for (fuel_name, emission_name) in self.transport_WTT:

            if self.transport_WTT[(fuel_name, emission_name)] is None:

                self.transport_WTT[(fuel_name, emission_name)] = Scalar(0.)

    def initialize_dependencies(self, emissions, fuels, ports, regions):
        """
        Initialize dependent dictionaries to allow wildcarding during command calls.

        Parameters
        ----------
        emissions
            All emissions in the simulation.
        fuels
            All fuels in the simulation.
        ports
            All ports in the simulation.
        regions
            All regions in the simulation.
        """

        for region_name in regions:

            for port_name in ports:

                self.distances.setdefault((region_name, port_name), None)

        for fuel_name in fuels:

            self.transport_costs.setdefault(fuel_name, None)

            for emission_name in emissions:

                self.transport_WTT.setdefault((fuel_name, emission_name), None)
