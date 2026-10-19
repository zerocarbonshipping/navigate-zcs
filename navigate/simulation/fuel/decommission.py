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
        Current time-step size, days.
    """
    dt = time_step / YEAR

    for increments in itertools.chain(producer.increments, producer.pipeline):
        for increment in increments:
            increment.age += dt
            increment.decided += dt


def perform_decommissioning(producer: Producer) -> None:
    """
    Decommission increments that have exceeded their plant's lifetime.

    Parameters
    ----------
    producer
        The producer instance.
    """
    for p, plant in enumerate(producer.plants):
        incs = producer.increments[p]
        lifetime = plant.lifetime.get()

        producer.increments[p] = [inc for inc in incs if inc.age < lifetime]

        # partially decommission increments whose age_span spans the lifetime boundary
        for inc in producer.increments[p]:
            if extends_past(inc, lifetime):
                alpha = calculate_share_below(inc, lifetime)
                decommissioning = inc.multiplier * (1.0 - alpha)

                inc.multiplier -= decommissioning
                inc.age_span = lifetime - inc.age
