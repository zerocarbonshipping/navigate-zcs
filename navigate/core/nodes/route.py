# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Route node, the ports, legs and sailing conditions a vessel trades on."""

from __future__ import annotations

from collections import Counter
from itertools import pairwise
from typing import TYPE_CHECKING

import numpy as np

from navigate.core import (
    SECTION_DEFINE,
    Expression,
    Scalar,
    as_scalar,
    assign_id,
    assign_reference_list,
    assign_value,
    deck_attribute,
    deck_command,
    write_matching_keys,
)
from navigate.core.assign import in_seeded_order
from navigate.core.enum_ import RouteTypeID
from navigate.core.node import Node
from navigate.core.node_type import CURVE, FORECAST, PORT, ROUTE, VARIABLE
from navigate.core.nodes.curve import Curve
from navigate.core.wrap import to_array
from navigate.exceptions import DeckInsufficientError, UnassignedAttributeError
from navigate.util import (
    ROUND_OFF,
    divide_nonzero,
    key_tuple_name,
    matching_keys,
    name_matches,
    unique_list,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from navigate.core.nodes.port import Port
    from navigate.core.types_ import (
        CurveArgument,
        CurveForecastArgument,
        CurveForecastInput,
        CurveInput,
        ForecastArgument,
        ForecastInput,
        NumberInput,
        ScalarArgument,
        ScalarInput,
    )
    from navigate.util.types_ import BoolArray, DateArray, FloatArray


class Route(Node):
    """A route: its ports, and the legs and sailing conditions between them."""

    type = ROUTE

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # external variables -----------------------------------------------------------
        self.route_type: RouteTypeID
        self.ports: list[Port]
        self.time_at_sea: ForecastInput | None = None

        # per leg, keyed by the names of the leg's origin and destination ports
        self.speeds: dict[tuple[str, str], CurveInput | None] = {}
        self.utilizations: dict[tuple[str, str], CurveForecastInput] = {}
        self.distances: dict[tuple[str, str], Scalar | Expression | None] = {}
        self.port_durations: dict[tuple[str, str], ForecastInput | None] = {}
        self.voyage_shares: dict[tuple[str, str], ScalarInput | None] = {}

        # per port, keyed by its name
        self.port_calls: dict[str, ForecastInput] = {}

        # internal variables -----------------------------------------------------------
        # each port once, in the order the route first calls it
        self.distinct_ports: tuple[Port, ...]

        # the per-leg inputs in the order of get_legs, empty where the route type
        # reads none
        self.leg_speeds: tuple[CurveInput, ...]
        self.leg_utilizations: tuple[CurveForecastInput, ...]
        self.leg_distances: tuple[Scalar | Expression, ...]
        self.leg_port_durations: tuple[ForecastInput, ...]
        self.leg_voyage_shares: tuple[ScalarInput, ...]

        self.conditions_per_leg: tuple[int, ...]

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(SECTION_DEFINE, required=True)
    def set_route_type(self, value: str) -> None:
        """Set the route type."""
        self.route_type = assign_id(value, RouteTypeID)

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_ports(self, value: Port | list[Port]) -> None:
        """Set the list of ports available for bunkering on the route."""
        self.ports = assign_reference_list(value, PORT, min_length=1)

    @deck_attribute()
    def set_time_at_sea(self, value: ForecastArgument) -> None:
        """Set the fraction of time spent at sea."""
        self.time_at_sea = assign_value(
            as_scalar(value),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            upper=1.0,
            inclusive_lower=False,
        )

    # external methods (DSL commands) --------------------------------------------------
    @deck_command()
    def set_speed(self, key1: str, key2: str, value: CurveArgument) -> None:
        """Set the speed, or the distribution of speeds, sailed on a leg."""
        speed: CurveInput

        if isinstance(value, Curve):
            # a Curve's y is the share of the leg's sea time sailed at its x, the speed
            speed = assign_value(value, type_=CURVE, lower=0.0, upper=1.0)
        else:
            # CURVE lets an expression referencing a Curve through the reference
            # walk, so that check_consistency rejects it with its own message
            speed = assign_value(
                as_scalar(value),
                type_=(CURVE, VARIABLE),
                lower=0.0,
                inclusive_lower=False,
            )

        self._write_legs((key1, key2), speed, self.speeds)

    @deck_command()
    def set_utilization(
        self, key1: str, key2: str, value: CurveForecastArgument
    ) -> None:
        """Set the cargo capacity utilization on a leg."""
        if isinstance(value, Curve) and self.route_type != RouteTypeID.TRAMP:
            raise ValueError(
                f"only accepts a Curve on a TRAMP route, but {self} is a"
                f" {self.route_type.name} route"
            )

        self._write_legs(
            (key1, key2),
            assign_value(
                as_scalar(value),
                type_=(CURVE, FORECAST, VARIABLE),
                lower=0.0,
                upper=1.0,
            ),
            self.utilizations,
        )

    @deck_command(SECTION_DEFINE)
    def set_distance(self, key1: str, key2: str, value: NumberInput) -> None:
        """Set the distance of a leg."""
        self._check_route_type(RouteTypeID.LINER)

        self._write_legs(
            (key1, key2),
            assign_value(as_scalar(value), lower=0.0, inclusive_lower=False),
            self.distances,
        )

    @deck_command()
    def set_port_duration(self, key1: str, key2: str, value: ForecastArgument) -> None:
        """Set the time in port at the stop that ends a leg."""
        self._check_route_type(RouteTypeID.LINER)

        self._write_legs(
            (key1, key2),
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0),
            self.port_durations,
        )

    @deck_command()
    def set_voyage_distribution(
        self, key1: str, key2: str, value: ScalarArgument
    ) -> None:
        """Set the share of the sea miles sailed on a leg."""
        self._check_route_type(RouteTypeID.TRAMP)

        self._write_legs(
            (key1, key2),
            assign_value(as_scalar(value), type_=VARIABLE, lower=0.0, upper=1.0),
            self.voyage_shares,
        )

    @deck_command()
    def set_port_calls(self, key: str, value: ForecastArgument) -> None:
        """Set the number of calls at a port over the reference year."""
        self._check_route_type(RouteTypeID.TRAMP)

        if not matching_keys(key, self.port_calls):
            raise ValueError(f'is given "{key}", which matches no port of {self}')

        write_matching_keys(
            key,
            assign_value(
                as_scalar(value),
                type_=(FORECAST, VARIABLE),
                lower=0.0,
                inclusive_lower=False,
            ),
            self.port_calls,
        )

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:
        if self.route_type == RouteTypeID.TRAMP and self.time_at_sea is None:
            raise UnassignedAttributeError(str(self), "TimeAtSea")

        # initialize_dependencies seeds only the legs of the inputs the route type
        # reads, and no command can unassign a leg once DEFINE is read
        self._check_legs_assigned("set_speed", self.speeds)
        self._check_legs_assigned("set_distance", self.distances)
        self._check_legs_assigned("set_port_duration", self.port_durations)
        self._check_legs_assigned("set_voyage_distribution", self.voyage_shares)

    def apply_defaults(self) -> None:
        # the ports are DEFINE-only, so their distinct order is fixed from here on
        self.distinct_ports = tuple(unique_list(self.ports))

        # the expectations are sized by the sailing conditions once DEFINE is read,
        # so the number on each leg is fixed from here on
        self.conditions_per_leg = self._count_conditions()

    def apply_command_defaults(self) -> None:
        # initialize_dependencies seeds each dictionary in the order of get_legs
        self.leg_speeds = in_seeded_order(self.speeds)
        self.leg_utilizations = in_seeded_order(self.utilizations)
        self.leg_distances = in_seeded_order(self.distances)
        self.leg_port_durations = in_seeded_order(self.port_durations)
        self.leg_voyage_shares = in_seeded_order(self.voyage_shares)

    def check_consistency(self) -> None:
        if self.route_type == RouteTypeID.LINER:
            self._check_liner()

        elif self.route_type == RouteTypeID.TRAMP:
            self._check_tramp()

        keys = self.get_leg_keys()
        legs = zip(keys, self.leg_speeds, self.leg_utilizations, strict=True)

        for key, speed, utilization in legs:
            self._check_speed(key, speed)
            self._check_utilization(key, speed, utilization)

        self._check_conditions_per_leg()

    def initialize_dependencies(self) -> None:
        """Initialize dependent dictionaries to allow wildcarding in command calls."""
        # stays None when unset: check_requirements names each leg left unassigned
        keys = self.get_leg_keys()

        for key in keys:
            self.speeds.setdefault(key, None)
            self.utilizations.setdefault(key, Scalar(1.0))

        if self.route_type == RouteTypeID.LINER:
            for key in keys:
                self.distances.setdefault(key, None)
                self.port_durations.setdefault(key, None)

        elif self.route_type == RouteTypeID.TRAMP:
            for key in keys:
                self.voyage_shares.setdefault(key, None)

            for port in self.ports:
                self.port_calls.setdefault(port.name, Scalar(1.0))

    def check_dynamic_consistency(self, times: FloatArray, dates: DateArray) -> None:
        # a vessel's freight and costs are spread over its cargo miles, which a
        # ballast leg lacks but the route as a whole must have
        carries_cargo = np.zeros(len(times), dtype=bool)
        sailed = self._sailed_legs()
        legs = zip(self.leg_speeds, self.leg_utilizations, sailed, strict=True)

        for speed, utilization, is_sailed in legs:
            if is_sailed:
                carries_cargo |= self._carries_cargo_on_leg(speed, utilization, times)

        empty = np.flatnonzero(~carries_cargo)

        if empty.size:
            date = dates[empty[0]]
            raise ValueError(
                f"{self}: 'set_utilization' is 0 wherever the route sails at"
                f" {date}; a leg may be sailed without cargo, but the route must"
                " carry cargo on at least one leg it sails at every time step."
            )

    def _write_legs[V](
        self, pattern: tuple[str, str], value: V, inputs: dict[tuple[str, str], V]
    ) -> None:
        """Write a value to every leg of the route a pair of port names matches."""
        # the pair is matched as a whole against the legs initialize_dependencies
        # seeds, so a wildcard in one part never creates a pair that is no leg
        pattern_from, pattern_to = pattern
        legs = []

        for origin, destination in inputs:
            origin_matches = name_matches(pattern_from, origin)
            destination_matches = name_matches(pattern_to, destination)

            if origin_matches and destination_matches:
                legs.append((origin, destination))

        if not legs:
            raise ValueError(
                f"is given {key_tuple_name(pattern)}, which matches no leg of {self}"
            )

        # every matched leg holds the same object: a Scalar answers a getter and
        # carries no per-leg state, and a node or an expression was always shared
        for leg in legs:
            inputs[leg] = value

    def _check_route_type(self, route_type: RouteTypeID) -> None:
        """Raise where a command applying to one route type is given to another."""
        if self.route_type != route_type:
            raise ValueError(
                f"only applies to a {route_type.name} route, but {self} is a"
                f" {self.route_type.name} route"
            )

    def _check_legs_assigned[V](
        self, command: str, inputs: Mapping[tuple[str, str], V | None]
    ) -> None:
        """Raise where a per-leg input the route type requires is unassigned."""
        missing = [key for key, value in inputs.items() if value is None]

        if missing:
            legs = ", ".join(key_tuple_name(key) for key in missing)
            raise DeckInsufficientError(
                f"{self}: '{command}' is unassigned for the legs {legs}."
            )

    def _check_liner(self) -> None:
        """Check the port sequence of a LINER, and that it is given no TimeAtSea."""
        if len(self.ports) < 2:
            raise ValueError(
                f"{self}: Must have a minimum of 2 ports assigned for a LINER,"
                f" only {len(self.ports)} were given."
            )

        for port, next_port in pairwise(self.ports):
            if port is next_port:
                raise ValueError(
                    f"{self}: Unable to place {port} after itself in the sequence."
                )

        if self.ports[0] is self.ports[-1]:
            raise ValueError(
                f"{self}: The set of ports is assumed to wrap around for a"
                f" LINER, so {self.ports[0]} cannot be placed both first and last."
            )

        # a port may be revisited, but each leg keys its own inputs
        counts = Counter(self.get_leg_keys())
        repeated = [key for key, count in counts.items() if count > 1]

        if repeated:
            raise ValueError(
                f"{self}: A LINER may call at a port more than once, but may not sail"
                f" the leg {key_tuple_name(repeated[0])} more than once."
            )

        if self.time_at_sea is not None:
            raise ValueError(f"{self}: 'TimeAtSea' only applies to a TRAMP route.")

    def _check_tramp(self) -> None:
        """Check that the ports of a TRAMP are unique."""
        if len(self.distinct_ports) < len(self.ports):
            raise ValueError(f"{self}: All ports on a TRAMP must be unique.")

    def _check_speed(self, key: tuple[str, str], speed: CurveInput) -> None:
        """Check that a leg's speed Curve lists positive speeds and whole shares."""
        if isinstance(speed, Expression):
            self._check_single_valued("set_speed", key, speed)
            return

        if not isinstance(speed, Curve):
            return

        if speed.x[0] <= 0.0:
            raise ValueError(
                f"{self}: The speeds of {speed} on the leg {key_tuple_name(key)}"
                f" must be greater than 0, but the lowest is {speed.x[0]}."
            )

        # one Curve may serve many legs, so its shares are never rescaled
        total = round(float(np.sum(speed.get(speed.x))), ROUND_OFF)
        if total != 1.0:
            raise ValueError(
                f"{self}: The shares of {speed} on the leg {key_tuple_name(key)}"
                f" must sum to 1, but sum to {total}."
            )

    def _check_utilization(
        self, key: tuple[str, str], speed: CurveInput, utilization: CurveForecastInput
    ) -> None:
        """Check that a leg's utilization Curve lists the speeds of its speed Curve."""
        if isinstance(utilization, Expression):
            self._check_single_valued("set_utilization", key, utilization)
            return

        if not isinstance(utilization, Curve):
            return

        if not isinstance(speed, Curve):
            raise ValueError(
                f"{self}: {utilization} gives a utilization per speed on the leg"
                f" {key_tuple_name(key)}, but the leg is sailed at the one speed"
                f" {speed}."
            )

        # a utilization belongs to a sailing condition, so it is read at the speeds
        # the leg's speed Curve lists, wherever speed management moves them
        if not np.array_equal(utilization.x, speed.x):
            raise ValueError(
                f"{self}: The speeds of {utilization} on the leg {key_tuple_name(key)}"
                f" must equal those of its speed Curve, {speed}."
            )

    def _check_single_valued(
        self, command: str, key: tuple[str, str], expression: Expression
    ) -> None:
        """Raise where an expression on a leg references a Curve it cannot read."""
        # an expression is evaluated without an input, as one value per leg, so a
        # Curve it references has no speed to be read at
        if any(isinstance(node, Curve) for node in expression.calculators.values()):
            raise ValueError(
                f"{self}: The expression <{expression}> given to '{command}' on the"
                f" leg {key_tuple_name(key)} references a Curve, but an expression is"
                " one value per leg; assign the Curve itself instead."
            )

    def _check_conditions_per_leg(self) -> None:
        """Raise where an event changes the number of sailing conditions on a leg."""
        keys = self.get_leg_keys()
        conditions = self._count_conditions()
        legs = zip(keys, conditions, self.conditions_per_leg, strict=True)

        for key, count, count_define in legs:
            if count != count_define:
                raise ValueError(
                    f"{self}: The speed on the leg {key_tuple_name(key)} has {count}"
                    f" sailing conditions, but had {count_define} once DEFINE was"
                    " read; the number of sailing conditions on a leg is fixed."
                )

    def _count_conditions(self) -> tuple[int, ...]:
        """Count the sailing conditions on each leg, one per speed its input lists."""
        speeds = in_seeded_order(self.speeds)

        return tuple(
            len(speed.x) if isinstance(speed, Curve) else 1 for speed in speeds
        )

    def _sailed_legs(self) -> BoolArray:
        """Tell which legs the route sails, in the order of get_legs."""
        if self.route_type == RouteTypeID.LINER:
            return np.ones(len(self.leg_speeds), dtype=bool)

        return self.get_voyage_shares() > 0.0

    def _carries_cargo_on_leg(
        self, speed: CurveInput, utilization: CurveForecastInput, times: FloatArray
    ) -> BoolArray:
        """Tell at each time whether a leg carries cargo in a condition it sails."""
        # check_consistency gives a utilization Curve a speed Curve listing the same
        # speeds, so its utilization per sailing condition is constant over time
        if isinstance(utilization, Curve) and isinstance(speed, Curve):
            is_sailed = speed.get(speed.x) > 0.0
            is_loaded = utilization.get(speed.x) > 0.0
            return np.full(len(times), np.any(is_sailed & is_loaded))

        # the one utilization holds in every sailing condition, and the shares of
        # a speed Curve sum to 1, so the leg sails at least one
        return utilization.get(times) > 0.0

    def get_legs(self) -> tuple[tuple[int, int], ...]:
        """
        Return the (origin, destination) stop indices of each leg, in canonical order.

        Every per-leg value on the route is ordered as this tuple.

        Returns
        -------
        tuple[tuple[int, int], ...]
            Consecutive stops, the last leg returning to the first, for a LINER;
            every ordered pair of ports, origin-major, for a TRAMP.
        """
        n_ports = len(self.ports)

        if self.route_type == RouteTypeID.LINER:
            return tuple((i, (i + 1) % n_ports) for i in range(n_ports))

        return tuple((i, j) for i in range(n_ports) for j in range(n_ports))

    def get_leg_keys(self) -> tuple[tuple[str, str], ...]:
        """
        Return the (origin, destination) port names of each leg, in canonical order.

        The names key the per-leg inputs the commands write.

        Returns
        -------
        tuple[tuple[str, str], ...]
            Port names of each leg, in the order of `get_legs`.
        """
        names = [port.name for port in self.ports]
        return tuple((names[i], names[j]) for i, j in self.get_legs())

    def get_conditions(self) -> tuple[tuple[int, int], ...]:
        """
        Return the leg and the speed entry of each sailing condition, leg-major.

        Every per-condition value on the route is ordered as this tuple. The entry
        indexes the speeds of the leg's speed Curve; a leg sailed at one speed has
        the one entry 0.

        Returns
        -------
        tuple[tuple[int, int], ...]
            Leg and speed entry of each sailing condition.
        """
        return tuple(
            (leg, entry)
            for leg, n_conditions in enumerate(self.conditions_per_leg)
            for entry in range(n_conditions)
        )

    def get_voyage_shares(self) -> FloatArray:
        """
        Return the voyage shares of a TRAMP route, normalized to sum to unity.

        The shares are rounded in total, and split equally where they total zero.

        Returns
        -------
        FloatArray
            Voyage share of each leg, in the order of `get_legs`.
        """
        shares = to_array(self.leg_voyage_shares)
        total = np.round(np.sum(shares), ROUND_OFF)

        return divide_nonzero(shares, total, default=1.0 / len(shares))

    def get_stops(self) -> range:
        """
        Return the index of each stop of the route.

        Returns
        -------
        range
            One index per entry of the route's ports, so a port called twice is two
            stops.
        """
        return range(len(self.ports))

    def get_tank_stops(self) -> tuple[int, ...]:
        """
        Return the stops at which the bunkering tracks the fuel held in the tank.

        Returns
        -------
        tuple[int, ...]
            Every stop of a LINER; none of a TRAMP, whose stops follow no sequence
            to carry fuel along.
        """
        if self.route_type == RouteTypeID.LINER:
            return tuple(self.get_stops())

        return ()

    def get_tank_legs(self) -> tuple[tuple[int, int], ...]:
        """
        Return the legs that carry the fuel tank from one tank stop to the next.

        Returns
        -------
        tuple[tuple[int, int], ...]
            The legs of a LINER except the one returning to the first stop; none
            of a TRAMP.
        """
        if self.route_type == RouteTypeID.LINER:
            return tuple((i, i + 1) for i in range(len(self.ports) - 1))

        return ()
