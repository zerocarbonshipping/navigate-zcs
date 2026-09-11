# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.util import (
    YEAR,
    get_increment_origin_index,
    get_increments_origin_index,
    interpolate_tied_capital,
)

if TYPE_CHECKING:
    from navigate.core.nodes.producer import Producer


def calculate_producer_profile(
    producer: Producer, timeline: np.ndarray, idx: int
) -> None:
    """
    Calculate the producer profile for a given time step.

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

    producer.profile.set_maximum_development(idx, producer.maximum_development.get())


def _transfer_feed_constraints(producer: Producer, idx: int) -> None:
    """
    Transfer the current feed constraints to the profile.

    Parameters
    ----------
    producer
        The producer instance.
    idx
        Current time-step index.
    """
    for feed_name, constraint in producer.feed_constraints.items():
        if constraint is not None:
            producer.profile.set_feed_constraint(idx, feed_name, constraint.get())


def _transfer_production_and_feed_mass(
    producer: Producer, years: np.ndarray, today: float, idx: int
) -> None:
    """
    Transfer the produced fuel mass and the consumed feed mass per plant,
    weighted by the increment multipliers.

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
    for p, plant in enumerate(producer.assets):
        incs = producer.increments[p]
        if not len(incs):
            continue

        fuel_name = plant.fuel.name
        expectation = plant.expectation

        decided = np.array([inc.decided for inc in incs])
        multipliers = np.array([inc.multiplier for inc in incs])

        origins = get_increments_origin_index(years, today, decided)
        production_unit = expectation.get_production(origins)
        production = np.sum(production_unit * multipliers)

        producer.profile.add_production_mass(fuel_name, production, idx)

        conversions = expectation.get_feed_mass(idx=origins)

        for feed_name, conversion in conversions.items():
            feed_mass = np.sum(production_unit * conversion * multipliers)
            producer.profile.add_feed_mass(feed_name, feed_mass, idx)


def _transfer_plant_tied_capital(
    producer: Producer, years: np.ndarray, today: float, idx: int
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
    for p, plant in enumerate(producer.assets):
        incs = producer.increments[p]
        for inc in incs:
            # find the cost profile corresponding to a plant entering
            # production at 'age' years ago. Notice here that if the
            # plant was part of the initial production, the cost profile
            # from a plant at age 0 is used. This is the best available
            # approximation as historical data is unknown
            origin = get_increment_origin_index(years, today, inc.age)

            # calculate remaining tied up capital
            tied_capital_flow = plant.expectation.get_tied_capital(origin)
            tied_capital = interpolate_tied_capital(tied_capital_flow, inc.age)

            producer.profile.add_plant_tied_capital(tied_capital * inc.multiplier, idx)
