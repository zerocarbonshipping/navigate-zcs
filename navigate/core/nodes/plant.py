# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Plant node, a fuel production plant type a producer builds."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    Scalar,
    as_scalar,
    assign_reference,
    assign_value,
    write_matching_keys,
)
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
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.process import Process
    from navigate.core.nodes.region import Region
    from navigate.core.nodes.source import Source
    from navigate.core.nodes.transport import Transport
    from navigate.core.types_ import ForecastArgument, ForecastInput
    from navigate.util import FloatArray


class Plant(Node):
    """A plant type: its fuel, process, region, source, capacity and transport."""

    def __init__(self, name: str) -> None:
        super().__init__(name, PLANT)

        # external variables -----------------------------------------------------------
        self.fuel: Fuel
        self.process: Process
        self.region: Region
        self.source: Source

        self.capacity: ForecastInput
        self.uptime: ForecastInput = Scalar(1.0)
        self.lifetime: ForecastInput = Scalar(30.0)
        self.lead_time: ForecastInput = Scalar(1.0)

        self.cost_of_capital: ForecastInput = Scalar(0.0)

        self.feed_transport: dict[str, Transport | None] = {}
        self.feed_distance: dict[str, ForecastInput | None] = {}

        self.fuel_transport: dict[str, Transport | None] = {}
        self.fuel_distance: dict[str, ForecastInput | None] = {}

        # internal variables -----------------------------------------------------------
        self.feed_deliveries: dict[str, tuple[Transport, ForecastInput] | None] = {}
        self.fuel_deliveries: dict[str, tuple[Transport, ForecastInput] | None] = {}

        self.expectation: PlantExpectation = PlantExpectation()
        self.profile: PlantProfile = PlantProfile()

        # cross-check variables
        self.producer_assignment: str | None = None

    # external methods (DSL attributes) ------------------------------------------------
    def set_fuel(self, fuel: Fuel) -> None:
        """Set the fuel produced by the plant."""
        self.fuel = assign_reference(fuel, FUEL)

    def set_process(self, process: Process) -> None:
        """Set the production process used by the plant."""
        self.process = assign_reference(process, PROCESS)

    def set_region(self, region: Region) -> None:
        """Set the region in which the plant is built."""
        self.region = assign_reference(region, REGION)

    def set_source(self, source: Source) -> None:
        """Set the energy source powering the plant."""
        self.source = assign_reference(source, SOURCE)

    def set_capacity(self, capacity: ForecastArgument) -> None:
        """Set the production capacity of the plant."""
        self.capacity = assign_value(
            as_scalar(capacity),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    def set_uptime(self, uptime: ForecastArgument) -> None:
        """Set the production uptime of the plant."""
        self.uptime = assign_value(
            as_scalar(uptime),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            upper=1.0,
            inclusive_lower=False,
        )

    def set_lifetime(self, lifetime: ForecastArgument) -> None:
        """Set the lifetime of the plant."""
        self.lifetime = assign_value(
            as_scalar(lifetime),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    def set_lead_time(self, lead_time: ForecastArgument) -> None:
        """Set the planning-to-production lead time of the plant."""
        self.lead_time = assign_value(
            as_scalar(lead_time), type_=(FORECAST, VARIABLE), lower=0.0
        )

    def set_cost_of_capital(self, cost_of_capital: ForecastArgument) -> None:
        """Set the cost of capital of the plant."""
        self.cost_of_capital = assign_value(
            as_scalar(cost_of_capital), type_=(FORECAST, VARIABLE), lower=0.0
        )

    # external methods (DSL commands) --------------------------------------------------
    def set_feed_transport(self, feed_name: str, value: Transport) -> None:
        """Set the transport mode delivering a feedstock or process output."""
        write_matching_keys(
            feed_name,
            assign_reference(value, TRANSPORT),
            self.feed_transport,
        )

    def set_feed_distance(self, feed_name: str, value: ForecastArgument) -> None:
        """Set the distance a feedstock or process output is transported."""
        write_matching_keys(
            feed_name,
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0),
            self.feed_distance,
        )

    def set_fuel_transport(self, port_name: str, value: Transport) -> None:
        """Set the transport mode delivering the produced fuel to a port."""
        write_matching_keys(
            port_name,
            assign_reference(value, TRANSPORT),
            self.fuel_transport,
        )

    def set_fuel_distance(self, port_name: str, value: ForecastArgument) -> None:
        """Set the distance the produced fuel is transported to a port."""
        write_matching_keys(
            port_name,
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0),
            self.fuel_distance,
        )

    # internal methods -----------------------------------------------------------------
    def apply_command_defaults(self) -> None:
        # the deliveries are the resolved form of the command dictionaries, so
        # they are rebuilt here, on every pass a command can have reassigned a
        # transport or a distance
        self.feed_deliveries = self._pair_deliveries(
            self.feed_transport, self.feed_distance
        )
        self.fuel_deliveries = self._pair_deliveries(
            self.fuel_transport, self.fuel_distance
        )

    def check_consistency(self) -> None:

        if self.fuel.liquid_market:
            raise ValueError(
                f"{self}: Unable to assign {self.fuel} to attribute 'Fuel' as it"
                " belongs to a liquid market ('LiquidMarket = TRUE')."
            )

        self._require_transport_where_distance(self.feed_transport, self.feed_distance)
        self._require_transport_where_distance(self.fuel_transport, self.fuel_distance)

    @staticmethod
    def _pair_deliveries(
        transports: dict[str, Transport | None],
        distances: dict[str, ForecastInput | None],
    ) -> dict[str, tuple[Transport, ForecastInput] | None]:
        """
        Pair each transport with its distance, zero where none is assigned.

        A name without a transport maps to None.
        """
        deliveries: dict[str, tuple[Transport, ForecastInput] | None] = {}
        for name, transport in transports.items():
            distance = distances[name]
            if transport is None:
                deliveries[name] = None
            elif distance is None:
                deliveries[name] = (transport, Scalar(0.0))
            else:
                deliveries[name] = (transport, distance)

        return deliveries

    def _require_transport_where_distance(
        self,
        transports: dict[str, Transport | None],
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
