# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core import Scalar, as_scalar, assign_value, command_assignment_to_dict
from navigate.core.expectations import PlantExpectation
from navigate.core.node import Node
from navigate.core.node_type import FORECAST, FUEL, PLANT, PROCESS, REGION, SOURCE, TRANSPORT, VARIABLE
from navigate.core.profiles import PlantProfile
from navigate.exceptions import no_value_assigned_error

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.process import Process


class Plant(Node):
    def __init__(self, name):
        super().__init__(name)

        self.type = PLANT

        self.fuel = None       # Fuel, the fuel being produced by the plant
        self.process = None    # Process, the top-level production process used at the plant
        self.region = None     # Region, region in which fuel is being produced.
        self.source = None     # Source, source of energy to power the process.

        self.capacity = None   # float, production of fuel in tons/day
        self.uptime = None     # float, uptime of the plant in time/time
        self.lifetime = None   # float, lifetime of the plant before decommissioning, years
        self.lead_time = None  # float, time from planning to production, years

        self.cost_of_capital = None  # float, cost of capital and discount rate

        self.feed_transport = {}  # dict[feedstock_name: Transport], transport mode for feedstock
        self.feed_distance = {}   # dict[feedstock_name: float], distance transported, nautical miles

        # cross-check properties
        self.producer_assignment = None  # name of producer plant is assigned to

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_fuel(self, fuel):
        """
        Set the fuel which is produced by the plant.

        Examples
        --------
        - Fuel("name")

        Parameters
        ----------
        fuel : NodeReference
            A Fuel node.
        """

        self.fuel = assign_value(fuel, scalar=False, type_=FUEL)

    def set_process(self, process):
        """
        Set the production process used by the plant.

        Examples
        --------
        - Process("name")

        Parameters
        ----------
        process : NodeReference
            A Process node.
        """

        self.process = assign_value(process, scalar=False, type_=PROCESS)

    def set_region(self, region):
        """
        Set the region in which the plant is built.

        Examples
        --------
        - Region("name")

        Parameters
        ----------
        region : NodeReference
            A Region node.
        """

        self.region = assign_value(region, scalar=False, type_=REGION)

    def set_source(self, source):
        """
        Set the energy source which is to generate power for the plant.

        Examples
        --------
        - Source("name")

        Parameters
        ----------
        source : NodeReference
            A Source node.
        """

        self.source = assign_value(source, scalar=False, type_=SOURCE)

    def set_capacity(self, capacity):
        """
        Set the production capacity of the plant in tons/day.

        Examples
        --------
        - 3000
        - Forecast("name")

        Parameters
        ----------
        capacity : float | NodeReference
            Production capacity of the plant in tons/day.
        """

        self.capacity = assign_value(as_scalar(capacity), type_=(FORECAST, VARIABLE),
                                     lower=0., inclusive_lower=False)

    def set_uptime(self, uptime):
        """
        Set the production uptime of the plant in time/time.

        Examples
        --------
        - 0.95
        - Forecast("name")

        Parameters
        ----------
        uptime : float | NodeReference
            Production uptime of the plant in time/time.
        """

        self.uptime = assign_value(as_scalar(uptime), type_=(FORECAST, VARIABLE),
                                   lower=0., upper=1., inclusive_lower=False)

    def set_lifetime(self, lifetime):
        """
        Set the lifetime of the plant in years.

        The plant is decommissioned when it surpasses its lifetime.

        Examples
        --------
        - 30

        Parameters
        ----------
        lifetime : float | NodeReference
            Lifetime of the plant in years.
        """

        self.lifetime = assign_value(as_scalar(lifetime), type_=(FORECAST, VARIABLE),
                                     lower=0., inclusive_lower=False)

    def set_lead_time(self, lead_time):
        """
        Set the planning to production lead time of the plant in years.

        Examples
        --------
        - 4
        - Forecast("name")

        Parameters
        ----------
        lead_time : float | NodeReference
            Construction lead time of the plant in years.
        """

        self.lead_time = assign_value(as_scalar(lead_time), type_=(FORECAST, VARIABLE), lower=0.)

    def set_cost_of_capital(self, cost_of_capital):
        """
        Set the cost of capital used in calculating the finance costs of the plant.

        Also used as the discount rate for levelized cost calculations for investment decisions.

        Examples
        --------
        - 0.1
        - Forecast("name")

        Parameters
        ----------
        cost_of_capital : float | NodeReference
            Cost of capital.
        """

        self.cost_of_capital = assign_value(as_scalar(cost_of_capital), type_=(FORECAST, VARIABLE), lower=0.)

    # external commands called in the input deck -----------------------------------------------------------------------
    def set_feed_transport(self, feed_name, value):
        """
        Set the transport mode used for transporting a specific feedstock or process output the plant.

        Examples
        --------
        - "feedstock_name", Transport("name")
        - "process_name", Transport("name")

        Parameters
        ----------
        feed_name : str
            The name of a feedstock or process.
        value : NodeReference
            The transport mode used to transport the feedstock or process output.
        """

        command_assignment_to_dict(feed_name, value, self.feed_transport, type_=TRANSPORT)

    def set_feed_distance(self, feed_name, value):
        """
        Set the distance a given feedstock or process output is transported to the plant in nautical miles.

        Examples
        --------
        - "feedstock_name", 100
        - "process_name", 100
        - "process_name", Forecast("name")

        Parameters
        ----------
        feed_name : str
            The name of a feedstock or process.
        value : float | NodeReference
            The distance of transport in nautical miles.
        """

        command_assignment_to_dict(feed_name,
                                   value,
                                   self.feed_distance,
                                   type_=(FORECAST, VARIABLE),
                                   lower=0.)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):

        if self.fuel is None:
            no_value_assigned_error(self, 'Fuel')

        if self.process is None:
            no_value_assigned_error(self, 'Process')

        if self.region is None:
            no_value_assigned_error(self, 'Region')

        if self.source is None:
            no_value_assigned_error(self, 'Source')

        if self.capacity is None:
            no_value_assigned_error(self, 'Capacity')

        if self.fuel.belongs_to_liquid_market():
            raise ValueError("{}: Unable to assign {} to attribute 'Fuel' as it is assigned to the list of liquid"
                             " markets in BunkerLogistics.".format(self, self.fuel))

        if self.uptime is None:
            self.uptime = Scalar(1)

        if self.lifetime is None:
            self.lifetime = Scalar(30)

        if self.lead_time is None:
            self.lead_time = Scalar(1)

        if self.cost_of_capital is None:
            self.cost_of_capital = Scalar(0)

        for feed_name in self.feed_transport:

            transport = self.feed_transport[feed_name]
            distance = self.feed_distance[feed_name]

            if (transport is None) and (distance is not None):
                raise ValueError("{}: Unable to assign a transport distance to '{}' as no transport is assigned."
                                 .format(self, feed_name))

            elif (transport is not None) and (distance is None):
                self.feed_distance[feed_name] = Scalar(0.)

    def initialize_dependencies(self, feedstocks, processes):
        """
        Initialize all dependent dictionaries.

        Parameters
        ----------
        feedstocks : dict[str, Feedstock]
            All feedstocks in the simulation.
        processes : dict[str, Process]
            All processes in the simulation.
        """

        for feedstock_name in feedstocks:
            self.feed_transport.setdefault(feedstock_name, None)
            self.feed_distance.setdefault(feedstock_name, None)

        for process_name in processes:
            self.feed_transport.setdefault(process_name, None)
            self.feed_distance.setdefault(process_name, None)

    def initialize_expectation(self, length: int, emissions: dict[str, Emission],
                               feedstocks: dict[str, Feedstock], ports: dict[str, Port],
                               processes: dict[str, Process]) -> None:

        self.expectation = PlantExpectation()
        self.expectation.initialize(length, emissions, feedstocks, ports, processes)

    def initialize_profile(self, timeline: np.ndarray, emissions: dict[str, Emission],
                           emissions_lifetime: float) -> None:

        self.profile = PlantProfile()
        self.profile.initialize(timeline, self.fuel, emissions, emissions_lifetime)

    def set_producer_assignment(self, producer_name):
        if self.producer_assignment is not None:
            raise ValueError("Producer(\"{}\"): {} is already assigned to a different producer, Producer(\"{}\")."
                             .format(producer_name, self, self.producer_assignment))

        self.producer_assignment = producer_name

    def is_assigned_to_producer(self):
        return self.producer_assignment is not None
