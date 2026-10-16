# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""One-time initialization of the existing producers at simulation start."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from navigate.core.increment import PlantIncrement
from navigate.simulation.cohort import split_by_age
from navigate.simulation.fuel.evolution import (
    calculate_evolution_expectation,
    calculate_feed_availability,
    define_existing_pipeline,
)

if TYPE_CHECKING:
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)


def initialize_existing_producer(producer: Producer, timeline: FloatArray) -> None:
    """
    Initialize the existing producer.

    This means discretizing the existing producer in time, by splitting the initial
    number of plants into individual increments with varying age.

    Must be called exactly once per producer: it assigns the producer's plants to it,
    which a second call rejects.

    Parameters
    ----------
    producer
        Producer to initialize.
    timeline
        Simulation timeline.
    """
    for plant in producer.plants:
        plant.set_producer_assignment(producer.name)

    idx = 0

    producer.increments = _build_initial_increments(producer)
    define_existing_pipeline(producer, timeline)

    calculate_feed_availability(producer, timeline, idx)
    calculate_evolution_expectation(producer, timeline, idx)

    for plant in producer.plants:
        fuel = plant.fuel
        producer.fuels.setdefault(fuel.name, fuel)


def _build_initial_increments(producer: Producer) -> list[list[PlantIncrement]]:
    """
    Build the initial increments of every plant type from its initial capacity.

    Parameters
    ----------
    producer
        Producer whose initial capacity is split.

    Returns
    -------
    list[list[PlantIncrement]]
        The increments of each plant type, oldest first.
    """
    return [_build_plant_increments(producer, p) for p in range(len(producer.plants))]


def _build_plant_increments(producer: Producer, plant_idx: int) -> list[PlantIncrement]:
    """
    Build the initial increments of one plant type, one per age bin.

    Where the type's initial age distribution is a number, its plants are spread
    evenly over the plant lifetime. A bin without plants gets no increment, and
    each plant was decided one lead time before its delivery.

    Parameters
    ----------
    producer
        Producer the plants belong to.
    plant_idx
        Index of the plant type in the producer.

    Returns
    -------
    list[PlantIncrement]
        The increments of the type, oldest first.
    """
    plant = producer.plants[plant_idx]
    initial_capacity = producer.initial_capacity[plant_idx].get()
    count = _calculate_initial_multiplier(producer, plant, initial_capacity)
    distribution = producer.initial_age_distribution[plant_idx]
    lifetime = plant.lifetime.get()
    lead_time = plant.lead_time.get()
    increments: list[PlantIncrement] = []

    if count > 0.0:
        for age, span, multiplier in split_by_age(count, distribution, lifetime):
            # only positive multipliers are kept, to reduce overhead and to avoid
            # round-off errors in the increment average properties
            if multiplier > 0.0:
                increment = PlantIncrement(
                    multiplier=multiplier,
                    age=float(age),
                    age_span=float(span),
                    decided=float(age) + lead_time,
                )
                increments.append(increment)

    return increments


def _calculate_initial_multiplier(
    producer: Producer, plant: Plant, initial_capacity: float
) -> float:
    """
    Return the number of plants of a type that make up its initial capacity.

    Parameters
    ----------
    producer
        Producer the plants belong to.
    plant
        Plant type of the plants.
    initial_capacity
        Initial capacity of the type, in tons/day.

    Returns
    -------
    float
        Number of plants, zero where the plant capacity is zero.
    """
    capacity = plant.capacity.get()

    if capacity > 0.0:
        return initial_capacity / capacity

    logger.warning(
        "%s: Unable to initialize a capacity of tons/day from %s (plant %s) as the "
        "plant capacity is zero.",
        producer,
        initial_capacity,
        plant,
    )

    return 0.0
