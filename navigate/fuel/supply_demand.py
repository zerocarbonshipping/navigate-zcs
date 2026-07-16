# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.util import add_dicts


def calculate_constrained_fair_share_fuel_demand(fuels, producers, gap, idx):
    """

    TODO: Can be improved with a regionality aspect

    Parameters
    ----------
    fuels : dict[str, Fuel]
        All fuels in the simulation not belonging to a liquid market.
    producers : dict[str, Producer]
        All constrained producers in the simulation.
    gap : dict[str, np.ndarray]
        The expected future gap between fuel supply and demand for each fuel pathway.
    idx : int
        Current time-step index.
    """

    # calculate the total potential of each fuel
    total_potentials = {fuel_name: 0. for fuel_name in fuels}

    for fuel_name in fuels:

        for producer in producers.values():

            if not producer.can_produce(fuel_name):
                continue

            total_potentials[fuel_name] += producer.expectation.get_development_potential(fuel_name)

    # calculate the fair-share out of the total potential
    fair_share = {(producer_name, fuel_name): 0. for fuel_name in fuels for producer_name in producers}

    for fuel_name, total_potential in total_potentials.items():

        if total_potential == 0.:
            continue

        for producer_name, producer in producers.items():

            if not producer.can_produce(fuel_name):
                continue

            potential = producer.expectation.get_development_potential(fuel_name)
            fair_share[(producer_name, fuel_name)] += potential / total_potential

    # assign a fair-share of fuel production to each producer
    _assign_fair_share_of_gap(producers, fair_share, gap, idx)


def calculate_fuel_supply_demand_gap(fuels, supply, demand):
    """
    Calculate the expected future gap between supply and demand of each fuel pathway.

    Parameters
    ----------
    fuels : dict[str, Fuel]
        All fuels in the simulation.
    supply : dict[str, np.ndarray]
        The sum of expected future fuel supply for all fuel pathways.
    demand : dict[str, np.ndarray]
        The sum of expected future fuel demand for all fuel pathways.

    Returns
    -------
    dict[str, np.ndarray]
        The expected future gap between fuel supply and demand for each fuel pathway.
    """

    # calculate the expected supply-demand
    # gap between the fuels
    gap = {}
    for fuel_name, fuel in fuels.items():

        if fuel.belongs_to_liquid_market():
            continue

        gap.setdefault(fuel_name, 0.)

        if fuel_name in demand:
            gap[fuel_name] += demand[fuel_name]

        if fuel_name in supply:
            gap[fuel_name] -= supply[fuel_name]

    return gap


def calculate_expected_fuel_demand(fleets, idx):
    """
    Calculate the expected future demand of each fuel pathway across all fleets.

    Parameters
    ----------
    fleets : dict[str, Fleet]
        All fleets in the simulation.
    idx : int
        Current time-step index.

    Returns
    -------
    dict[str, np.ndarray]
        The sum of expected future fuel demand for all fuel pathways.
    """

    return add_dicts(*(_calculate_expected_fleet_fuel_demand(fleet, idx) for fleet in fleets.values()))


def calculate_expected_fuel_supply(producers, idx):
    """
    Calculate the expected future supply of each fuel pathway across all producers.

    Parameters
    ----------
    producers : dict[str, Producer]
        All producers in the simulation.
    idx : int
        Current time-step index.

    Returns
    -------
    dict[str, np.ndarray]
        The sum of expected future fuel supply for all fuel pathways.
    """

    if not producers:
        return {}

    return add_dicts(*(_calculate_expected_producer_fuel_supply(producer, idx) for producer in producers.values()))


def _assign_fair_share_of_gap(producers, fair_share, gap, idx):
    """
    Assign fair-share of the supply/demand gap of a fuel pathway to producers.

    Parameters
    ----------
    producers : dict[str, Producer]
        Either all constrained producers or all unconstrained producers in the simulation.
    fair_share : dict[(str, str), float]
        Fair-share of the supply/demand gap.
    gap : dict[str, np.ndarray]
        The expected future gap between fuel supply and demand for each fuel pathway.
    idx : int
        Current time-step index.
    """

    for producer_name, producer in producers.items():

        expectation = producer.expectation
        profile = producer.profile

        for fuel_name in gap:

            if not producer.can_produce(fuel_name):
                continue

            key = (producer_name, fuel_name)
            demand_share = gap[fuel_name] * fair_share[key]
            expectation.set_fair_share_demand(idx, fuel_name, demand_share)
            profile.set_fair_share_fuel_fraction(idx, fuel_name, fair_share[key])


def _calculate_expected_producer_fuel_supply(producer, idx):
    """
    Calculate the expected future supply of each fuel pathway across all plants of the producer.

    Parameters
    ----------
    producer : Producer
        Producer for which fuel production is calculated.
    idx : int
        Current time-step index.

    Returns
    -------
    dict[str, np.ndarray]
        The sum of expected future fuel production from the producer for each fuel pathway.
    """

    idx_ = np.s_[idx:]

    expectation = producer.expectation
    supply = {}

    for plant in producer.get_plants():

        plant_name = plant.get_name()
        fuel_name = plant.fuel.get_name()

        supply.setdefault(fuel_name, 0.)
        supply[fuel_name] += expectation.get_guaranteed_production(plant_name, idx=idx_)

    return supply


def _calculate_expected_fleet_fuel_demand(fleet, idx):
    """
    Calculate the expected future demand of each fuel pathway across all vessel of a single fleet.

    Notice that the demand is taken directly from the expected bunkering calculated previously in the time-step.
    This means that it does not account for the newest fleet evolution but rather a time-lagged view on the expected
    multipliers. This is necessary to ensure potential feedstock availability and bunker limits are satisfied.

    Parameters
    ----------
    fleet : Fleet
        Fleet for which demand is being calculated.
    idx : int
        Current time-step index.

    Returns
    -------
    dict[str, np.ndarray]
        The sum of expected future fuel consumption from the fleet for each fuel pathway.
    """

    return fleet.expectation.get_fuel_demand(np.s_[idx:])
