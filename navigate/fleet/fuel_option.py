# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Primary fuel type, usable fuel types and usable fuels of each vessel."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from navigate.core.enum_ import FuelTypeID
from navigate.util import unique_list

if TYPE_CHECKING:
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.vessel import Vessel

logger = logging.getLogger(__name__)


def determine_fuel_type(vessel: Vessel) -> None:
    """
    Set a vessel's primary fuel type, the one every reader takes as its fuel type.

    The fuel type assigned through the DSL wins. Otherwise it is the main fuel type
    with the largest power capacity summed across all converters in the power
    system; a tie between fuel types is broken by the size of the tanks that store
    them.

    TODO: The tank size should optimally be weighted by the LHV, but it might vary
    within a given fuel type

    Parameters
    ----------
    vessel
        Vessel to set the primary fuel type on.
    """
    if vessel.fuel_type is not None:
        vessel.primary_fuel_type = vessel.fuel_type
        return

    power_system = vessel.power_system
    fuel_type_power: dict[FuelTypeID, float] = {}

    for converter in power_system.get_converters():
        main_fuel_types = converter.main_fuel_types
        power_capacity = converter.power_capacity.get()

        for fuel_type in main_fuel_types:
            if fuel_type in fuel_type_power:
                fuel_type_power[fuel_type] += power_capacity

            else:
                fuel_type_power[fuel_type] = power_capacity

    # invert the mapping to the fuel types of each power capacity
    power_capacities = unique_list(fuel_type_power.values())
    power_fuel_type = {}

    for power in power_capacities:
        power_fuel_type[power] = [
            key for key, value in fuel_type_power.items() if value == power
        ]

    max_power = max(power_capacities)

    if len(power_fuel_type[max_power]) > 1:
        # a tie in power capacity is broken by the tank size
        tanks = vessel.tanks
        fuel_type_size = {
            fuel_type: tank.size.get()
            for tank in tanks
            for fuel_type in tank.get_fuel_types()
        }

        usable_fuel_types = [
            fuel_type
            for fuel_type in power_fuel_type[max_power]
            if fuel_type in fuel_type_size
        ]
        fuel_type = usable_fuel_types[0]

        for type_ in usable_fuel_types:
            if type_ not in fuel_type_size:
                continue

            # a tie in tank size keeps the first fuel type
            if fuel_type_size[type_] > fuel_type_size[fuel_type]:
                fuel_type = type_

        logger.info(
            "%s: Has a power system with multiple main fuel types (%s) of equal power. "
            "%s was chosen as the primary.",
            vessel,
            ", ".join([FuelTypeID(f).name for f in power_fuel_type[max_power]]),
            FuelTypeID(fuel_type).name,
        )

    else:
        fuel_type = power_fuel_type[max_power][0]

    vessel.primary_fuel_type = fuel_type


def determine_usable_fuel_types(vessel: Vessel) -> None:
    """
    Determine a vessel's usable fuel types.

    The usable types are the union of tank and converter fuel types, after
    checking that the tanks can store the fuels required by the converters.

    Parameters
    ----------
    vessel
        Vessel to determine the usable fuel types for; skipped if already determined.
    """
    if vessel.usable_fuel_types:
        return

    tank_fuel_types = [
        fuel_type for tank in vessel.tanks for fuel_type in tank.get_fuel_types()
    ]

    power_system_fuel_types = [
        fuel_type
        for converter in vessel.power_system.get_converters()
        for fuel_type in converter.get_fuel_types()
    ]

    for converter in vessel.power_system.get_converters():
        main_fuel_types = converter.main_fuel_types
        pilot_fuel_types = converter.pilot_fuel_types

        if converter.is_dual_fuel():
            if converter.minimum_pilot_fuel.get() > 0.0 and not any(
                fuel_type in tank_fuel_types for fuel_type in pilot_fuel_types
            ):
                raise ValueError(
                    "{}: Missing a tank which can store fuel of"
                    " type(s) {} required as pilot fuel for {}.".format(
                        vessel,
                        ", ".join(FuelTypeID(f).name for f in pilot_fuel_types),
                        converter,
                    )
                )

        else:
            if not any(fuel_type in tank_fuel_types for fuel_type in main_fuel_types):
                raise ValueError(
                    "{}: Missing a tank which can store fuel of type(s) {} for"
                    " {}.".format(
                        vessel,
                        ", ".join(FuelTypeID(f).name for f in main_fuel_types),
                        converter,
                    )
                )

    vessel.usable_fuel_types = unique_list(tank_fuel_types + power_system_fuel_types)


def determine_usable_fuels(
    vessel: Vessel, fuels_by_fuel_type: dict[FuelTypeID, list[Fuel]]
) -> None:
    """
    Determine the fuels usable by a vessel from its usable fuel types.

    Parameters
    ----------
    vessel
        Vessel to determine the usable fuels for.
    fuels_by_fuel_type
        All fuels in the simulation grouped by fuel type.
    """
    for fuel_type in vessel.usable_fuel_types:
        fuels = fuels_by_fuel_type[fuel_type]

        for fuel in fuels:
            vessel.usable_fuels.setdefault(fuel.name, fuel)

    if not vessel.usable_fuels:
        raise ValueError(
            f"{vessel}: No overlap between the fuel types of the PowerSystem,"
            " Tanks and Fuels."
        )
