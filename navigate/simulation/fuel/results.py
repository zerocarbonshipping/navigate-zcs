# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The plant, producer and port results written at each time step."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.fuel._profiles import iterate_increments
from navigate.util import average_yearly_flow

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

    Its plants' results take the expected cost and WTT of the fuel they produce at
    the step.

    Parameters
    ----------
    producer
        The producer.
    timeline
        Simulation timeline, in years.
    idx
        Current time-step index.
    """
    _transfer_feed_constraints(producer, idx)
    _transfer_production_and_feed_mass(producer, idx)
    _transfer_plant_tied_capital(producer, timeline[idx], idx)
    _transfer_instantaneous_production(producer, idx)

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
    for feed_name, limit in producer.feed_limits.items():
        if limit is not None:
            producer.results.feed_constraint[feed_name][idx] = limit.get()


def _transfer_production_and_feed_mass(producer: Producer, idx: int) -> None:
    """
    Transfer the fuel produced and feed used per plant, weighted by its increments.

    Parameters
    ----------
    producer
        The producer.
    idx
        Current time-step index.
    """
    results = producer.results

    for plant, increments in zip(producer.plants, producer.increments, strict=True):
        if not increments:
            continue

        origins = np.array([increment.origin for increment in increments])
        counts = np.array([increment.count for increment in increments])

        production_per_plant = plant.expectation.production[origins]
        production = np.sum(production_per_plant * counts)
        feed_masses = _calculate_feed_masses(plant, counts, origins)

        results.production_mass[plant.fuel.name][idx] += production

        for key, value in feed_masses.items():
            results.feed_mass[key][idx] += value


def _calculate_feed_masses(
    plant: Plant, counts: FloatArray, origins: IntArray
) -> dict[str, float]:
    """
    Calculate the feed mass a set of increments of a plant type uses, per feed.

    Production and feed use are those of when the plants were decided.

    Parameters
    ----------
    plant
        The plant type of the increments.
    counts
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
        feed_masses[feed_name] = np.sum(production * conversion * counts)

    return feed_masses


def _transfer_plant_tied_capital(producer: Producer, time: float, idx: int) -> None:
    """
    Transfer the remaining tied-up capital per plant increment.

    An increment ties up the capital of a plant decided when it was, averaged over
    the ages of its plants since delivery.

    Parameters
    ----------
    producer
        The producer.
    time
        Current time, in years.
    idx
        Current time-step index.
    """
    results = producer.results

    for _, plant, increment in iterate_increments(producer.plants, producer.increments):
        youngest = increment.youngest_age(time)
        oldest = increment.oldest_age(time)

        tied_capital_flow = plant.expectation.tied_capital[increment.origin]
        tied_capital = average_yearly_flow(tied_capital_flow, youngest, oldest)

        results.plant_tied_capital[idx] += tied_capital * increment.count


def _transfer_instantaneous_production(producer: Producer, idx: int) -> None:
    """
    Transfer the expected cost and WTT of the fuel each plant produces at the step.

    A plant the producer expects no production from at the step stays missing.

    Parameters
    ----------
    producer
        The producer.
    idx
        Current time-step index.
    """
    for plant in producer.plants:
        production = producer.expectation.expected_production[plant.name][idx]
        expectation = plant.expectation
        results = plant.results

        if production > 0.0:
            results.instantaneous_cost[idx] = expectation.expected_production_cost[idx]

            for emission_name, wtt in expectation.expected_production_wtt.items():
                results.instantaneous_wtt[emission_name][idx] = wtt[idx]


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

    for key, value in port.allow_bunkering.items():
        results.bunkering_allowed[key][idx] = value

    for key, value in port.bunkering_limits.items():
        if value is not None:
            results.bunkering_limit_mass[key][idx] = value.get()
