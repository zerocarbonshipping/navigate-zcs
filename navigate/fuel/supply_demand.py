# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Expected fuel supply, demand and gap, and each producer's share of the gap."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.util import YEAR, add_dicts

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatLike


def calculate_constrained_fair_share_fuel_demand(
    fuels: dict[str, Fuel],
    producers: dict[str, Producer],
    gap: dict[str, FloatLike],
    idx: int,
) -> None:
    """
    Assign each constrained producer a fair share of its fuels' supply gap.

    TODO: Can be improved with a regionality aspect

    Parameters
    ----------
    fuels
        All fuels in the simulation not belonging to a liquid market.
    producers
        All constrained producers in the simulation.
    gap
        The expected future gap between fuel supply and demand for each fuel pathway,
        tons/year.
    idx
        Current time-step index.
    """
    total_potentials = dict.fromkeys(fuels, 0.0)

    for fuel_name in fuels:
        for producer in producers.values():
            if not producer.can_produce(fuel_name):
                continue

            total_potentials[fuel_name] += (
                producer.expectation.get_development_potential(fuel_name)
            )

    fair_share = {
        (producer_name, fuel_name): 0.0
        for fuel_name in fuels
        for producer_name in producers
    }

    for fuel_name, total_potential in total_potentials.items():
        if total_potential == 0.0:
            continue

        for producer_name, producer in producers.items():
            if not producer.can_produce(fuel_name):
                continue

            potential = producer.expectation.get_development_potential(fuel_name)
            fair_share[(producer_name, fuel_name)] += potential / total_potential

    _assign_fair_share_of_gap(producers, fair_share, gap, idx)


def calculate_fuel_supply_demand_gap(
    fuels: dict[str, Fuel],
    supply: dict[str, FloatLike],
    demand: dict[str, FloatLike],
) -> dict[str, FloatLike]:
    """
    Calculate the expected future gap between supply and demand of each fuel pathway.

    Parameters
    ----------
    fuels
        All fuels in the simulation.
    supply
        The sum of expected future fuel supply for all fuel pathways, tons/year.
    demand
        The sum of expected future fuel demand for all fuel pathways, tons/year.

    Returns
    -------
    dict[str, FloatLike]
        The expected future gap between fuel supply and demand for each fuel pathway,
        tons/year.
    """
    gap: dict[str, FloatLike] = {}

    for fuel_name, fuel in fuels.items():
        if fuel.liquid_market:
            continue

        gap.setdefault(fuel_name, 0.0)

        if fuel_name in demand:
            gap[fuel_name] += demand[fuel_name]

        if fuel_name in supply:
            gap[fuel_name] -= supply[fuel_name]

    return gap


def calculate_expected_fuel_demand(
    fleets: dict[str, Fleet], idx: int
) -> dict[str, FloatLike]:
    """
    Calculate the expected future demand of each fuel pathway across all fleets.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.

    Returns
    -------
    dict[str, FloatLike]
        The sum of expected future fuel demand for all fuel pathways, tons/year.
    """
    return add_dicts(
        *(
            _calculate_expected_fleet_fuel_demand(fleet, idx)
            for fleet in fleets.values()
        )
    )


def calculate_expected_fuel_supply(
    producers: dict[str, Producer], idx: int
) -> dict[str, FloatLike]:
    """
    Calculate the expected future supply of each fuel pathway across all producers.

    Parameters
    ----------
    producers
        All producers in the simulation.
    idx
        Current time-step index.

    Returns
    -------
    dict[str, FloatLike]
        The sum of expected future fuel supply for all fuel pathways, tons/year.
    """
    return add_dicts(
        *(
            _calculate_expected_producer_fuel_supply(producer, idx)
            for producer in producers.values()
        )
    )


def calculate_development_potential(
    producer: Producer, time_step: float, idx: int
) -> None:
    """
    Calculate the development potential of the producer per fuel type.

    Parameters
    ----------
    producer
        The producer instance.
    time_step
        Current time-step size, days.
    idx
        Current time-step index.
    """
    maximum_development = producer.maximum_development.get() * time_step / YEAR
    ramp_up = producer.maximum_ramp_up.get() * time_step / YEAR
    utilization = min(producer.current_utilization + ramp_up, 1.0)
    maximum_development *= utilization

    potential = dict.fromkeys(producer.fuels, 0.0)

    for plant in producer.assets:
        plant_name = plant.name
        fuel_name = plant.fuel.name
        production = float(plant.expectation.get_production(idx))

        uptake = 1.0 if producer.allow_plant[plant_name] else 0.0
        plant_potential = uptake * maximum_development

        for feed_name, constraint in producer.feed_constraints.items():
            if constraint is None:
                continue

            mass = producer.expectation.get_plant_feed_consumption(
                plant_name, feed_name
            )

            if mass == 0.0:
                continue

            gap = float(producer.expectation.get_feed_gap(feed_name, idx))
            potential_multipliers = uptake * gap / mass

            if potential_multipliers < plant_potential:
                plant_potential = potential_multipliers

        potential[fuel_name] += plant_potential * production

    for fuel_name in producer.fuels:
        # TODO: can easily loop over export distribution to include shares going to
        # ports
        producer.expectation.set_development_potential(fuel_name, potential[fuel_name])


def _assign_fair_share_of_gap(
    producers: dict[str, Producer],
    fair_share: dict[tuple[str, str], float],
    gap: dict[str, FloatLike],
    idx: int,
) -> None:
    """
    Assign fair-share of the supply/demand gap of a fuel pathway to producers.

    Parameters
    ----------
    producers
        Either all constrained producers or all unconstrained producers in the
        simulation.
    fair_share
        Fair-share of the supply/demand gap per producer and fuel.
    gap
        The expected future gap between fuel supply and demand for each fuel pathway,
        tons/year.
    idx
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


def _calculate_expected_producer_fuel_supply(
    producer: Producer, idx: int
) -> dict[str, FloatLike]:
    """
    Calculate the future supply of each fuel pathway across all plants of the producer.

    Parameters
    ----------
    producer
        Producer for which fuel production is calculated.
    idx
        Current time-step index.

    Returns
    -------
    dict[str, FloatLike]
        The sum of expected future fuel production from the producer for each fuel
        pathway, tons/year.
    """
    idx_ = np.s_[idx:]

    expectation = producer.expectation
    supply: dict[str, FloatLike] = {}

    for plant in producer.plants:
        plant_name = plant.name
        fuel_name = plant.fuel.name

        supply.setdefault(fuel_name, 0.0)
        supply[fuel_name] += expectation.get_guaranteed_production(plant_name, idx=idx_)

    return supply


def _calculate_expected_fleet_fuel_demand(
    fleet: Fleet, idx: int
) -> dict[str, FloatLike]:
    """
    Calculate future demand of each fuel pathway across all vessel of a single fleet.

    Notice that the demand is taken directly from the expected bunkering calculated
    previously in the time-step. This means that it does not account for the newest
    fleet evolution but rather a time-lagged view on the expected multipliers. This is
    necessary to ensure potential feedstock availability and bunker limits are
    satisfied.

    Parameters
    ----------
    fleet
        Fleet for which demand is being calculated.
    idx
        Current time-step index.

    Returns
    -------
    dict[str, FloatLike]
        The sum of expected future fuel consumption from the fleet for each fuel
        pathway, tons/year.
    """
    return fleet.expectation.get_fuel_demand(np.s_[idx:])
