# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Producer development potential, the expected fuel gap and each producer's share."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.fuel.port_supply import calculate_guaranteed_bunker_supply
from navigate.util import add_dicts, subtract

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray, FloatLike


def calculate_development_potential(
    producer: Producer, time_step: float, idx: int
) -> None:
    """
    Calculate the development potential of the producer per fuel.

    Parameters
    ----------
    producer
        The producer.
    time_step
        Current time-step size, in years.
    idx
        Current time-step index.
    """
    development = producer.maximum_development.get() * time_step

    potential = dict.fromkeys(producer.fuels, 0.0)

    for plant in producer.plants:
        if not producer.allow_plants[plant.name]:
            continue

        newbuilds = _calculate_feasible_newbuilds(producer, plant, development, idx)

        # a Python float, as a builtin sum() adds up the development potentials
        production = float(plant.expectation.production[idx])
        potential[plant.fuel.name] += newbuilds * production

    # TODO: can easily loop over export shares to include shares going to ports
    for key, value in potential.items():
        producer.expectation.development_potential[key] = value


def _calculate_feasible_newbuilds(
    producer: Producer, plant: Plant, development: float, idx: int
) -> float:
    """
    Calculate the plants a producer can develop that its constrained feeds can supply.

    Parameters
    ----------
    producer
        The producer.
    plant
        Plant type to develop.
    development
        Number of plants the producer may develop over the time step.
    idx
        Current time-step index.

    Returns
    -------
    float
        Number of the plants the producer can develop within its feed constraints.
    """
    expectation = producer.expectation
    newbuilds = development

    for feed_name, limit in producer.feed_limits.items():
        if limit is None:
            continue

        consumption = expectation.plant_feed_consumption[plant.name, feed_name]

        if consumption == 0.0:
            continue

        # a Python float, as the newbuilds reach the builtin sum() of the potentials
        gap = float(expectation.feed_gap[feed_name][idx])
        newbuilds = min(newbuilds, gap / consumption)

    return newbuilds


def calculate_fair_share_demand(
    producers: dict[str, Producer],
    fleets: dict[str, Fleet],
    ports: dict[str, Port],
    fuels: dict[str, Fuel],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Assign each producer a share of each fuel's expected gap by its potential.

    The gap of a fuel is the sum of the ports' shortfalls: at each port, the fleets'
    expected demand for the fuel less the supply guaranteed production brings there,
    where the demand is the larger. A producer exports to the ports by fixed shares,
    so the supply a port holds beyond its demand is stranded there and serves no
    other port's shortfall.

    The demand is the expected bunkering calculated earlier in the time step, so it
    lags the newest fleet evolution. This keeps feedstock availability and bunker
    limits satisfied.

    Each share is stored with the producer's guaranteed production of the fuel it was
    measured against, so that the production the producer gains later can come off
    it.

    TODO: Can be improved with a regionality aspect

    Parameters
    ----------
    producers
        All producers in the simulation.
    fleets
        All fleets in the simulation.
    ports
        All ports in the simulation.
    fuels
        All fuels in the simulation not traded on a liquid market.
    timeline
        Simulation timeline, in years.
    idx
        Current time-step index.
    """
    demand = _calculate_bunker_demand(fleets, idx)
    supply = calculate_guaranteed_bunker_supply(ports, producers, fuels, timeline, idx)
    gap = _calculate_fuel_gap(fuels, demand, supply)

    productions: dict[str, dict[str, FloatLike]] = {}

    for producer_name, producer in producers.items():
        productions[producer_name] = _calculate_guaranteed_production(producer, idx)

    for fuel_name, fuel_gap in gap.items():
        shares = _calculate_fair_shares(producers, fuel_name)

        for producer_name, share in shares.items():
            producer = producers[producer_name]
            fair_share = fuel_gap * share
            production = productions[producer_name][fuel_name]

            producer.expectation.fair_share_demand[fuel_name][idx:] = fair_share
            producer.expectation.fair_share_baseline[fuel_name][idx:] = production
            producer.results.fair_share_fuel_fraction[fuel_name][idx] = share


def _calculate_bunker_demand(
    fleets: dict[str, Fleet], idx: int
) -> dict[tuple[str, str], FloatLike]:
    """
    Calculate the expected future demand of each fuel at each port across all fleets.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.

    Returns
    -------
    dict[tuple[str, str], FloatLike]
        Expected future demand of each fuel at each port, by port and fuel, in
        tons/year.
    """
    forward = np.s_[idx:]
    demands = [fleet.expectation.bunker_demand.at[forward] for fleet in fleets.values()]
    return add_dicts(*demands)


def _calculate_fuel_gap(
    fuels: dict[str, Fuel],
    demand: dict[tuple[str, str], FloatLike],
    supply: dict[tuple[str, str], FloatArray],
) -> dict[str, FloatLike]:
    """
    Calculate the expected future gap of each fuel, the sum of the ports' shortfalls.

    Parameters
    ----------
    fuels
        All fuels in the simulation not traded on a liquid market.
    demand
        Expected future demand of each fuel at each port, by port and fuel, in
        tons/year.
    supply
        Guaranteed future supply of each of the fuels at each port, by port and fuel,
        in tons/year.

    Returns
    -------
    dict[str, FloatLike]
        Expected future gap of each fuel, in tons/year; a port's shortfall is exactly
        zero where its demand and supply agree to rounding.
    """
    gaps: dict[str, FloatLike] = dict.fromkeys(fuels, 0.0)

    for key, port_supply in supply.items():
        _, fuel_name = key
        shortfall = subtract(demand[key], port_supply)
        gaps[fuel_name] += np.maximum(shortfall, 0.0)

    return gaps


def _calculate_guaranteed_production(
    producer: Producer, idx: int
) -> dict[str, FloatLike]:
    """
    Calculate the guaranteed production of each of a producer's fuels.

    Parameters
    ----------
    producer
        The producer.
    idx
        Current time-step index.

    Returns
    -------
    dict[str, FloatLike]
        Production of each of the producer's fuels from its plants in service and in
        the pipeline, from idx on, in tons/year.
    """
    forward = np.s_[idx:]
    expectation = producer.expectation
    production: dict[str, FloatLike] = {}

    for plant in producer.plants:
        fuel_name = plant.fuel.name
        guaranteed = expectation.guaranteed_production[plant.name][forward]
        production[fuel_name] = production.get(fuel_name, 0.0) + guaranteed

    return production


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

    for producer_name, producer in producers.items():
        if not producer.can_produce(fuel_name):
            continue

        potential = producer.expectation.development_potential[fuel_name]
        potentials[producer_name] = potential

    total = sum(potentials.values())

    if total == 0.0:
        return dict.fromkeys(potentials, 0.0)

    return {name: potential / total for name, potential in potentials.items()}
