# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The port, plant, producer and global results computed after the run.

The time steps write masses and emissions per ton of fuel. Once the results hold their
final values, they are converted to energy and CO2-equivalents.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.core.results import (
        GlobalResults,
        PlantResults,
        PortResults,
        ProducerResults,
    )


def complete_port_results(results: PortResults) -> None:
    """
    Write the port results computed from the written ones.

    Parameters
    ----------
    results
        Port results, written for the whole run.
    """
    _complete_fuel_infrastructure(results)
    results.equivalent_bunker_wtt = results.context.equivalent(results.bunker_wtt)


def complete_plant_results(results: PlantResults) -> None:
    """
    Write the plant results computed from the written ones.

    Parameters
    ----------
    results
        Plant results, written for the whole run.
    """
    context = results.context

    investment = context.equivalent_by_emission(results.investment_wtt)
    instantaneous = context.equivalent_by_emission(results.instantaneous_wtt)

    results.equivalent_investment_wtt = investment
    results.equivalent_instantaneous_wtt = instantaneous


def complete_producer_results(results: ProducerResults) -> None:
    """
    Write the producer results computed from the written ones.

    Parameters
    ----------
    results
        Producer results, written for the whole run.
    """
    _complete_fuel_producer(results)


def complete_global_fuel_results(results: GlobalResults) -> None:
    """
    Write the global fuel results computed from the written ones.

    Parameters
    ----------
    results
        Global results, the ports and producers summed into them.
    """
    _complete_fuel_infrastructure(results)
    _complete_fuel_producer(results)


def _complete_fuel_infrastructure(results: PortResults | GlobalResults) -> None:
    context = results.context

    results.bunker_energy = context.energy(results.bunker_mass)
    results.bunker_supply_energy = context.energy(results.bunker_supply_mass)
    results.bunkering_limit_energy = context.energy(results.bunkering_limit_mass)


def _complete_fuel_producer(results: ProducerResults | GlobalResults) -> None:
    context = results.context

    results.production_energy = context.energy(results.production_mass)
    results.production_type_energy = context.fuel_type_energy(results.production_mass)
