# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""One-time initialization of the existing producers at simulation start."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.fuel.evolution import (
    calculate_evolution_expectation,
    calculate_feed_availability,
    define_existing_pipeline,
)

if TYPE_CHECKING:
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray


def initialize_existing_producer(producer: Producer, timeline: FloatArray) -> None:
    """
    Initialize the existing producer.

    This means discretizing the existing producer in time, by splitting the initial
    number of plants into individual increments with varying age.

    Must be called exactly once per producer: discretization appends to the increment
    stores.

    Parameters
    ----------
    producer
        Producer to initialize.
    timeline
        Simulation timeline.
    """
    for plant in producer.assets:
        plant.set_producer_assignment(producer.name)

    idx = 0

    producer.define_initial_capacity()
    producer.define_initial_age()
    producer.define_initial_decided()
    producer.define_initial_multipliers()

    # zero multipliers are dropped to reduce overhead and to avoid round-off
    # errors in the increment average properties
    for a in range(len(producer.increments)):
        producer.increments[a] = [
            inc for inc in producer.increments[a] if inc.multiplier > 0.0
        ]

    define_existing_pipeline(producer, timeline)

    calculate_feed_availability(producer, timeline, idx)
    calculate_evolution_expectation(producer, timeline, idx)

    for plant in producer.assets:
        fuel = plant.fuel
        producer.fuels.setdefault(fuel.name, fuel)
