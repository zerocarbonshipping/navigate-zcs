# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plant ageing and decommissioning."""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

from navigate.simulation.cohort import calculate_share_below

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
        Current time-step size, in years.
    """
    for increments in itertools.chain(producer.increments, producer.pipeline):
        for increment in increments:
            increment.age += time_step
            increment.decided += time_step


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
        running = []

        for increment in producer.increments[p]:
            share = calculate_share_below(increment, lifetime)

            if share == 0.0:
                continue

            if share < 1.0:
                increment.count *= share
                increment.age_span = lifetime - increment.age

            running.append(increment)

        producer.increments[p] = running
