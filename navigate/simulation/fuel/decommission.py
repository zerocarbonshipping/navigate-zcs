# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plant ageing and decommissioning."""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

from navigate.simulation.cohort import calculate_share_below, extends_past
from navigate.util import YEAR

if TYPE_CHECKING:
    from navigate.core.nodes.producer import Producer


def update_plant_ages(producer: Producer, time_step: float) -> None:
    """
    Age the producer's plants and its pipeline by the time since the last time-step.

    The time since decision advances with the age, as it dates the plant attributes
    an increment was decided with.

    Parameters
    ----------
    producer
        Producer whose plants are aged.
    time_step
        Current time-step size, in days.
    """
    dt = time_step / YEAR

    for increments in itertools.chain(producer.increments, producer.pipeline):
        for increment in increments:
            increment.age += dt
            increment.decided += dt


def perform_decommissioning(producer: Producer) -> None:
    """
    Decommission the plants past their lifetime.

    An increment spanning the lifetime keeps the share of its plants below it, as its
    plants are spread uniformly over its age span.

    Parameters
    ----------
    producer
        Producer whose plants are decommissioned.
    """
    for p, plant in enumerate(producer.plants):
        lifetime = plant.lifetime.get()
        increments = producer.increments[p]
        running = [increment for increment in increments if increment.age < lifetime]

        for increment in running:
            if extends_past(increment, lifetime):
                share = calculate_share_below(increment, lifetime)
                increment.multiplier *= share
                increment.age_span = lifetime - increment.age

        producer.increments[p] = running
