# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plant decommissioning."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.cohort import calculate_share_below

if TYPE_CHECKING:
    from navigate.core.nodes.producer import Producer


def perform_decommissioning(producer: Producer, time: float) -> None:
    """
    Decommission the plants past their lifetime.

    An increment spanning the lifetime keeps the share of its plants below it, as its
    plants are spread uniformly over its age span.

    Parameters
    ----------
    producer
        Producer whose plants are decommissioned.
    time
        Current time, in years.
    """
    for p, plant in enumerate(producer.plants):
        lifetime = plant.lifetime.get()
        running = []

        for increment in producer.increments[p]:
            share = calculate_share_below(increment, lifetime, time)

            if share == 0.0:
                continue

            if share < 1.0:
                increment.count *= share
                increment.age_span = lifetime - increment.age(time)

            running.append(increment)

        producer.increments[p] = running
