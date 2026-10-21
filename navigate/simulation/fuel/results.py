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
    from navigate.util.types_ import FloatArray


def record_plant_results(plant: Plant, idx: int) -> None:
    """
    Write the cost and WTT per ton of the plant invested in at the step to its results.

    Parameters
    ----------
    plant
        The plant instance.
    idx
        Current time-step index.
    """
    expectation = plant.expectation
    results = plant.results

    cost = expectation.get_levelized_production_cost(idx)
    results.investment_cost[idx] = cost

    for emission in expectation.get_emissions():
        wtt = expectation.get_production_wtt(emission, idx)
        results.investment_wtt[emission][idx] = wtt


def record_producer_results(producer: Producer, timeline: FloatArray, idx: int) -> None:
    """
    Calculate the producer results for a given time step.

    Parameters
    ----------
    producer
        The producer instance.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    """
    years = timeline / YEAR
    today = years[idx]

    _transfer_feed_constraints(producer, idx)
    _transfer_production_and_feed_mass(producer, years, today, idx)
    _transfer_plant_tied_capital(producer, years, today, idx)

    producer.results.maximum_development[idx] = producer.maximum_development.get()


def _transfer_feed_constraints(producer: Producer, idx: int) -> None:
    """
    Transfer the current feed constraints to the results.

    Parameters
    ----------
    producer
        The producer instance.
    idx
        Current time-step index.
    """
    for feed_name, constraint in producer.feed_constraints.items():
        if constraint is not None:
            producer.results.feed_constraint[feed_name][idx] = constraint.get()


def _transfer_production_and_feed_mass(
    producer: Producer, years: FloatArray, today: float, idx: int
) -> None:
    """
    Transfer the produced fuel mass and consumed feed mass per plant.

    Weighted by the increment multipliers.

    Parameters
    ----------
    producer
        The producer instance.
    years
        Simulation timeline in years.
    today
        The current year (years[idx]).
    idx
        Current time-step index.
    """
    for p, plant in enumerate(producer.plants):
        incs = producer.increments[p]
        if not len(incs):
            continue

        fuel_name = plant.fuel.name
        expectation = plant.expectation

        decided = np.array([inc.decided for inc in incs])
        multipliers = np.array([inc.multiplier for inc in incs])

        origins = find_origin_indexes(years, today, decided)
        production_unit = expectation.get_production(origins)
        production = np.sum(production_unit * multipliers)

        producer.results.production_mass[fuel_name][idx] += production

        conversions = expectation.get_feed_masses(origins)
        for feed_name, conversion in conversions.items():
            feed_mass = np.sum(production_unit * conversion * multipliers)
            producer.results.feed_mass[feed_name][idx] += feed_mass


def _transfer_plant_tied_capital(
    producer: Producer, years: FloatArray, today: float, idx: int
) -> None:
    """
    Transfer the remaining tied-up capital per plant increment.

    Parameters
    ----------
    producer
        The producer instance.
    years
        Simulation timeline in years.
    today
        The current year (years[idx]).
    idx
        Current time-step index.
    """
    for p, plant in enumerate(producer.plants):
        incs = producer.increments[p]
        for inc in incs:
            # the cost profile is that of a plant entering production 'age' years
            # ago; a plant of the initial production uses the results of a plant at
            # age 0, the best available approximation as historical data is unknown
            origin = find_origin_index(years, today, inc.age)

            tied_capital_flow = plant.expectation.get_tied_capital(origin)
            tied_capital = interpolate_yearly_flow(tied_capital_flow, inc.age)

            producer.results.plant_tied_capital[idx] += tied_capital * inc.multiplier


def record_port_results(port: Port, idx: int) -> None:
    """
    Write the port's bunkering permissions and limits to its results.

    Parameters
    ----------
    port
        The port instance.
    idx
        Current time-step index.
    """
    results = port.results

    for key, value in port.bunkering_allowed.items():
        results.bunkering_allowed[key][idx] = value

    for key, value in port.bunkering_limit.items():
        if value is not None:
            results.bunkering_limit_mass[key][idx] = value.get()
