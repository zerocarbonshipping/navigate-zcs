# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

import navigate.core.enum_ as enum_
from navigate.util import define_index_map

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.route import Route
    from navigate.core.nodes.vessel import Vessel


def extract_times(vessel: Vessel, idx: int) -> tuple[list, list]:
    """
    Extract time at sea and time in port for a vessel.

    Parameters
    ----------
    vessel
        Vessel for which constraint is being added.
    idx
        Current time-step index.

    Returns
    -------
    tuple[list, list]
        The time at sea and time in port for the vessel (days).
    """

    time_sea = vessel.expectation.get_time_sea(idx)
    time_port = vessel.expectation.get_time_port(idx)

    route = vessel.route
    route_type = route.route_type

    # group to a single cumulative leg
    if route_type == enum_.RouteTypeID.REGIONAL_TRIP:

        sailing_fractions = route.get_voyage_distribution(to_array=True)
        time_sea = np.multiply(sum(time_sea), sailing_fractions)

    return time_sea, time_port


def get_converters(vessel: Vessel) -> dict[str, Converter]:
    """
    The three converters of a vessel's power system, keyed by name.

    Parameters
    ----------
    vessel
        Vessel whose power system is queried.

    Returns
    -------
    dict[str, Converter]
        The propulsion, electrical, and heat converters keyed by name.
    """

    return {c.name: c for c in vessel.power_system.get_converters()}


def get_port_converters(vessel: Vessel) -> dict[str, Converter]:
    """
    The two converters that serve port energy demands (electrical and heat), keyed by name.

    Parameters
    ----------
    vessel
        Vessel whose power system is queried.

    Returns
    -------
    dict[str, Converter]
        The electrical and heat converters keyed by name.
    """

    power_system = vessel.power_system
    return {c.name: c for c in (power_system.electrical, power_system.heat)}


def initialize_converter_fuel_maps(alg: BunkerAlgorithm) -> None:
    """
    Precompute, per vessel, which fuels each converter can use, and the inverse maps.

    Fills ``alg.fuels_per_converter``, ``alg.converters_per_fuel`` and
    ``alg.port_converters_per_fuel``. The maps are static: converter fuel types and
    vessel usable fuels are fixed once the existing fleet is initialized, which
    happens after the algorithm itself is initialized -- hence they are built on the
    first call to ``BunkerAlgorithm.build`` instead of in ``initialize``.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    for fleet in alg.fleets.values():

        for vessel in fleet.vessels:

            v = vessel.name
            converters = get_converters(vessel)
            port_converters = get_port_converters(vessel)

            for c, converter in converters.items():
                fuel_types = converter.get_fuel_types()
                alg.fuels_per_converter[(v, c)] = {f: fuel for f, fuel in vessel.usable_fuels.items()
                                                   if fuel.fuel_type in fuel_types}

            for f in vessel.usable_fuels:
                alg.converters_per_fuel[(v, f)] = tuple(c for c in converters
                                                        if f in alg.fuels_per_converter[(v, c)])
                alg.port_converters_per_fuel[(v, f)] = tuple(c for c in port_converters
                                                             if f in alg.fuels_per_converter[(v, c)])


def get_port_name_to_indices(route: Route) -> dict[str, list[int]]:
    """
    The port indices of a route, keyed by port name.

    Parameters
    ----------
    route
        Route whose ports are indexed.

    Returns
    -------
    dict[str, list[int]]
        A name maps to multiple indices when a route calls the same port more than once.
    """

    return define_index_map([port.name for port in route.ports])
