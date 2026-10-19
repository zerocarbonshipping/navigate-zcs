# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The results of the port, plant, producer and global profiles, from what was written.

The time steps write masses and emissions per ton of fuel. Once a profile holds its
final values, they are converted to energy and CO2-equivalents.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.core.profiles import (
        GlobalProfile,
        PlantProfile,
        PortProfile,
        ProducerProfile,
    )


def complete_port_profile(profile: PortProfile) -> None:
    """
    Write the results of a port profile computed from its written ones.

    Parameters
    ----------
    profile
        Port profile, written for the whole run.
    """
    _complete_fuel_infrastructure(profile)
    profile.equivalent_bunker_wtt = profile.context.equivalent(profile.bunker_wtt)


def complete_plant_profile(profile: PlantProfile) -> None:
    """
    Write the results of a plant profile computed from its written ones.

    Parameters
    ----------
    profile
        Plant profile, written for the whole run.
    """
    context = profile.context

    profile.equivalent_investment_wtt = context.equivalent_by_emission(
        profile.investment_wtt
    )
    profile.equivalent_instantaneous_wtt = context.equivalent_by_emission(
        profile.instantaneous_wtt
    )


def complete_producer_profile(profile: ProducerProfile) -> None:
    """
    Write the results of a producer profile computed from its written ones.

    Parameters
    ----------
    profile
        Producer profile, written for the whole run.
    """
    _complete_fuel_producer(profile)


def complete_global_fuel_results(profile: GlobalProfile) -> None:
    """
    Write the fuel results of the global profile computed from its written ones.

    Parameters
    ----------
    profile
        Global profile, the ports and producers summed into it.
    """
    _complete_fuel_infrastructure(profile)
    _complete_fuel_producer(profile)


def _complete_fuel_infrastructure(profile: PortProfile | GlobalProfile) -> None:
    context = profile.context

    profile.bunker_energy = context.energy(profile.bunker_mass)
    profile.bunker_supply_energy = context.energy(profile.bunker_supply_mass)
    profile.bunkering_limit_energy = context.energy(profile.bunkering_limit_mass)


def _complete_fuel_producer(profile: ProducerProfile | GlobalProfile) -> None:
    context = profile.context

    profile.production_energy = context.energy(profile.production_mass)
    profile.production_type_energy = context.fuel_type_energy(profile.production_mass)
