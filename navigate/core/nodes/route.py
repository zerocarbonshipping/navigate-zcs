# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Route node, the ports, legs and sailing conditions a vessel trades on."""

from __future__ import annotations

import itertools
import logging
from typing import TYPE_CHECKING

from navigate.core import (
    Scalar,
    as_list,
    as_scalar,
    assign_fraction_list,
    assign_id,
    assign_list,
    assign_reference_list,
    assign_value,
    write_matching_key_pairs,
)
from navigate.core.enum_ import RouteTypeID
from navigate.core.node import Node
from navigate.core.node_type import FORECAST, PORT, ROUTE, VARIABLE
from navigate.exceptions import UnassignedAttributeError
from navigate.util import unique_list

if TYPE_CHECKING:
    from navigate.core.expression import Expression
    from navigate.core.nodes.port import Port
    from navigate.core.types_ import (
        ForecastArgument,
        ForecastInput,
        NumberInput,
        ScalarArgument,
        ScalarInput,
    )

logger = logging.getLogger(__name__)


class Route(Node):
    """The ports a vessel calls at and the legs and sailing conditions between them."""

    def __init__(self, name: str) -> None:
        super().__init__(name, ROUTE)

        # external variables -----------------------------------------------------------
        self.route_type: RouteTypeID
        self.ports: list[Port]

        # time at sea/in port
        self.port_durations: list[ForecastInput] = []
        self.time_at_sea: ForecastInput | None = None
        self.port_calls: list[ForecastInput] = []

        # legs and sailing conditions
        self.speeds: list[ForecastInput]
        self.utilizations: list[ForecastInput] = []
        self.distances: list[Scalar | Expression] = []
        self.condition_distribution: list[float] = []

        # regulation
        self.voyage_distribution: dict[tuple[str, str], ScalarInput] = {}

    # external methods (DSL attributes) ------------------------------------------------
    def set_route_type(self, route_type: str) -> None:
        """Set the route type."""
        self.route_type = assign_id(route_type, RouteTypeID)

    def set_ports(self, ports: Port | list[Port]) -> None:
        """Set the list of ports available for bunkering on the route."""
        self.ports = assign_reference_list(ports, PORT, min_length=1)

    def set_port_durations(
        self, port_durations: ForecastArgument | list[ForecastArgument]
    ) -> None:
        """Set the duration of each port call of the trip."""
        entries: list[ForecastArgument] = as_list(port_durations)
        self.port_durations = assign_list(
            [as_scalar(entry) for entry in entries],
            min_length=1,
            type_=(FORECAST, VARIABLE),
            lower=0.0,
        )

    def set_time_at_sea(self, time_at_sea: ForecastArgument) -> None:
        """Set the fraction of time spent at sea."""
        self.time_at_sea = assign_value(
            as_scalar(time_at_sea),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            upper=1.0,
            inclusive_lower=False,
        )

    def set_port_calls(
        self, port_calls: ForecastArgument | list[ForecastArgument]
    ) -> None:
        """Set the number of port calls per port over the reference duration."""
        entries: list[ForecastArgument] = as_list(port_calls)
        self.port_calls = assign_list(
            [as_scalar(entry) for entry in entries],
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    def set_distances(self, distances: NumberInput | list[NumberInput]) -> None:
        """Set the distance of each leg of a ROUND_TRIP."""
        entries: list[NumberInput] = as_list(distances)
        self.distances = assign_list(
            [as_scalar(entry) for entry in entries], lower=0.0, inclusive_lower=False
        )

    def set_condition_distribution(self, condition_distribution: list[float]) -> None:
        """Set the share of a leg's sea time spent in each sailing condition."""
        self.condition_distribution, rescaled = assign_fraction_list(
            condition_distribution
        )

        if rescaled:
            logger.warning(
                "%s: 'ConditionDistribution' is rescaled proportionally to sum to 1.",
                self,
            )

    def set_speeds(self, speeds: ForecastArgument | list[ForecastArgument]) -> None:
        """Set the speed per ROUND_TRIP leg or per REGIONAL_TRIP condition."""
        entries: list[ForecastArgument] = as_list(speeds)
        self.speeds = assign_list(
            [as_scalar(entry) for entry in entries],
            min_length=1,
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    def set_utilizations(
        self, utilizations: ForecastArgument | list[ForecastArgument]
    ) -> None:
        """Set the utilization per ROUND_TRIP leg or per REGIONAL_TRIP condition."""
        entries: list[ForecastArgument] = as_list(utilizations)
        self.utilizations = assign_list(
            [as_scalar(entry) for entry in entries],
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            upper=1.0,
        )

    # external methods (DSL commands) --------------------------------------------------
    def set_voyage_distribution(
        self, port_name_from: str, port_name_to: str, fraction: ScalarArgument
    ) -> None:
        """Set the share of the sea miles sailed from one port to another."""
        write_matching_key_pairs(
            (port_name_from, port_name_to),
            assign_value(as_scalar(fraction), type_=VARIABLE, lower=0.0, upper=1.0),
            self.voyage_distribution,
        )

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:

        # each route type reads a different set of the leg and port attributes
        if self.route_type == RouteTypeID.ROUND_TRIP:
            if not self.port_durations:
                raise UnassignedAttributeError(str(self), "PortDurations")

            if not self.distances:
                raise UnassignedAttributeError(str(self), "Distances")

        elif self.route_type == RouteTypeID.REGIONAL_TRIP:
            if self.time_at_sea is None:
                raise UnassignedAttributeError(str(self), "TimeAtSea")

    def apply_defaults(self) -> None:

        if not self.utilizations:
            self.utilizations = [Scalar(1.0) for _ in self.speeds]

        if (self.route_type == RouteTypeID.REGIONAL_TRIP) and not self.port_calls:
            self.port_calls = [Scalar(1.0) for _ in self.ports]

    def check_consistency(self) -> None:

        if len(self.speeds) != len(self.utilizations):
            raise ValueError(
                f"{self}: The length of 'Speeds' ({len(self.speeds)}) and "
                f"'Utilizations' ({len(self.utilizations)}) must correspond."
            )

        if self.route_type == RouteTypeID.ROUND_TRIP:
            self._check_round_trip()

        elif self.route_type == RouteTypeID.REGIONAL_TRIP:
            self._check_regional_trip()

    def _check_round_trip(self) -> None:
        """Check what a ROUND_TRIP reads, and warn about what it ignores."""
        if len(self.distances) != len(self.speeds):
            raise ValueError(
                f"{self}: The length of 'Distances' ({len(self.distances)}) and"
                f" Speeds ({len(self.speeds)}) must correspond."
            )

        if len(self.ports) < 2:
            raise ValueError(
                f"{self}: Must have a minimum of 2 ports assigned for a ROUND_TRIP,"
                f" only {len(self.ports)} were given."
            )

        # based on previous checks, distances is representative for all leg related
        # lists
        if len(self.distances) != len(self.ports):
            raise ValueError(
                f"{self}: The length of 'Distances' ({len(self.distances)}) and"
                f" 'Ports' ({len(self.ports)}) must correspond for a ROUND_TRIP."
            )

        if len(self.ports) != len(self.port_durations):
            raise ValueError(
                f"{self}: The length of 'Ports' ({len(self.ports)}) and"
                f" 'PortDurations' ({len(self.port_durations)}) must correspond."
            )

        # the same port may not be placed in sequence
        for p in range(len(self.ports) - 1):
            if self.ports[p] is self.ports[p + 1]:
                raise ValueError(
                    f"{self}: Unable to place {self.ports[p]} after itself in the"
                    " sequence."
                )

        # the set is assumed periodical so check first/last are not in sequence
        if self.ports[0] is self.ports[-1]:
            raise ValueError(
                f"{self}: The set of ports is assumed to wrap around for a"
                f" 'ROUND_TRIP', so {self.ports[0]} cannot be"
                " placed both first and last."
            )

        if self.time_at_sea is not None:
            logger.warning(
                "%s: 'TimeAtSea' is assigned but is unused for a ROUND_TRIP.", self
            )

        if self.port_calls:
            logger.warning(
                "%s: 'PortCalls' is assigned but is unused for a ROUND_TRIP.", self
            )

        if self.condition_distribution:
            logger.warning(
                "%s: 'ConditionDistribution' is assigned but is unused for a "
                "ROUND_TRIP.",
                self,
            )

    def _check_regional_trip(self) -> None:
        """Check what a REGIONAL_TRIP reads, and warn about what it ignores."""
        if len(self.condition_distribution) != len(self.speeds):
            raise ValueError(
                f"{self}: The length of 'ConditionDistribution'"
                f" ({len(self.condition_distribution)}) and 'Speeds'"
                f" ({len(self.speeds)}) must correspond."
            )

        # all ports must be unique
        if len(self.ports) > len(unique_list(self.ports)):
            raise ValueError(f"{self}: All ports on a 'REGIONAL_TRIP' must be unique.")

        if len(self.ports) != len(self.port_calls):
            raise ValueError(
                f"{self}: The length of 'Ports' ({len(self.ports)}) and 'PortCalls'"
                f" ({len(self.port_calls)}) must correspond."
            )

        if self.distances:
            logger.warning(
                "%s: 'Distances' is assigned but is unused for a REGIONAL_TRIP.",
                self,
            )

        if self.port_durations:
            logger.warning(
                "%s: 'PortDurations' is assigned but is unused for a REGIONAL_TRIP.",
                self,
            )

    def initialize_dependencies(self) -> None:
        """Initialize dependent dictionaries so command calls can use wildcards."""
        names = [port.name for port in self.ports]
        for key in itertools.product(names, names):
            self.voyage_distribution.setdefault(key, Scalar(0.0))

    def get_number_of_ports(self) -> int:
        return len(self.ports)

    def get_legs(self) -> tuple[tuple[int, int], ...]:
        """
        Return the (origin, destination) stop indices of each leg, in canonical order.

        Every per-leg value on the route is ordered as this tuple.

        Returns
        -------
        tuple[tuple[int, int], ...]
            Consecutive stops, the last leg returning to the first, for a
            ROUND_TRIP; every ordered pair of ports, origin-major, for a
            REGIONAL_TRIP.
        """
        n_ports = self.get_number_of_ports()

        if self.route_type == RouteTypeID.ROUND_TRIP:
            return tuple((i, (i + 1) % n_ports) for i in range(n_ports))

        return tuple((i, j) for i in range(n_ports) for j in range(n_ports))

    def get_conditions(self) -> tuple[tuple[int, int], ...]:
        """
        Return the leg and the speed entry of each sailing condition, leg-major.

        Every per-condition value on the route is ordered as this tuple. The entry
        indexes 'Speeds' and 'Utilizations', and 'ConditionDistribution' on a
        REGIONAL_TRIP.

        Returns
        -------
        tuple[tuple[int, int], ...]
            One condition per leg, its entry the leg's, for a ROUND_TRIP; every
            entry on every leg for a REGIONAL_TRIP, whose sailing conditions are
            route-wide.
        """
        n_legs = len(self.get_legs())

        if self.route_type == RouteTypeID.ROUND_TRIP:
            return tuple((leg, leg) for leg in range(n_legs))

        entries = range(len(self.speeds))
        return tuple((leg, entry) for leg in range(n_legs) for entry in entries)

    def get_tank_stops(self) -> tuple[int, ...]:
        """
        Return the stops at which the bunkering tracks the fuel held in the tank.

        Returns
        -------
        tuple[int, ...]
            Every stop of a ROUND_TRIP; none of a REGIONAL_TRIP, whose stops follow
            no sequence to carry fuel along.
        """
        if self.route_type == RouteTypeID.ROUND_TRIP:
            return tuple(range(self.get_number_of_ports()))

        return ()

    def get_tank_legs(self) -> tuple[tuple[int, int], ...]:
        """
        Return the legs that carry the fuel tank from one tank stop to the next.

        Returns
        -------
        tuple[tuple[int, int], ...]
            The legs of a ROUND_TRIP except the one returning to the first stop;
            none of a REGIONAL_TRIP.
        """
        if self.route_type == RouteTypeID.ROUND_TRIP:
            return tuple((i, i + 1) for i in range(self.get_number_of_ports() - 1))

        return ()
