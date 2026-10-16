# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Node maps: node attributes derived from other nodes', written once or each step."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import FuelTypeID
from navigate.util import unique_list

if TYPE_CHECKING:
    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.levy import Levy
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.vessel import Vessel


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


def define_vessel_fuel_maps(vessels: dict[str, Vessel], fuels: dict[str, Fuel]) -> None:
    """
    Write on each vessel its usable fuel types and fuels and its converter-fuel pairs.

    A usable fuel type is one a tank stores or a converter burns, and a usable fuel
    is a fuel of a usable type. Each converter is paired with the usable fuels of
    its fuel types, in usable-fuel order, and each usable fuel with the converters
    burning it, in power-system order; a fuel only a tank stores has no converter.

    Parameters
    ----------
    vessels
        All vessels in the simulation, keyed by name.
    fuels
        All fuels in the simulation, keyed by name.
    """
    fuels_per_fuel_type = get_fuels_per_fuel_type(fuels)

    for vessel in vessels.values():
        usable_fuel_types = _usable_fuel_types(vessel)
        usable_fuels = _usable_fuels(usable_fuel_types, fuels_per_fuel_type)
        fuels_per_converter = _fuels_per_converter(vessel, usable_fuels)
        converters_per_fuel = _converters_per_fuel(
            vessel, usable_fuels, fuels_per_converter
        )

        vessel.usable_fuel_types = usable_fuel_types
        vessel.usable_fuels = usable_fuels
        vessel.fuels_per_converter = fuels_per_converter
        vessel.converters_per_fuel = converters_per_fuel


def _usable_fuel_types(vessel: Vessel) -> list[FuelTypeID]:
    """Return the fuel types the tanks store, then those the converters burn."""
    fuel_types: list[FuelTypeID] = []

    for tank in vessel.tanks:
        fuel_types.extend(tank.get_fuel_types())

    for converter in vessel.power_system.get_converters():
        fuel_types.extend(converter.get_fuel_types())

    return unique_list(fuel_types)


def _usable_fuels(
    fuel_types: list[FuelTypeID], fuels_per_fuel_type: dict[FuelTypeID, list[Fuel]]
) -> dict[str, Fuel]:
    """Return the fuels of the given types, keyed by name, type by type."""
    usable_fuels: dict[str, Fuel] = {}

    for fuel_type in fuel_types:
        for fuel in fuels_per_fuel_type[fuel_type]:
            usable_fuels[fuel.name] = fuel

    return usable_fuels


def _fuels_per_converter(
    vessel: Vessel, usable_fuels: dict[str, Fuel]
) -> dict[str, dict[str, Fuel]]:
    """Return, per converter name, the usable fuels of its fuel types."""
    fuels_per_converter: dict[str, dict[str, Fuel]] = {}

    for converter in vessel.power_system.get_converters():
        fuel_types = converter.get_fuel_types()
        burned: dict[str, Fuel] = {}

        for fuel_name, fuel in usable_fuels.items():
            if fuel.fuel_type in fuel_types:
                burned[fuel_name] = fuel

        fuels_per_converter[converter.name] = burned

    return fuels_per_converter


def _converters_per_fuel(
    vessel: Vessel,
    usable_fuels: dict[str, Fuel],
    fuels_per_converter: dict[str, dict[str, Fuel]],
) -> dict[str, dict[str, Converter]]:
    """Return, per usable fuel name, the converters burning it, keyed by name."""
    converters_per_fuel: dict[str, dict[str, Converter]] = {}

    for fuel_name in usable_fuels:
        converters_per_fuel[fuel_name] = {}

    for converter in vessel.power_system.get_converters():
        for fuel_name in fuels_per_converter[converter.name]:
            converters_per_fuel[fuel_name][converter.name] = converter

    return converters_per_fuel


def update_imposed_levies(ports: dict[str, Port], levies: dict[str, Levy]) -> None:
    """
    Write on each port the active levies whose jurisdiction holds that port.

    Parameters
    ----------
    ports
        All ports in the simulation, keyed by name.
    levies
        All levies in the simulation, keyed by name.
    """
    active = [levy for levy in levies.values() if levy.is_active()]

    for port in ports.values():
        port.imposed_levies = [levy for levy in active if port in levy.jurisdiction]
