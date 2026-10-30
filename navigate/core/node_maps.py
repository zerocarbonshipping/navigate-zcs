# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Node maps: node attributes derived from other nodes', written once or each step."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import PORT_ENERGY_DEMANDS, FuelTypeID
from navigate.util import unique_list

if TYPE_CHECKING:
    from collections.abc import Mapping

    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.levy import Levy
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.producer import Producer
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel


def define_vessel_fuel_maps(vessels: dict[str, Vessel], fuels: dict[str, Fuel]) -> None:
    """
    Write on each vessel its usable fuels and its tank-fuel and converter-fuel pairs.

    A usable fuel type is one a tank stores or a converter burns, and a usable fuel
    is a fuel of a usable type. Each tank is paired with the fuels of its fuel types,
    type by type. Each converter is paired with the usable fuels of its fuel types,
    in usable-fuel order, and each usable fuel with the converters burning it, in
    converter order; a fuel only a tank stores has no converter. The port pairs keep
    only the converters serving port energy demands, in that demand order.

    Parameters
    ----------
    vessels
        All vessels in the simulation, keyed by name.
    fuels
        All fuels in the simulation, keyed by name.
    """
    fuels_per_fuel_type = _fuels_per_fuel_type(fuels)

    for vessel in vessels.values():
        usable_fuel_types = _usable_fuel_types(vessel)
        usable_fuels = _fuels_of_types(usable_fuel_types, fuels_per_fuel_type)
        per_tank = _fuels_per_tank(vessel, fuels_per_fuel_type)
        per_converter = _fuels_per_converter(vessel, usable_fuels)
        per_fuel = _converters_per_fuel(vessel, usable_fuels, per_converter)
        per_port_converter = _fuels_per_port_converter(vessel, per_converter)
        port_per_fuel = _port_converters_per_fuel(per_fuel, per_port_converter)

        vessel.usable_fuels = usable_fuels
        vessel.fuels_per_tank = per_tank
        vessel.fuels_per_converter = per_converter
        vessel.converters_per_fuel = per_fuel
        vessel.fuels_per_port_converter = per_port_converter
        vessel.port_converters_per_fuel = port_per_fuel


def _fuels_per_fuel_type(fuels: dict[str, Fuel]) -> dict[FuelTypeID, list[Fuel]]:
    """Return the fuels per fuel type in input order, every fuel type a key."""
    fuels_per_fuel_type: dict[FuelTypeID, list[Fuel]] = {id_: [] for id_ in FuelTypeID}

    for fuel in fuels.values():
        fuels_per_fuel_type[fuel.fuel_type].append(fuel)

    return fuels_per_fuel_type


def _usable_fuel_types(vessel: Vessel) -> list[FuelTypeID]:
    """Return the fuel types the tanks store, then those the converters burn."""
    fuel_types: list[FuelTypeID] = []

    for tank in vessel.tanks:
        fuel_types.extend(tank.fuel_types)

    for converter in vessel.get_converters():
        fuel_types.extend(converter.get_fuel_types())

    return unique_list(fuel_types)


def _fuels_of_types(
    fuel_types: list[FuelTypeID], fuels_per_fuel_type: dict[FuelTypeID, list[Fuel]]
) -> dict[str, Fuel]:
    """Return the fuels of the given types, keyed by name, type by type."""
    fuels: dict[str, Fuel] = {}

    for fuel_type in fuel_types:
        for fuel in fuels_per_fuel_type[fuel_type]:
            fuels[fuel.name] = fuel

    return fuels


def _fuels_per_tank(
    vessel: Vessel, fuels_per_fuel_type: dict[FuelTypeID, list[Fuel]]
) -> dict[str, dict[str, Fuel]]:
    """Return, per tank name, the fuels of its fuel types."""
    fuels_per_tank: dict[str, dict[str, Fuel]] = {}

    for tank in vessel.tanks:
        stored = _fuels_of_types(tank.fuel_types, fuels_per_fuel_type)
        fuels_per_tank[tank.name] = stored

    return fuels_per_tank


