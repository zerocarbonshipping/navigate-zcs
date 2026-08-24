# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Determines the fuel options of a vessel from its power system and tanks: the representative fuel
type, the usable fuel types, and the usable fuels, based on the simulation fuels grouped by fuel
type.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from navigate.core.enum_ import FuelTypeID
from navigate.core.nodes.vessel import Vessel
from navigate.util import unique_list

if TYPE_CHECKING:
    from navigate.core.nodes.fuel import Fuel

logger = logging.getLogger(__name__)


def get_fuels_per_fuel_type(fuels: dict[str, Fuel]) -> dict[FuelTypeID, list[Fuel]]:
    """
    Creates a dict of all fuels available for bunkering for each fuel type.

    Parameters
    ----------
    fuels
        All fuels in the simulation, keyed by name.

    Returns
    -------
    Dictionary of bunker fuels linked to a given fuel type.
    """

    # construct dict of fuels per fuel types
    fuel_per_fuel_type = {id_: [] for id_ in FuelTypeID}

    for fuel in fuels.values():

        fuel_type = fuel.fuel_type
        fuel_per_fuel_type[fuel_type].append(fuel)

    return fuel_per_fuel_type


def determine_fuel_type(vessel: Vessel) -> None:
    """
    Determines the representative fuel type of a vessel based on the sum of power capacity for the main fuel types
    across all converters in the power system. If multiple fuel types have the same power capacity, the one
    with the largest tank is chosen.

    TODO: The tank size should optimally be weighted by the LHV, but it might vary within a given fuel type

    Parameters
    ----------
    vessel
        Vessel to determine the representative fuel type for; skipped if already set through the DSL.
    """

    if vessel.fuel_type is not None:
        return

    power_system = vessel.power_system
    fuel_type_power = {}

    for converter in power_system.get_converters():

        main_fuel_types = converter.main_fuel_types
        power_capacity = converter.power_capacity.get()

        for fuel_type in main_fuel_types:

            if fuel_type in fuel_type_power:

                fuel_type_power[fuel_type] += power_capacity

            else:

                fuel_type_power[fuel_type] = power_capacity

    # reverse the list
    power_capacities = unique_list(fuel_type_power.values())
    power_fuel_type = {}

    for power in power_capacities:
        power_fuel_type[power] = [key for key, value in fuel_type_power.items() if value == power]

    # find the fuel types with the highest power
    max_power = max(power_capacities)

    if len(power_fuel_type[max_power]) > 1:

        # if multiple fuel types with same power
        # base the primary type on the tank size
        tanks = vessel.tanks
        fuel_type_size = {fuel_type: tank.size.get() for tank in tanks for fuel_type in tank.get_fuel_types()}

        # reduce the list of possibly fuel types
        usable_fuel_types = [fuel_type for fuel_type in power_fuel_type[max_power] if fuel_type in fuel_type_size]
        fuel_type = usable_fuel_types[0]

        for type_ in usable_fuel_types:

            if type_ not in fuel_type_size:
                continue

            # notice that if multiple tanks have the same size
            # the first encountered fuel type is chosen
            if fuel_type_size[type_] > fuel_type_size[fuel_type]:
                fuel_type = type_

        logger.info("{}: Has a power system with multiple main fuel types "
                    "({}) of equal power. {} was chosen as the primary."
                    .format(vessel,
                            ', '.join([FuelTypeID(f).name for f in power_fuel_type[max_power]]),
                            FuelTypeID(fuel_type).name))

    else:

        fuel_type = power_fuel_type[max_power][0]

    vessel.fuel_type = fuel_type


def determine_usable_fuel_types(vessel: Vessel) -> None:
    """
    Determines the fuel types usable by a vessel as the union of tank and converter fuel types, after checking
    that the tanks can store the fuels required by the converters.

    Parameters
    ----------
    vessel
        Vessel to determine the usable fuel types for; skipped if already determined.
    """

    if vessel.usable_fuel_types:
        return

    tank_fuel_types = [fuel_type for tank in vessel.tanks for fuel_type in tank.get_fuel_types()]

    power_system_fuel_types = [fuel_type for converter in vessel.power_system.get_converters()
                               for fuel_type in converter.get_fuel_types()]

    # check the tanks allow for storage of fuels used in the converters
    for converter in vessel.power_system.get_converters():

        main_fuel_types = converter.main_fuel_types
        pilot_fuel_types = converter.pilot_fuel_types

        if converter.is_dual_fuel():

            if converter.minimum_pilot_fuel.get() > 0.:

                if not any((fuel_type in tank_fuel_types for fuel_type in pilot_fuel_types)):
                    raise ValueError("{}: Missing a tank which can store fuel of"
                                     " type(s) {} required as pilot fuel for {}."
                                     .format(vessel,
                                             ', '.join(FuelTypeID(f).name for f in pilot_fuel_types),
                                             converter))

        else:
            if not any((fuel_type in tank_fuel_types for fuel_type in main_fuel_types)):
                raise ValueError("{}: Missing a tank which can store fuel of type(s) {} for {}."
                                 .format(vessel, ', '.join(FuelTypeID(f).name for f in main_fuel_types), converter))

    vessel.usable_fuel_types = unique_list(tank_fuel_types + power_system_fuel_types)


def determine_usable_fuels(vessel: Vessel, fuels_by_fuel_type: dict[FuelTypeID, list[Fuel]]) -> None:
    """
    Determines the fuels usable by a vessel from its usable fuel types.

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

            vessel.usable_fuels.setdefault(fuel.get_name(), fuel)

    # check that the vessel can bunker
    if not vessel.usable_fuels:
        raise ValueError("{}: No overlap between the fuel types of the PowerSystem, Tanks and Fuels.".format(vessel))
