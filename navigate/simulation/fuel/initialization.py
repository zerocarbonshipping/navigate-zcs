# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""One-time initialization of the existing producers at simulation start."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.increment import PlantIncrement
from navigate.core.nodes.curve import Curve
from navigate.simulation.fuel.evolution import (
    calculate_evolution_expectation,
    calculate_feed_availability,
    define_existing_pipeline,
)

if TYPE_CHECKING:
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.producer import Producer
    from navigate.core.types_ import CurveTableInput
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
    increments: list[list[PlantIncrement]] = []

    for p, plant in enumerate(producer.plants):
        initial_capacity = producer.initial_capacity[p].get()
        multiplier = _calculate_initial_multiplier(producer, plant, initial_capacity)
        distribution = producer.initial_age_distribution[p]

        if multiplier > 0.0:
            increments.append(_split_by_age(plant, multiplier, distribution))
        else:
            increments.append([])

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


def _split_by_age(
    plant: Plant, multiplier: float, distribution: CurveTableInput
) -> list[PlantIncrement]:
    """
    Split the initial plants of one type into one increment per age bin.

    A Curve distribution sets the ages and the share of each; otherwise the plants
    are spread evenly over yearly bins across the plant lifetime. A bin without
    plants gets no increment, and each plant was decided one lead time before its
    delivery.

    Parameters
    ----------
    plant
        Plant type of the plants.
    multiplier
        Number of initial plants of the type.
    distribution
        Initial age distribution of the type; a number spreads the ages evenly.

    Returns
    -------
    list[PlantIncrement]
        The increments of the type, oldest first.
    """
    if isinstance(distribution, Curve):
        ages = distribution.x[::-1]
        multipliers = multiplier * distribution.y[::-1]

    else:
        lifetime = plant.lifetime.get()
        bins = int(lifetime)
        ages = np.linspace(lifetime - 1.0, 0.0, bins)
        multipliers = [multiplier / bins for _ in range(bins)]

    # the oldest increment is assumed to have entered over a year
    spans = np.insert(ages[:-1] - ages[1:], 0, 1.0)
    lead_time = plant.lead_time.get()
    increments: list[PlantIncrement] = []

    for i in range(ages.size):
        # only positive multipliers are kept, to reduce overhead and to avoid
        # round-off errors in the increment average properties
        if multipliers[i] > 0.0:
            age = float(ages[i])
            increment = PlantIncrement(
                multiplier=multipliers[i],
                age=age,
                age_span=float(spans[i]),
                decided=age + lead_time,
            )
            increments.append(increment)

    return increments
