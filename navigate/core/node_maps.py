# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Maps between nodes: derived from static attributes or rewritten each time step."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import FuelTypeID

if TYPE_CHECKING:
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.levy import Levy
    from navigate.core.nodes.port import Port


def get_fuels_per_fuel_type(fuels: dict[str, Fuel]) -> dict[FuelTypeID, list[Fuel]]:
    """
    Group all simulation fuels by fuel type.

    Parameters
    ----------
    fuels
        All fuels in the simulation, keyed by name.

    Returns
    -------
    dict[FuelTypeID, list[Fuel]]
        Every FuelTypeID as a key, mapped to the fuels of that type in input
        iteration order; a fuel type with no fuels maps to an empty list.
    """
    # construct dict of fuels per fuel types
    fuel_per_fuel_type: dict[FuelTypeID, list[Fuel]] = {id_: [] for id_ in FuelTypeID}

    for fuel in fuels.values():
        fuel_type = fuel.fuel_type
        fuel_per_fuel_type[fuel_type].append(fuel)

    return fuel_per_fuel_type


def update_port_levies(ports: dict[str, Port], levies: dict[str, Levy]) -> None:
    """
    Rewrite the levies of each port as the active levies whose jurisdiction holds it.

    Parameters
    ----------
    ports
        All ports in the simulation, keyed by name.
    levies
        All levies in the simulation, keyed by name.
    """
    active_levies = [levy for levy in levies.values() if levy.is_active()]

    for port in ports.values():
        port.levies = [levy for levy in active_levies if port in levy.jurisdiction]
