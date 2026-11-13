# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The plant, producer and port results written at each time step."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.cohort import find_origin_index, find_origin_indexes
from navigate.util import YEAR, interpolate_yearly_flow

if TYPE_CHECKING:
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray, IntArray


def record_plant_results(plant: Plant, idx: int) -> None:
    """
    Write the cost and WTT per ton of the plant invested in at the step to its results.

    Parameters
    ----------
    plant
        The plant.
    idx
        Current time-step index.
    """
    expectation = plant.expectation
    results = plant.results

    cost = expectation.levelized_production_cost[idx]
    results.investment_cost[idx] = cost

    for emission_name, wtt in expectation.production_wtt.items():
        results.investment_wtt[emission_name][idx] = wtt[idx]


def record_producer_results(producer: Producer, timeline: FloatArray, idx: int) -> None:
    """
    Write the producer's production, feed use, tied capital and limits to its results.

    Parameters
    ----------
    producer
        The producer.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    _transfer_feed_constraints(producer, idx)
    _transfer_production_and_feed_mass(producer, timeline, idx)
    _transfer_plant_tied_capital(producer, timeline, idx)

    producer.results.maximum_development[idx] = producer.maximum_development.get()


def _transfer_feed_constraints(producer: Producer, idx: int) -> None:
    """
    Transfer the current feed constraints to the results.

    Parameters
    ----------
    producer
        The producer.
    idx
        Current time-step index.
    """
    for feed_name, constraint in producer.feed_constraints.items():
        if constraint is not None:
            producer.results.feed_constraint[feed_name][idx] = constraint.get()


def _transfer_production_and_feed_mass(
    producer: Producer, timeline: FloatArray, idx: int
) -> None:
    """
    Transfer the fuel produced and feed used per plant, weighted by its increments.

    Parameters
    ----------
    producer
        The producer.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    results = producer.results
    years = timeline / YEAR
    current_year = years[idx]

    for plant, increments in zip(producer.plants, producer.increments, strict=True):
        if not increments:
            continue

        decided = np.array([increment.decided for increment in increments])
        multipliers = np.array([increment.multiplier for increment in increments])
        origins = find_origin_indexes(years, current_year, decided)

        production_per_plant = plant.expectation.production[origins]
        production = np.sum(production_per_plant * multipliers)
        feed_masses = _calculate_feed_masses(plant, multipliers, origins)

        results.production_mass[plant.fuel.name][idx] += production

        for key, value in feed_masses.items():
            results.feed_mass[key][idx] += value


def _calculate_feed_masses(
    plant: Plant, multipliers: FloatArray, origins: IntArray
) -> dict[str, float]:
    """
    Calculate the feed mass a set of increments of a plant type uses, per feed.

    Production and feed use are those of when the plants were decided.

    Parameters
    ----------
    plant
        The plant type of the increments.
    multipliers
        Number of plants in each increment.
    origins
        Time-step index at which each increment was decided.

    Returns
    -------
    dict[str, float]
        Feed mass per feed name, in tons/year.
    """
    production = plant.expectation.production[origins]
    conversions = plant.expectation.feed_conversion.at[origins]

    feed_masses: dict[str, float] = {}
    for feed_name, conversion in conversions.items():
        feed_masses[feed_name] = np.sum(production * conversion * multipliers)

    return feed_masses


def _transfer_plant_tied_capital(
    producer: Producer, timeline: FloatArray, idx: int
) -> None:
    """
    Transfer the remaining tied-up capital per plant increment.

    Parameters
    ----------
    producer
        The producer.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    results = producer.results
    years = timeline / YEAR
    current_year = years[idx]

    for plant, increments in zip(producer.plants, producer.increments, strict=True):
        for increment in increments:
            # the costs are those of a plant that entered production 'age' years ago
            origin = find_origin_index(years, current_year, increment.age)
            tied_capital_flow = plant.expectation.tied_capital[origin]
            tied_capital = interpolate_yearly_flow(tied_capital_flow, increment.age)

            results.plant_tied_capital[idx] += tied_capital * increment.multiplier


def record_port_results(port: Port, idx: int) -> None:
    """
    Write the port's bunkering permissions and limits to its results.

    Parameters
    ----------
    port
        The port.
    idx
        Current time-step index.
    """
    results = port.results

    for key, value in port.bunkering_allowed.items():
        results.bunkering_allowed[key][idx] = value

    for key, value in port.bunkering_limits.items():
        if value is not None:
            results.bunkering_limit_mass[key][idx] = value.get()
