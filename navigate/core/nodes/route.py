# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import itertools
import logging

import numpy as np

from navigate.core import (
    Scalar,
    as_list,
    as_scalar,
    as_scalar_list,
    assign_fraction_list,
    assign_id,
    assign_list,
    assign_value,
    command_assignment_to_tuple_dict,
)
from navigate.core.enum_ import RouteTypeID
from navigate.core.id_ import FORECAST, PORT, ROUTE, VARIABLE
from navigate.core.node import Node
from navigate.exceptions import no_value_assigned_error
from navigate.util import normalize_fractional, to_numpy, unique_list

logger = logging.getLogger(__name__)


class Route(Node):
    def __init__(self, name):
        super().__init__(name)

        self._type = ROUTE

        self.route_type = None             # int, route type ID
        self.ports = []                    # list[Port], ports a vessel can bunker in

        # time at sea/in port
        self.port_durations = []           # list[float], duration spend in each port, days (round trip)
        self.time_at_sea = None            # float, fraction of time spent at sea (regional trip)
        self.port_calls = []               # list[float], number of times each port is called (regional trip)

        # conditions per leg
        self.speeds = []                   # list[float], speed of the vessel, knots
        self.capacity_utilizations = []    # list[float], cargo capacity utilization, fraction
        self.distances = []                # list[float], distance per leg, nautical miles (round trip)
        self.condition_distribution = []   # list[float], time at condition, fraction (regional trip)

        # regulation
        self.voyage_distribution = {}      # dict[(port_name, port_name)], fraction of sea time spent between ports

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_route_type(self, route_type):
        """
        Set the route type.

        Examples
        --------
        - ROUND_TRIP
        - REGIONAL_TRIP

        Parameters
        ----------
        route_type : str
            Assignment read from input deck.
        """

        self.route_type = assign_id(route_type, RouteTypeID)

    def set_ports(self, ports):
        """
        Set the list of ports available for bunkering on the route.

        Examples
        --------
        - Port("name")
        - [Port("name1"), Port("name2")]

        Parameters
        ----------
        ports : list[NodeReference]
            A list of NodeReference to a Port.
        """

        self.ports = assign_list(as_list(ports), scalar=False, type_=PORT)

    def set_port_durations(self, port_durations):
        """
        Set the duration spent at each port call of the trip, days.

        Only applicable if 'RouteType' is ROUND_TRIP.

        Examples
        --------
        - [2]
        - [3.5, 5]

        Parameters
        ----------
        port_durations : list[float | NodeReference]
            A list of floats or NodeReferences to a Forecast.
        """

        self.port_durations = assign_list(as_scalar_list(port_durations), type_=(FORECAST, VARIABLE), lower=0.)

    def set_time_at_sea(self, time_at_sea):
        """
        Set the fraction of time spent at sea.

        Only applicable if 'RouteType' is REGIONAL_TRIP.

        Examples
        --------
        - 0.75

        Parameters
        ----------
        time_at_sea : float
            Fraction of time spent at sea.
        """

        self.time_at_sea = assign_value(as_scalar(time_at_sea), type_=(FORECAST, VARIABLE), lower=0., upper=1.)

    def set_port_calls(self, port_calls):
        """
        Set the number of port calls per port over the reference duration.

        Only applicable if 'RouteType' is REGIONAL_TRIP.

        Examples
        --------
        - [100]
        - [20, 15.5]

        Parameters
        ----------
        port_calls : list[float | NodeReference]
            A list of floats or NodeReferences to a Forecast.
        """

        self.port_calls = assign_list(as_scalar_list(port_calls), type_=(FORECAST, VARIABLE), lower=0., inclusive_lower=False)

    def set_distances(self, distances):
        """
        Set the distance of the various legs of the trip, nautical miles.

        Only applicable if 'RouteType' is ROUND_TRIP.

        Examples
        --------
        - [6000]
        - [1470, 150.8]

        Parameters
        ----------
        distances : list[float]
            A list of floats.
        """

        self.distances = assign_list(as_scalar_list(distances), lower=0., inclusive_lower=False)

    def set_condition_distribution(self, condition_distribution):
        """
        Set the fraction of time spent on the various legs of the trip.
        The sum of the coefficients in the list must equal unity.

        Only applicable if 'RouteType' is REGIONAL_TRIP.

        Examples
        --------
        - [1]
        - [0.3, 0.7]

        Parameters
        ----------
        condition_distribution : list[float]
            A list of floats.
        """

        self.condition_distribution, normalized = assign_fraction_list(condition_distribution)

        if normalized:
            logger.info("{}: 'ConditionDistribution' is normalized to 1 by equal fractions.".format(self))

    def set_speeds(self, speeds):
        """
        Set the speed of the various legs of the trip, knots.

        Examples
        --------
        - [10.5]
        - [12, 14]

        Parameters
        ----------
        speeds : list[float | NodeReference]
            A list of floats or NodeReferences to a Forecast.
        """

        self.speeds = assign_list(as_scalar_list(speeds), type_=(FORECAST, VARIABLE), lower=0., inclusive_lower=False)

    def set_capacity_utilizations(self, capacity_utilizations):
        """
        Set the capacity utilization of the various legs of the trip.

        Examples
        --------
        - [0.8]
        - [1, 0]

        Parameters
        ----------
        capacity_utilizations : list[float | NodeReference]
            A list of floats or NodeReferences to a Forecast.
        """

        self.capacity_utilizations = assign_list(as_scalar_list(capacity_utilizations),
                                                 type_=(FORECAST, VARIABLE),
                                                 lower=0.,
                                                 upper=1.)

    # external commands called in the input deck -----------------------------------------------------------------------
    def set_voyage_distribution(self, port_name_from, port_name_to, fraction):
        """
        Set the fraction of total sailing time spent traveling from 'port_from' to 'port_to'.

        Examples
        --------
        - "port_name_from", "port_name_to", 0.5
        - "port_name_from", "port_name_to", Forecast("name")

        Parameters
        ----------
        port_name_from : str
            Name of port from which vessel departs.
        port_name_to : str
            Name of port to which vessel arrives.
        fraction : float
            Fraction of total sailing time spent traveling from 'port_from' to 'port_to'.
        """

        command_assignment_to_tuple_dict((port_name_from, port_name_to), fraction, self.voyage_distribution,
                                         type_=VARIABLE, lower=0., upper=1.)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):
        if self.route_type is None:
            no_value_assigned_error(self, 'RouteType')

        if not self.ports:
            no_value_assigned_error(self, 'Ports')

        if not self.speeds:
            no_value_assigned_error(self, 'Speeds')

        if not self.capacity_utilizations:
            self.capacity_utilizations = as_scalar_list([1. for _ in self.speeds])

        if len(self.speeds) != len(self.capacity_utilizations):
            raise ValueError(
                f"{self}: The length of 'Speeds' ({len(self.speeds)}) and "
                f"'CapacityUtilizations' ({len(self.capacity_utilizations)}) must correspond."
            )

        # checking requirements that are route type specific
        if self.route_type == RouteTypeID.ROUND_TRIP:

            if not self.port_durations:
                no_value_assigned_error(self, 'PortDurations')

            if not self.distances:
                no_value_assigned_error(self, 'Distances')

            if len(self.distances) != len(self.speeds):
                raise ValueError("{}: The length of 'Distances' ({}) and Speeds ({}) must correspond."
                                 .format(self, len(self.distances), len(self.speeds)))

            if len(self.ports) < 2:
                raise ValueError("{}: Must have a minimum of 2 ports assigned for a ROUND_TRIP, only {} were given."
                                 .format(self, len(self.ports)))

            # based on previous checks, distances is representative for all leg related lists
            if len(self.distances) != len(self.ports):
                raise ValueError("{}: The length of 'Distances' ({}) and 'Ports' ({}) must correspond for a ROUND_TRIP."
                                 .format(self, len(self.distances), len(self.ports)))

            if len(self.ports) != len(self.port_durations):
                raise ValueError("{}: The length of 'Ports' ({}) and 'PortDurations' ({}) must correspond."
                                 .format(self, len(self.ports), len(self.port_durations)))

            # the same port may not be placed in sequence
            for p in range(len(self.ports) - 1):
                if self.ports[p] is self.ports[p + 1]:
                    raise ValueError("{}: Unable to place {} after itself in the sequence."
                                     .format(self, self.ports[p]))

            # the set is assumed periodical so check first/last are not in sequence
            if self.ports[0] is self.ports[-1]:
                raise ValueError("{}: The set of ports is assumed to wrap around for a 'ROUND_TRIP', so {} cannot be"
                                 " placed both first and last.".format(self, self.ports[0]))

            if self.time_at_sea is not None:
                logger.warning("{}: 'TimeAtSea' is assigned but is unused for a ROUND_TRIP.".format(self))

            if self.port_calls:
                logger.warning("{}: 'PortCalls' is assigned but is unused for a ROUND_TRIP.".format(self))

            if self.condition_distribution:
                logger.warning("{}: 'ConditionDistribution' is assigned but is unused for a ROUND_TRIP.".format(self))

        elif self.route_type == RouteTypeID.REGIONAL_TRIP:

            if self.time_at_sea is None:
                no_value_assigned_error(self, 'TimeAtSea')

            if len(self.condition_distribution) != len(self.speeds):
                raise ValueError("{}: The length of 'ConditionDistribution' ({}) and 'Speeds' ({}) must correspond."
                                 .format(self, len(self.condition_distribution), len(self.speeds)))

            # all ports must be unique
            if len(self.ports) > len(unique_list(self.ports)):
                raise ValueError("{}: All ports on a 'REGIONAL_TRIP' must be unique.".format(self))

            if not self.port_calls:
                self.port_calls = as_scalar_list([1. for _ in self.ports])

            if len(self.ports) != len(self.port_calls):
                raise ValueError("{}: The length of 'Ports' ({}) and 'PortCalls' ({}) must correspond."
                                 .format(self, len(self.ports), len(self.port_calls)))

            if self.distances:
                logger.warning("{}: 'Distances' is assigned but is unused for a REGIONAL_TRIP.".format(self))

            if self.port_durations:
                logger.warning("{}: 'PortDurations' is assigned but is unused for a REGIONAL_TRIP.".format(self))

    def initialize_dependencies(self):
        names = [port.get_name() for port in self.ports]
        for key in itertools.product(names, names):
            self.voyage_distribution.setdefault(key, Scalar(0.))

    def get_voyage_distribution(self, to_array=False):
        fractions = normalize_fractional(self.voyage_distribution, None)

        if to_array:
            return [fractions[(pi.get_name(), pj.get_name())] for pj in self.ports for pi in self.ports]
        else:
            return fractions

    def get_number_of_legs(self):
        return len(self.speeds)

    def get_number_of_ports(self):
        return len(self.ports)

    def get_leg_indices(self) -> tuple[tuple[int, int], ...]:
        """
        The (origin, destination) port-index pairs of the legs on the route.

        Returns
        -------
        Consecutive legs for a round trip, otherwise all port-to-port combinations (required for
        regulatory purposes).
        """

        if self.route_type == RouteTypeID.ROUND_TRIP:
            n_legs = self.get_number_of_legs()
            return tuple((i, (i + 1) % n_legs) for i in range(n_legs))
        else:
            n_ports = self.get_number_of_ports()
            return tuple((i, j) for i in range(n_ports) for j in range(n_ports))

    def local_to_global_leg_idx(self, p1: int, p2: int):
        if self.route_type == RouteTypeID.ROUND_TRIP:
            return p1
        else:
            return p1 * self.get_number_of_ports() + p2

    def get_number_of_regional_legs(self):
        if self.route_type == RouteTypeID.ROUND_TRIP:
            return self.get_number_of_legs()
        else:
            return self.get_number_of_ports() ** 2

    def get_number_of_port_calls(self):
        if self.route_type == RouteTypeID.ROUND_TRIP:
            return np.ones((self.get_number_of_ports(),))
        else:
            return to_numpy(self.port_calls)