def _fuels_per_converter(
    vessel: Vessel, usable_fuels: dict[str, Fuel]
) -> dict[str, dict[str, Fuel]]:
    """Return, per converter name, the usable fuels of its fuel types."""
    fuels_per_converter: dict[str, dict[str, Fuel]] = {}

    for converter in vessel.get_converters():
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

    for converter in vessel.get_converters():
        for fuel_name in fuels_per_converter[converter.name]:
            converters_per_fuel[fuel_name][converter.name] = converter

    return converters_per_fuel


def _fuels_per_port_converter(
    vessel: Vessel, fuels_per_converter: dict[str, dict[str, Fuel]]
) -> dict[str, dict[str, Fuel]]:
    """Return, per name of a converter serving port demands, its usable fuels."""
    fuels_per_port_converter: dict[str, dict[str, Fuel]] = {}

    for demand_type in PORT_ENERGY_DEMANDS:
        name = vessel.get_converter(demand_type).name
        fuels_per_port_converter[name] = fuels_per_converter[name]

    return fuels_per_port_converter


def _port_converters_per_fuel(
    converters_per_fuel: dict[str, dict[str, Converter]],
    fuels_per_port_converter: dict[str, dict[str, Fuel]],
) -> dict[str, dict[str, Converter]]:
    """Return, per usable fuel name, the converters burning it that serve in port."""
    port_converters_per_fuel: dict[str, dict[str, Converter]] = {}

    for fuel_name, converters in converters_per_fuel.items():
        in_port: dict[str, Converter] = {}

        for converter_name, converter in converters.items():
            if converter_name in fuels_per_port_converter:
                in_port[converter_name] = converter
        port_converters_per_fuel[fuel_name] = in_port

    return port_converters_per_fuel


def define_fuel_plants(fuels: dict[str, Fuel], plants: dict[str, Plant]) -> None:
    """
    Write on each fuel the plants producing it, in plant order.

    Parameters
    ----------
    fuels
        All fuels in the simulation, keyed by name.
    plants
        All plants in the simulation, keyed by name.
    """
    for fuel in fuels.values():
        fuel.plants = []

    for plant in plants.values():
        plant.fuel.plants.append(plant)


def define_producer_fuels(producers: dict[str, Producer]) -> None:
    """
    Write on each producer the fuels its plants produce, in plant order.

    Parameters
    ----------
    producers
        All producers in the simulation, keyed by name.
    """
    for producer in producers.values():
        fuels: dict[str, Fuel] = {}

        for plant in producer.plants:
            fuels.setdefault(plant.fuel.name, plant.fuel)

        producer.fuels = fuels


def define_vessels_in_jurisdiction(
    policies: Mapping[str, Levy | Regulation], vessels: dict[str, Vessel]
) -> None:
    """
    Write on each policy whether each vessel's route calls at a port it governs.

    Parameters
    ----------
    policies
        All levies or all regulations in the simulation, keyed by name.
    vessels
        All vessels in the simulation, keyed by name.
    """
    for policy in policies.values():
        jurisdiction = set(policy.jurisdiction)
        in_jurisdiction_vessel: dict[str, bool] = {}

        for vessel_name, vessel in vessels.items():
            in_jurisdiction = not jurisdiction.isdisjoint(vessel.route.ports)
            in_jurisdiction_vessel[vessel_name] = in_jurisdiction

        policy.in_jurisdiction_vessel = in_jurisdiction_vessel


def update_bunkerable_fuels(vessels: dict[str, Vessel]) -> None:
    """
    Write on each vessel, per route stop, the usable fuels the stop's port allows.

    Each stop keeps the vessel's usable-fuel order.

    Parameters
    ----------
    vessels
        All vessels in the simulation, keyed by name.
    """
    for vessel in vessels.values():
        bunkerable_fuels: list[dict[str, Fuel]] = []

        for port in vessel.route.ports:
            allowed: dict[str, Fuel] = {}

            for fuel_name, fuel in vessel.usable_fuels.items():
                if port.bunkering_allowed[fuel_name]:
                    allowed[fuel_name] = fuel
            bunkerable_fuels.append(allowed)

        vessel.bunkerable_fuels = bunkerable_fuels


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
    active = [levy for levy in levies.values() if levy.active]

    for port in ports.values():
        port.imposed_levies = [levy for levy in active if port in levy.jurisdiction]
