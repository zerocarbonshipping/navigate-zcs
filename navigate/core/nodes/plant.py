# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Plant node, a fuel production plant type a producer builds."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import Scalar, as_scalar, assign_value, command_assignment_to_dict
from navigate.core.expectations import PlantExpectation
from navigate.core.node import Node
from navigate.core.node_type import (
    FORECAST,
    FUEL,
    PLANT,
    PROCESS,
    REGION,
    SOURCE,
    TRANSPORT,
    VARIABLE,
)
from navigate.core.profiles import PlantProfile

if TYPE_CHECKING:
    from navigate.core.expression import Expression
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.input_kinds import ForecastInput
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.process import Process
    from navigate.core.nodes.region import Region
    from navigate.core.nodes.source import Source
    from navigate.core.nodes.transport import Transport
    from navigate.util import FloatArray


class Plant(Node):
    """A plant type: its fuel, process, region, source, capacity and transport."""

    def __init__(self, name: str) -> None:
        super().__init__(name, PLANT)

        # external variables -----------------------------------------------------------
        self.fuel: Fuel | Expression
        self.process: Process | Expression
        self.region: Region | Expression
        self.source: Source | Expression

        self.capacity: ForecastInput
        self.uptime: ForecastInput = Scalar(1.0)
        self.lifetime: ForecastInput = Scalar(30.0)
        self.lead_time: ForecastInput = Scalar(1.0)

        self.cost_of_capital: ForecastInput = Scalar(0.0)

        self.feed_transport: dict[str, Transport | Expression | None] = {}
        self.feed_distance: dict[str, ForecastInput | None] = {}

        self.fuel_transport: dict[str, Transport | Expression | None] = {}
        self.fuel_distance: dict[str, ForecastInput | None] = {}

        # internal variables -----------------------------------------------------------
        self.expectation: PlantExpectation = PlantExpectation()
        self.profile: PlantProfile = PlantProfile()

        # cross-check variables
        self.producer_assignment: str | None = None

    # external methods (DSL attributes) ------------------------------------------------
    def set_fuel(self, fuel: Fuel) -> None:
        """
        Set the fuel which is produced by the plant.

        Examples
        --------
        - Fuel("name")

        Parameters
        ----------
        fuel
            A Fuel node.
        """
        self.fuel = assign_value(fuel, scalar=False, type_=FUEL)

    def set_process(self, process: Process) -> None:
        """
        Set the production process used by the plant.

        Examples
        --------
        - Process("name")

        Parameters
        ----------
        process
            A Process node.
        """
        self.process = assign_value(process, scalar=False, type_=PROCESS)

    def set_region(self, region: Region) -> None:
        """
        Set the region in which the plant is built.

        Examples
        --------
        - Region("name")

        Parameters
        ----------
        region
            A Region node.
        """
        self.region = assign_value(region, scalar=False, type_=REGION)

    def set_source(self, source: Source) -> None:
        """
        Set the energy source which is to generate power for the plant.

        Examples
        --------
        - Source("name")

        Parameters
        ----------
        source
            A Source node.
        """
        self.source = assign_value(source, scalar=False, type_=SOURCE)

    def set_capacity(self, capacity: float | ForecastInput) -> None:
        """
        Set the production capacity of the plant in tons/day.

        Examples
        --------
        - 3000
        - Forecast("name")

        Parameters
        ----------
        capacity
            Production capacity of the plant in tons/day.
        """
        self.capacity = assign_value(
            as_scalar(capacity),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    def set_uptime(self, uptime: float | ForecastInput) -> None:
        """
        Set the production uptime of the plant in time/time.

        Examples
        --------
        - 0.95
        - Forecast("name")

        Parameters
        ----------
        uptime
            Production uptime of the plant in time/time.
        """
        self.uptime = assign_value(
            as_scalar(uptime),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            upper=1.0,
            inclusive_lower=False,
        )

    def set_lifetime(self, lifetime: float | ForecastInput) -> None:
        """
        Set the lifetime of the plant in years.

        The plant is decommissioned when it surpasses its lifetime.

        Examples
        --------
        - 30

        Parameters
        ----------
        lifetime
            Lifetime of the plant in years.
        """
        self.lifetime = assign_value(
            as_scalar(lifetime),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    def set_lead_time(self, lead_time: float | ForecastInput) -> None:
        """
        Set the planning to production lead time of the plant in years.

        Examples
        --------
        - 4
        - Forecast("name")

        Parameters
        ----------
        lead_time
            Construction lead time of the plant in years.
        """
        self.lead_time = assign_value(
            as_scalar(lead_time), type_=(FORECAST, VARIABLE), lower=0.0
        )

    def set_cost_of_capital(self, cost_of_capital: float | ForecastInput) -> None:
        """
        Set the cost of capital used in calculating the finance costs of the plant.

        Also used as the discount rate for levelized cost calculations for investment
        decisions.

        Examples
        --------
        - 0.1
        - Forecast("name")

        Parameters
        ----------
        cost_of_capital
            Cost of capital.
        """
        self.cost_of_capital = assign_value(
            as_scalar(cost_of_capital), type_=(FORECAST, VARIABLE), lower=0.0
        )

    # external methods (DSL commands) --------------------------------------------------
    def set_feed_transport(self, feed_name: str, value: Transport) -> None:
        """
        Set the transport mode for delivering feedstock or process output to the plant.

        Examples
        --------
        - "feedstock_name", Transport("name")
        - "process_name", Transport("name")

        Parameters
        ----------
        feed_name
            The name of a feedstock or process.
        value
            The transport mode used to transport the feedstock or process output.
        """
        command_assignment_to_dict(
            feed_name, as_scalar(value), self.feed_transport, type_=TRANSPORT
        )

    def set_feed_distance(self, feed_name: str, value: float | ForecastInput) -> None:
        """
        Set the feedstock or process transport distance to the plant, nautical miles.

        Examples
        --------
        - "feedstock_name", 100
        - "process_name", 100
        - "process_name", Forecast("name")

        Parameters
        ----------
        feed_name
            The name of a feedstock or process.
        value
            The distance of transport in nautical miles.
        """
        command_assignment_to_dict(
            feed_name,
            as_scalar(value),
            self.feed_distance,
            type_=(FORECAST, VARIABLE),
            lower=0.0,
        )

    def set_fuel_transport(self, port_name: str, value: Transport) -> None:
        """
        Set the transport mode used for delivering the produced fuel to a given port.

        The cost and WTT emissions of the delivery are given by the transport rates of
        the plant's region, see `Region.set_transport_cost` and
        `Region.set_transport_wtt`.

        Examples
        --------
        - "port_name", Transport("name")

        Parameters
        ----------
        port_name
            The name of a port.
        value
            The transport mode used to deliver the produced fuel to the port.
        """
        command_assignment_to_dict(
            port_name, as_scalar(value), self.fuel_transport, type_=TRANSPORT
        )

    def set_fuel_distance(self, port_name: str, value: float | ForecastInput) -> None:
        """
        Set the distance the produced fuel is transported to a port, in nautical miles.

        Examples
        --------
        - "port_name", 100
        - "port_name", Forecast("name")

        Parameters
        ----------
        port_name
            The name of a port.
        value
            The distance of transport in nautical miles.
        """
        command_assignment_to_dict(
            port_name,
            as_scalar(value),
            self.fuel_distance,
            type_=(FORECAST, VARIABLE),
            lower=0.0,
        )

    # internal methods -----------------------------------------------------------------
    def apply_command_defaults(self) -> None:
        self._default_distances(self.feed_transport, self.feed_distance)
        self._default_distances(self.fuel_transport, self.fuel_distance)

    def check_consistency(self) -> None:

        if self.fuel.liquid_market:
            raise ValueError(
                f"{self}: Unable to assign {self.fuel} to attribute 'Fuel' as it"
                " belongs to a liquid market ('LiquidMarket = TRUE')."
            )

        self._require_transport_where_distance(self.feed_transport, self.feed_distance)
        self._require_transport_where_distance(self.fuel_transport, self.fuel_distance)

    @staticmethod
    def _default_distances(
        transports: dict[str, Transport | Expression | None],
        distances: dict[str, ForecastInput | None],
    ) -> None:
        """Give a transported route with no distance assigned a distance of zero."""
        for name, transport in transports.items():
            if (transport is not None) and (distances[name] is None):
                distances[name] = Scalar(0.0)

    def _require_transport_where_distance(
        self,
        transports: dict[str, Transport | Expression | None],
        distances: dict[str, ForecastInput | None],
    ) -> None:
        """Raise where a distance is assigned but no transport carries it."""
        for name, transport in transports.items():
            if (transport is None) and (distances[name] is not None):
                raise ValueError(
                    f"{self}: Unable to assign a transport distance to '{name}' as no"
                    " transport is assigned."
                )

    def initialize_dependencies(
        self,
        feedstocks: dict[str, Feedstock],
        ports: dict[str, Port],
        processes: dict[str, Process],
    ) -> None:
        """
        Initialize dependent dictionaries to allow wildcarding during command calls.

        Parameters
        ----------
        feedstocks
            All feedstocks in the simulation.
        ports
            All ports in the simulation.
        processes
            All processes in the simulation.
        """
        for feedstock_name in feedstocks:
            self.feed_transport.setdefault(feedstock_name, None)
            self.feed_distance.setdefault(feedstock_name, None)

        for process_name in processes:
            self.feed_transport.setdefault(process_name, None)
            self.feed_distance.setdefault(process_name, None)

        for port_name in ports:
            self.fuel_transport.setdefault(port_name, None)
            self.fuel_distance.setdefault(port_name, None)

    def initialize_expectation(
        self,
        length: int,
        emissions: dict[str, Emission],
        feedstocks: dict[str, Feedstock],
        ports: dict[str, Port],
        processes: dict[str, Process],
    ) -> None:

        self.expectation.initialize(length, emissions, feedstocks, ports, processes)

    def initialize_profile(
        self,
        timeline: FloatArray,
        emissions: dict[str, Emission],
        fuels: dict[str, Fuel],
        emissions_lifetime: float,
    ) -> None:

        self.profile.initialize(
            timeline, emissions, fuels, self.fuel.name, emissions_lifetime
        )

    def set_producer_assignment(self, producer_name: str) -> None:
        """Record the producer building this plant, raising if another already does."""
        if self.producer_assignment is not None:
            raise ValueError(
                f'Producer("{producer_name}"): {self} is already assigned to a'
                f' different producer, Producer("{self.producer_assignment}").'
            )

        self.producer_assignment = producer_name
