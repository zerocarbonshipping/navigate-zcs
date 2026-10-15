# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The plant cohorts of a producer: their initial split by age and their ageing."""

from __future__ import annotations

import itertools
import logging
from typing import TYPE_CHECKING

from navigate.core.increment import PlantIncrement
from navigate.simulation.economics.cohort import discretize_initial_cohorts
from navigate.util import YEAR

if TYPE_CHECKING:
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.producer import Producer

logger = logging.getLogger(__name__)


def define_initial_cohorts(producer: Producer) -> None:
    """
    Split each plant type's initial capacity into cohorts of plants by age.

    Parameters
    ----------
    producer
        Producer to define the initial cohorts for.
    """
    distributions = producer.initial_age_distribution

    for p, plant in enumerate(producer.assets):
        distribution = distributions[p] if distributions else None
        lifetime = plant.lifetime.get()
        lead_time = plant.lead_time.get()
        total = _get_initial_plants(producer, p, plant)
        cohorts = discretize_initial_cohorts(distribution, lifetime, total)

        increments = []
        for age, span, multiplier in cohorts:
            # empty cohorts are dropped to reduce overhead and to avoid round-off
            # errors in the cohort average properties; the positive form drops NaN
            if not multiplier > 0.0:
                continue

            # a cohort was decided one lead time before it entered service
            increment = PlantIncrement(
                multiplier=multiplier,
                age=age,
                age_span=span,
                decided=age + lead_time,
            )
            increments.append(increment)

        producer.increments.append(increments)


def age_producer_cohorts(producer: Producer, time_step: float) -> None:
    """
    Age every plant cohort of the producer, built or in the pipeline, by the time step.

    The time since decision ages too, as it dates the plant attributes a cohort was
    decided with.

    Parameters
    ----------
    producer
        Producer to age.
    time_step
        Time-step size, in days.
    """
    dt = time_step / YEAR

    for increments in itertools.chain(producer.increments, producer.pipeline):
        for increment in increments:
            increment.age += dt
            increment.decided += dt


def _get_initial_plants(producer: Producer, index: int, plant: Plant) -> float:
    """Return the number of plants the initial capacity of a plant type makes up."""
    initial_capacity = producer.initial_capacity[index].get()
    capacity = plant.capacity.get()

    # the positive form also sends a NaN capacity to the warning
    if capacity > 0.0:
        return initial_capacity / capacity

    logger.warning(
        "%s: Unable to initialize a capacity of tons/day from %s (plant %s) as "
        "the plant capacity is zero.",
        producer,
        initial_capacity,
        plant,
    )

    return 0.0
