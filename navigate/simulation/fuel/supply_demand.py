# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Producer development potential, the expected fuel gap and each producer's share."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.util import YEAR, add_dicts

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatLike


def calculate_development_potential(
    producer: Producer, time_step: float, idx: int
) -> None:
    """
    Calculate the development potential of the producer per fuel.

    Parameters
    ----------
    producer
        The producer instance.
    time_step
        Current time-step size, in days.
    idx
        Current time-step index.
    """
    ramp_up = producer.maximum_ramp_up.get() * time_step / YEAR
    utilization = min(producer.current_utilization + ramp_up, 1.0)
    development = producer.maximum_development.get() * time_step / YEAR * utilization

    potential = dict.fromkeys(producer.fuels, 0.0)

    for plant in producer.plants:
        if not producer.allow_plant[plant.name]:
            continue

        multipliers = _limit_by_feed(producer, plant.name, development, idx)
        production = float(plant.expectation.get_production(idx))
        potential[plant.fuel.name] += multipliers * production

    # TODO: can easily loop over export distribution to include shares going to ports
    for key, value in potential.items():
        producer.expectation.set_development_potential(key, value)


def _limit_by_feed(
    producer: Producer, plant_name: str, development: float, idx: int
) -> float:
    """
    Limit the plants a producer can develop to those its constrained feeds can supply.

    Parameters
    ----------
    producer
        The producer instance.
    plant_name
        Name of the plant to develop.
    development
        Number of plants the ramp-up allows the producer to develop over the time step.
    idx
        Current time-step index.

    Returns
    -------
    float
        Number of the plants the producer can develop within its feed constraints.
    """
    expectation = producer.expectation
    limit = development

    for feed_name, constraint in producer.feed_constraints.items():
        if constraint is None:
            continue

        mass = expectation.get_plant_feed_consumption(plant_name, feed_name)

        if mass == 0.0:
            continue

        gap = float(expectation.get_feed_gap(feed_name, idx))
        limit = min(limit, gap / mass)

    return limit


def calculate_expected_fuel_demand(
    fleets: dict[str, Fleet], idx: int
) -> dict[str, FloatLike]:
    """
    Calculate the expected future demand of each fuel across all fleets.

    The demand is the expected bunkering calculated earlier in the time step, so it
    lags the newest fleet evolution. This keeps feedstock availability and bunker
    limits satisfied.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.

    Returns
    -------
    dict[str, FloatLike]
        Expected future demand of each fuel, in tons/year.
    """
    forward = np.s_[idx:]
    demands = [fleet.expectation.get_fuel_demand(forward) for fleet in fleets.values()]
    return add_dicts(*demands)


def calculate_expected_fuel_supply(
    producers: dict[str, Producer], idx: int
) -> dict[str, FloatLike]:
    """
    Calculate the expected future supply of each fuel across all producers.

    Parameters
    ----------
    producers
        All producers in the simulation.
    idx
        Current time-step index.

    Returns
    -------
    dict[str, FloatLike]
        Expected future supply of each fuel, in tons/year.
    """
    forward = np.s_[idx:]
    supply: dict[str, FloatLike] = {}

    for producer in producers.values():
        expectation = producer.expectation

        for plant in producer.plants:
            fuel_name = plant.fuel.name
            production = expectation.get_guaranteed_production(plant.name, forward)
            supply[fuel_name] = supply.get(fuel_name, 0.0) + production

    return supply


def calculate_expected_fuel_gap(
    fuels: dict[str, Fuel],
    supply: dict[str, FloatLike],
    demand: dict[str, FloatLike],
) -> dict[str, FloatLike]:
    """
    Calculate the expected future gap between demand and supply of each fuel.

    Parameters
    ----------
    fuels
        All fuels in the simulation not traded on a liquid market.
    supply
        Expected future supply of each fuel, in tons/year.
    demand
        Expected future demand of each fuel, in tons/year.

    Returns
    -------
    dict[str, FloatLike]
        Expected future demand less supply of each fuel, in tons/year.
    """
    return {name: demand.get(name, 0.0) - supply.get(name, 0.0) for name in fuels}


def calculate_fair_share_demand(
    producers: dict[str, Producer], gap: dict[str, FloatLike], idx: int
) -> None:
    """
    Assign each producer a share of each fuel's gap in proportion to its potential.

    TODO: Can be improved with a regionality aspect

    Parameters
    ----------
    producers
        All producers in the simulation.
    gap
        Expected future gap between demand and supply of each fuel, in tons/year.
    idx
        Current time-step index.
    """
    for fuel_name, fuel_gap in gap.items():
        shares = _calculate_fair_shares(producers, fuel_name)

        for producer_name, share in shares.items():
            producer = producers[producer_name]
            demand = fuel_gap * share
            producer.expectation.set_fair_share_demand(idx, fuel_name, demand)
            producer.results.fair_share_fuel_fraction[fuel_name][idx] = share


def _calculate_fair_shares(
    producers: dict[str, Producer], fuel_name: str
) -> dict[str, float]:
    """
    Calculate each producer's share of the total development potential of a fuel.

    Parameters
    ----------
    producers
        All producers in the simulation.
    fuel_name
        Name of the fuel.

    Returns
    -------
    dict[str, float]
        Share of each producer able to produce the fuel, zero for all when no
        producer has any potential.
    """
    potentials: dict[str, float] = {}

    for name, producer in producers.items():
        if not producer.can_produce(fuel_name):
            continue

        potentials[name] = producer.expectation.get_development_potential(fuel_name)

    total = sum(potentials.values())

    if total == 0.0:
        return dict.fromkeys(potentials, 0.0)

    return {name: potential / total for name, potential in potentials.items()}
