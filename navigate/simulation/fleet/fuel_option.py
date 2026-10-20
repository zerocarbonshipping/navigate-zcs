# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Each vessel's primary fuel type, and the check that its tanks hold what it burns."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.core.enum_ import FuelTypeID
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

    fuel_type_power: defaultdict[FuelTypeID, float] = defaultdict(float)

    for converter in vessel.power_system.get_converters():
        power_capacity = converter.power_capacity.get()

        for fuel_type in converter.main_fuel_types:
            fuel_type_power[fuel_type] += power_capacity

    max_power = max(fuel_type_power.values())
    fuel_types = [key for key, value in fuel_type_power.items() if value == max_power]

    if len(fuel_types) == 1:
        vessel.primary_fuel_type = fuel_types[0]
        return

    vessel.primary_fuel_type = _largest_tank_fuel_type(vessel, fuel_types)

    logger.info(
        "%s: Has a power system with multiple main fuel types (%s) of equal power. "
        "%s was chosen as the primary.",
        vessel,
        _fuel_type_names(fuel_types),
        vessel.primary_fuel_type.name,
    )


def check_fuel_options(vessel: Vessel) -> None:
    """
    Raise where a vessel's tanks cannot store what its converters need to burn.

    A single-fuel converter needs a tank for one of its main fuel types, and a
    dual-fuel converter that must burn a minimum of pilot fuel one for one of its
    pilot fuel types; the vessel needs at least one usable fuel. The minimum pilot
    fuel may be a forecast, so the check runs once its value is precalculated.

    Parameters
    ----------
    vessel
        Vessel whose fuel storage is checked.
    """
    tank_fuel_types: set[FuelTypeID] = set()

    for tank in vessel.tanks:
        tank_fuel_types.update(tank.get_fuel_types())

    for converter in vessel.power_system.get_converters():
        if converter.is_dual_fuel():
            needs_pilot = converter.minimum_pilot_fuel.get() > 0.0

            if needs_pilot and tank_fuel_types.isdisjoint(converter.pilot_fuel_types):
                names = _fuel_type_names(converter.pilot_fuel_types)
                raise ValueError(
                    f"{vessel}: Missing a tank which can store fuel of type(s) "
                    f"{names} required as pilot fuel for {converter}."
                )

        elif tank_fuel_types.isdisjoint(converter.main_fuel_types):
            names = _fuel_type_names(converter.main_fuel_types)
            raise ValueError(
                f"{vessel}: Missing a tank which can store fuel of type(s) "
                f"{names} for {converter}."
            )

    if not vessel.usable_fuels:
        raise ValueError(
            f"{vessel}: No overlap between the fuel types of the PowerSystem,"
            " Tanks and Fuels."
        )


def _largest_tank_fuel_type(vessel: Vessel, fuel_types: list[FuelTypeID]) -> FuelTypeID:
    """
    Pick the fuel type stored in the largest tank, among those a tank stores.

    A tie in tank size keeps the first fuel type.
    """
    tank_sizes: dict[FuelTypeID, float] = {}

    for tank in vessel.tanks:
        size = tank.size.get()

        for fuel_type in tank.get_fuel_types():
            tank_sizes[fuel_type] = size

    stored = [fuel_type for fuel_type in fuel_types if fuel_type in tank_sizes]
    return max(stored, key=lambda fuel_type: tank_sizes[fuel_type])


def _fuel_type_names(fuel_types: list[FuelTypeID]) -> str:
    """Join the names of fuel types for a message."""
    return ", ".join(fuel_type.name for fuel_type in fuel_types)
