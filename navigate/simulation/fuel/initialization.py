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
from navigate.util import YEAR, divide_nonzero, step_lengths

if TYPE_CHECKING:
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)


def initialize_existing_producer(producer: Producer, timeline: FloatArray) -> None:
    """
    Initialize the existing producer, splitting its plants into increments by age.

    Must be called exactly once per producer: it assigns the producer's plants to it,
    which a second call rejects.

    Parameters
    ----------
    producer
        Producer to initialize.
    timeline
        Simulation timeline, in days.
    """
    idx = 0

    for plant in producer.plants:
        plant.set_producer_assignment(producer.name)
        producer.fuels.setdefault(plant.fuel.name, plant.fuel)

    producer.increments = _build_initial_increments(producer)
    producer.pipeline = _build_existing_pipeline(producer, timeline)
    _define_initial_development(producer)

    calculate_feed_availability(producer, timeline, idx)
    calculate_producer_evolution_expectation(producer, timeline, idx)


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
    count = _calculate_initial_count(producer, plant, initial_capacity)
    distribution = producer.initial_age_distribution[plant_idx]
    lifetime = plant.lifetime.get()
    lead_time = plant.lead_time.get()

    # a NaN count, such as from an expression dividing by zero, builds no cohorts
    if not count > 0.0:
        return []

    # only positive multipliers are kept, to reduce overhead and to avoid round-off
    # errors in the increment average properties
    increments: list[PlantIncrement] = []
    for age, span, multiplier in split_by_age(count, distribution, lifetime):
        if multiplier > 0.0:
            increment = PlantIncrement(
                multiplier=multiplier,
                age=float(age),
                age_span=float(span),
                decided=float(age) + lead_time,
            )
            increments.append(increment)

    return increments


def _calculate_initial_count(
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
        "%s: Unable to initialize a capacity of %s tons/day (plant %s) as the plant "
        "capacity is zero.",
        producer,
        initial_capacity,
        plant,
    )

    return 0.0


def _build_existing_pipeline(
    producer: Producer, timeline: FloatArray
) -> list[list[PlantIncrement]]:
    """
    Build the increments of every plant type from its existing pipeline.

    Parameters
    ----------
    producer
        Producer whose existing pipelines are split.
    timeline
        Simulation timeline, in days.

    Returns
    -------
    list[list[PlantIncrement]]
        The increments of each plant type, earliest delivery first.
    """
    plant_count = len(producer.plants)
    return [_build_plant_pipeline(producer, p, timeline) for p in range(plant_count)]


def _build_plant_pipeline(
    producer: Producer, plant_idx: int, timeline: FloatArray
) -> list[PlantIncrement]:
    """
    Build the increments of one plant type, one per date its pipeline adds capacity.

    Parameters
    ----------
    producer
        Producer the plants belong to.
    plant_idx
        Index of the plant type in the producer.
    timeline
        Simulation timeline, in days.

    Returns
    -------
    list[PlantIncrement]
        The increments of the type, earliest delivery first; none without a
        pipeline.
    """
    plant = producer.plants[plant_idx]
    pipeline = producer.existing_pipeline[plant.name]

    if pipeline is None:
        return []

    capacity = plant.capacity.get()
    lead_time = plant.lead_time.get()

    # interpolating on the timeline makes the deliveries overlap the simulation
    # dates exactly
    capacities = np.interp(timeline, pipeline.x, pipeline.y)
    added = np.diff(capacities, prepend=0.0)
    is_delivery = added > 0.0

    deliveries = timeline[is_delivery] / YEAR
    counts = added[is_delivery] / capacity

    # the first increment is assumed to have entered over a year
    spans = step_lengths(deliveries)

    # the pipeline holds negative ages, as its plants are not yet delivered, each
    # decided one lead time before its delivery
    increments: list[PlantIncrement] = []
    for count, delivery, span in zip(counts, deliveries, spans, strict=True):
        age = -delivery
        increment = PlantIncrement(
            multiplier=count,
            age=age,
            age_span=span,
            decided=age + lead_time,
        )
        increments.append(increment)

    return increments


def _define_initial_development(producer: Producer) -> None:
    """
    Define the initial uptake, utilization and development from the pipeline.

    The uptake weighs each pipelined plant by the inertia raised to the years since
    it was decided, and the development counts every pipelined plant.

    Parameters
    ----------
    producer
        Producer whose pipeline is read.
    """
    inertia = producer.inertia.get()
    maximum_development = producer.maximum_development.get()
    weighted_counts = np.zeros(len(producer.plants))
    weight_total = 0.0
    count_total = 0.0

    # TODO: this may need to be based on continuous compound growth?
    for p, increments in enumerate(producer.pipeline):
        decided = np.array([increment.decided for increment in increments])
        multipliers = np.array([increment.multiplier for increment in increments])
        weights = inertia ** np.maximum(decided, 0.0)

        weighted_counts[p] = np.dot(multipliers, weights)
        weight_total += np.sum(weights)
        count_total += np.sum(multipliers)

    weighted_total = np.sum(weighted_counts)
    even_share = 1.0 / weighted_counts.size
    uptakes = divide_nonzero(weighted_counts, weighted_total, default=even_share)

    # the latest value of the development constraint is used, since the period
    # to average it back over is hard to define: the pipeline and the lead time
    # are inconsistent, and the lead time varies between plants
    average_development = divide_nonzero(weighted_total, weight_total)
    utilization = float(divide_nonzero(average_development, maximum_development))

    producer.current_uptake = uptakes
    producer.current_utilization = min(utilization, 1.0)
    producer.results.development[0] = count_total
