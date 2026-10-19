# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The producer at simulation start: its existing plants and its decided pipeline."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.increment import PlantIncrement
from navigate.simulation.cohort import split_by_age
from navigate.simulation.fuel.expectation import (
    calculate_producer_evolution_expectation,
)
from navigate.simulation.fuel.feed import calculate_feed_availability
from navigate.util import YEAR, divide_nonzero

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
    _define_existing_pipeline(producer, timeline)

    calculate_feed_availability(producer, timeline, idx)
    calculate_producer_evolution_expectation(producer, timeline, idx)

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


def _define_existing_pipeline(producer: Producer, timeline: FloatArray) -> None:
    """
    Define the initial number of plants of each type in the production pipeline.

    Also derives the initial uptake and development-constraint utilization from the
    pipeline counts.

    Parameters
    ----------
    producer
        Producer to define the pipeline for.
    timeline
        Simulation timeline, days.
    """
    producer.pipeline = [[] for _ in producer.plants]

    for p, (_name, pipeline) in enumerate(producer.existing_pipelines.items()):
        if pipeline is None:
            continue

        planned_delivery = pipeline.x
        planned_capacity = pipeline.y

        # interpolating on the timeline makes the deliveries overlap the
        # simulation dates exactly
        planned_capacity = np.interp(timeline, planned_delivery, planned_capacity)

        incremental_delivery = timeline / YEAR
        incremental_capacity = np.insert(
            np.diff(planned_capacity), 0, planned_capacity[0]
        )

        non_zeros = incremental_capacity > 0.0
        incremental_delivery = incremental_delivery[non_zeros]
        incremental_capacity = incremental_capacity[non_zeros]

        # the first increment is assumed to have entered over a year
        incremental_dt = np.insert(np.diff(incremental_delivery), 0, 1.0)

        plant = producer.plants[p]
        capacity = plant.capacity.get()
        incremental_plants = incremental_capacity / capacity

        # a project was decided one lead time before its delivery
        lead_time = plant.lead_time.get()

        # the pipeline uses negative ages, as its plants are not yet delivered
        producer.pipeline[p] = [
            PlantIncrement(multiplier=m, age=-d, age_span=t, decided=lead_time - d)
            for m, d, t in zip(
                incremental_plants, incremental_delivery, incremental_dt, strict=True
            )
        ]

        producer.profile.development[0] = np.sum(incremental_plants)

    # the current uptake is an inertia-weighted average over the pipeline
    n = len(producer.plants)
    sum_weights = 0.0
    uptake = np.zeros((n,), dtype=np.float64)
    inertia = producer.inertia.get()

    for p in range(n):
        pinc = producer.pipeline[p]
        if not len(pinc):
            continue

        # TODO: this may need to be based on continuous compound growth?
        lead_time = producer.plants[p].lead_time.get()
        ages = np.array([inc.age for inc in pinc])
        multipliers = np.array([inc.multiplier for inc in pinc])
        weights = inertia ** (np.maximum(lead_time + ages, 0.0))

        uptake[p] = np.dot(multipliers, weights)
        sum_weights += np.sum(weights)

    producer.current_uptake = divide_nonzero(
        uptake, np.sum(uptake), default=1.0 / uptake.size
    )

    # the latest value of the development constraint is used, since the period
    # to average it back over is hard to define: the pipeline and the lead time
    # are inconsistent, and the lead time varies between plants
    maximum_development = producer.maximum_development.get()
    average_development = divide_nonzero(np.sum(uptake), sum_weights)

    producer.current_utilization = min(
        float(divide_nonzero(average_development, maximum_development)), 1.0
    )
