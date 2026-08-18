# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.misc import YEAR
from navigate.util import get_increment_origin_index, get_increments_origin_index

if TYPE_CHECKING:
    from navigate.fuel.producer.producer import Producer


def calculate_profile(producer: Producer, timeline, idx):
    """
    Calculate the producer profile for a given time step.

    Parameters
    ----------
    producer
        The producer instance.
    timeline : np.ndarray
        Simulation timeline.
    idx : int
        Current time-step index.
    """

    years = timeline / YEAR
    today = years[idx]

    for feed_name, constraint in producer.feed_constraints.items():

        if constraint is not None:

            producer.profile.set_feed_constraint(idx, feed_name, constraint.get())

    # transfer multiplier increment based attributes
    for p, plant in enumerate(producer.assets):

        incs = producer.increments[p]
        if not len(incs):
            continue

        fuel_name = plant.fuel.get_name()
        expectation = plant.expectation

        decided = np.array([inc.decided for inc in incs])
        multipliers = np.array([inc.multiplier for inc in incs])

        origins = get_increments_origin_index(years, today, decided)
        production_unit = expectation.get_production(origins)
        production = np.sum(production_unit * multipliers)

        producer.profile.add_production_mass(idx, fuel_name, production)

        conversions = expectation.get_feed_mass(idx=origins)

        for feed_name, conversion in conversions.items():

            feed_mass = np.sum(production_unit * conversion * multipliers)
            producer.profile.add_feed_mass(idx, feed_name, feed_mass)

    # transfer tied-up capital per increment
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
            time_flow = np.arange(0, tied_capital_flow.size) * YEAR
            tied_capital = np.interp(inc.age * YEAR, time_flow, tied_capital_flow)

            producer.profile.add_plant_tied_capital(tied_capital * inc.multiplier, idx)

    producer.profile.set_maximum_development(idx, producer.maximum_development.get())
