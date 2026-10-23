# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Route node, the ports, legs and sailing conditions a vessel trades on."""

from __future__ import annotations

from collections import Counter
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
from navigate.core.enum_ import RouteTypeID
from navigate.core.node import Node
from navigate.core.node_type import CURVE, FORECAST, PORT, ROUTE, VARIABLE
from navigate.core.nodes.curve import Curve
from navigate.exceptions import DeckInsufficientError, UnassignedAttributeError
from navigate.util import ROUND_OFF, matching_keys, unique_list

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


class Route(Node):
    """The ports a vessel calls at and the legs and sailing conditions between them."""

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
        self.voyage_distribution: dict[tuple[str, str], ScalarInput | None] = {}

        # per port, keyed by its name
        self.port_calls: dict[str, ForecastInput] = {}

        # internal variables -----------------------------------------------------------
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
    def set_route_type(self, route_type: str) -> None:
        """Set the route type."""
        self.route_type = assign_id(route_type, RouteTypeID)

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_ports(self, ports: Port | list[Port]) -> None:
        """Set the list of ports available for bunkering on the route."""
        self.ports = assign_reference_list(ports, PORT, min_length=1)

    @deck_attribute()
    def set_time_at_sea(self, time_at_sea: ForecastArgument) -> None:
        """Set the fraction of time spent at sea."""
        self.time_at_sea = assign_value(
            as_scalar(time_at_sea),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            upper=1.0,
            inclusive_lower=False,
        )

    # external methods (DSL commands) --------------------------------------------------
    @deck_command()
    def set_speed(
        self, port_name_from: str, port_name_to: str, speed: CurveArgument
    ) -> None:
        """Set the speed, or the distribution of speeds, sailed on a leg."""
        value: CurveInput

        # a Curve's y is the share of the leg's sea time sailed at its x, the speed
        if isinstance(speed, Curve):
            value = assign_value(speed, type_=CURVE, lower=0.0, upper=1.0)
        else:
            # CURVE lets an expression referencing a Curve through the reference
            # walk, so that check_consistency rejects it with its own message
            value = assign_value(
                as_scalar(speed),
                type_=(CURVE, VARIABLE),
                lower=0.0,
                inclusive_lower=False,
            )

        self._write_legs((port_name_from, port_name_to), value, self.speeds)

    @deck_command()
    def set_utilization(
        self, port_name_from: str, port_name_to: str, utilization: CurveForecastArgument
    ) -> None:
        """Set the cargo capacity utilization on a leg."""
        if isinstance(utilization, Curve) and self.route_type != RouteTypeID.TRAMP:
            raise ValueError(
                f"only accepts a Curve on a TRAMP route, but {self} is a"
                f" {self.route_type.name} route"
            )

        self._write_legs(
            (port_name_from, port_name_to),
            assign_value(
                as_scalar(utilization),
                type_=(CURVE, FORECAST, VARIABLE),
                lower=0.0,
                upper=1.0,
            ),
            self.utilizations,
        )

    @deck_command(SECTION_DEFINE)
    def set_distance(
        self, port_name_from: str, port_name_to: str, distance: NumberInput
    ) -> None:
        """Set the distance of a leg."""
        self._check_route_type(RouteTypeID.LINER)

        self._write_legs(
            (port_name_from, port_name_to),
            assign_value(as_scalar(distance), lower=0.0, inclusive_lower=False),
            self.distances,
        )

    @deck_command()
    def set_port_duration(
        self, port_name_from: str, port_name_to: str, port_duration: ForecastArgument
    ) -> None:
        """Set the time in port at the stop that ends a leg."""
        self._check_route_type(RouteTypeID.LINER)

        self._write_legs(
            (port_name_from, port_name_to),
            assign_value(
                as_scalar(port_duration), type_=(FORECAST, VARIABLE), lower=0.0
            ),
            self.port_durations,
        )

    @deck_command()
    def set_voyage_distribution(
        self, port_name_from: str, port_name_to: str, fraction: ScalarArgument
    ) -> None:
        """Set the share of the sea miles sailed on a leg."""
        self._check_route_type(RouteTypeID.TRAMP)

        self._write_legs(
            (port_name_from, port_name_to),
            assign_value(as_scalar(fraction), type_=VARIABLE, lower=0.0, upper=1.0),
            self.voyage_distribution,
        )

    @deck_command()
    def set_port_calls(self, port_name: str, port_calls: ForecastArgument) -> None:
        """Set the number of calls at a port over the reference year."""
        self._check_route_type(RouteTypeID.TRAMP)

        if not matching_keys(port_name, self.port_calls):
            raise ValueError(f'is given "{port_name}", which matches no port of {self}')

        write_matching_keys(
            port_name,
            assign_value(
                as_scalar(port_calls),
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
        self._check_legs_assigned("set_voyage_distribution", self.voyage_distribution)

    def apply_defaults(self) -> None:
        # the expectations are sized by the sailing conditions once DEFINE is read,
        # so the number on each leg is fixed from here on
        self.conditions_per_leg = _count_conditions(_in_seeded_order(self.speeds))

    def apply_command_defaults(self) -> None:
        # initialize_dependencies seeds each dictionary in the order of get_legs
        self.leg_speeds = _in_seeded_order(self.speeds)
        self.leg_utilizations = _in_seeded_order(self.utilizations)
        self.leg_distances = _in_seeded_order(self.distances)
        self.leg_port_durations = _in_seeded_order(self.port_durations)
        self.leg_voyage_shares = _in_seeded_order(self.voyage_distribution)

    def check_consistency(self) -> None:

        if self.route_type == RouteTypeID.LINER:
            self._check_liner()

        elif self.route_type == RouteTypeID.TRAMP:
            self._check_tramp()

        legs = zip(
            self.get_leg_keys(), self.leg_speeds, self.leg_utilizations, strict=True
        )
        for key, speed, utilization in legs:
            self._check_speed(key, speed)
            self._check_utilization(key, speed, utilization)

        self._check_conditions_per_leg()

    def initialize_dependencies(self) -> None:
        """Initialize dependent dictionaries so command calls can use wildcards."""
        # stays None when unset: check_requirements names each leg left unassigned
        for key in self.get_leg_keys():
            self.speeds.setdefault(key, None)
            self.utilizations.setdefault(key, Scalar(1.0))

            if self.route_type == RouteTypeID.LINER:
                self.distances.setdefault(key, None)
                self.port_durations.setdefault(key, None)

            elif self.route_type == RouteTypeID.TRAMP:
                self.voyage_distribution.setdefault(key, None)

        if self.route_type == RouteTypeID.TRAMP:
            for port in self.ports:
                self.port_calls.setdefault(port.name, Scalar(1.0))

    def _write_legs[V](
        self, key: tuple[str, str], value: V, inputs: dict[tuple[str, str], V]
    ) -> None:
        """Write a value to every leg of the route a pair of port names matches."""
        # the pair is matched as a whole against the legs initialize_dependencies
        # seeds, so a wildcard in one part never creates a pair that is no leg
        pattern_from, pattern_to = key
        legs = [
            (port_from, port_to)
            for port_from, port_to in inputs
            if matching_keys(pattern_from, [port_from])
            and matching_keys(pattern_to, [port_to])
        ]

        if not legs:
            raise ValueError(
                f"is given {_name_leg(key)}, which matches no leg of {self}"
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
            raise DeckInsufficientError(
                f"{self}: '{command}' is unassigned for the legs"
                f" {', '.join(_name_leg(key) for key in missing)}."
            )

    def _check_liner(self) -> None:
        """Check the port sequence of a LINER, and that it is given no TimeAtSea."""
        if len(self.ports) < 2:
            raise ValueError(
                f"{self}: Must have a minimum of 2 ports assigned for a LINER,"
                f" only {len(self.ports)} were given."
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
                f" LINER, so {self.ports[0]} cannot be placed both first and last."
            )

        # a port may be revisited, but each leg keys its own inputs
        counts = Counter(self.get_leg_keys())
        repeated = [key for key, count in counts.items() if count > 1]

        if repeated:
            raise ValueError(
                f"{self}: A LINER may call at a port more than once, but may not sail"
                f" the leg {_name_leg(repeated[0])} more than once."
            )

        if self.time_at_sea is not None:
            raise ValueError(f"{self}: 'TimeAtSea' only applies to a TRAMP route.")

    def _check_tramp(self) -> None:
        """Check that the ports of a TRAMP are unique."""
        if len(self.ports) > len(unique_list(self.ports)):
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
                f"{self}: The speeds of {speed} on the leg {_name_leg(key)} must be"
                f" greater than 0, but the lowest is {speed.x[0]}."
            )

        # one Curve may serve many legs, so its shares are never rescaled
        total = round(float(np.sum(speed.get(speed.x))), ROUND_OFF)
        if total != 1.0:
            raise ValueError(
                f"{self}: The shares of {speed} on the leg {_name_leg(key)} must sum"
                f" to 1, but sum to {total}."
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
                f" {_name_leg(key)}, but the leg is sailed at the one speed {speed}."
            )

        # a utilization belongs to a sailing condition, so it is read at the speeds
        # the leg's speed Curve lists, wherever speed management moves them
        if not np.array_equal(utilization.x, speed.x):
            raise ValueError(
                f"{self}: The speeds of {utilization} on the leg {_name_leg(key)}"
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
                f" leg {_name_leg(key)} references a Curve, but an expression is"
                " one value per leg; assign the Curve itself instead."
            )

    def _check_conditions_per_leg(self) -> None:
        """Raise where an event changes the number of sailing conditions on a leg."""
        conditions = _count_conditions(self.leg_speeds)
        legs = zip(
            self.get_leg_keys(), conditions, self.conditions_per_leg, strict=True
        )

        for key, count, count_define in legs:
            if count != count_define:
                raise ValueError(
                    f"{self}: The speed on the leg {_name_leg(key)} has {count}"
                    f" sailing conditions, but had {count_define} once DEFINE was"
                    " read; the number of sailing conditions on a leg is fixed."
                )

    def get_number_of_ports(self) -> int:
        return len(self.ports)

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
        n_ports = self.get_number_of_ports()

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
            return tuple(range(self.get_number_of_ports()))

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
            return tuple((i, i + 1) for i in range(self.get_number_of_ports() - 1))

        return ()


def _in_seeded_order[K, V](inputs: Mapping[K, V | None]) -> tuple[V, ...]:
    """
    Return the values of a command dictionary in the order it is seeded.

    Parameters
    ----------
    inputs
        Command dictionary, every entry assigned.

    Returns
    -------
    tuple[V, ...]
        The assigned values.
    """
    # check_requirements leaves no seeded entry unassigned, so the None test only
    # narrows the type
    return tuple(value for value in inputs.values() if value is not None)


def _count_conditions(speeds: tuple[CurveInput, ...]) -> tuple[int, ...]:
    """
    Count the sailing conditions on each leg: one per speed its speed input lists.

    Parameters
    ----------
    speeds
        Speed input of each leg.

    Returns
    -------
    tuple[int, ...]
        Number of sailing conditions on each leg.
    """
    return tuple(len(speed.x) if isinstance(speed, Curve) else 1 for speed in speeds)


def _name_leg(key: tuple[str, str]) -> str:
    """
    Name a leg as a command addresses it.

    Parameters
    ----------
    key
        Port names of the leg's origin and destination.

    Returns
    -------
    str
        The leg's port names, quoted as the command arguments are.
    """
    origin, destination = key
    return f'("{origin}", "{destination}")'
