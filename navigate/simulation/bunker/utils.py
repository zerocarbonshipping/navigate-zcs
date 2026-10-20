# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Look up the converters and port indices the LP is keyed by."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.util import define_index_map

if TYPE_CHECKING:
    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.route import Route
    from navigate.core.nodes.vessel import Vessel


def get_converters(vessel: Vessel) -> dict[str, Converter]:
    """
    Return the three converters of a vessel, keyed by name.

    Parameters
    ----------
    vessel
        Vessel whose converters are returned.

    Returns
    -------
    dict[str, Converter]
        The propulsion, electrical, and heat converters keyed by name.
    """
    return {converter.name: converter for converter in vessel.get_converters()}


def get_port_converters(vessel: Vessel) -> dict[str, Converter]:
    """
    Return the two converters serving port energy demands, keyed by name.

    Parameters
    ----------
    vessel
        Vessel whose port converters are returned.

    Returns
    -------
    dict[str, Converter]
        The electrical and heat converters keyed by name.
    """
    converters = (vessel.electrical_converter, vessel.heat_converter)
    return {converter.name: converter for converter in converters}


def get_port_name_to_indices(route: Route) -> dict[str, list[int]]:
    """
    Return the port indices of a route, keyed by port name.

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
