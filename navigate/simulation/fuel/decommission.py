# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plant decommissioning."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.cohort import retire_past_age

if TYPE_CHECKING:
    from navigate.core.nodes.producer import Producer


def perform_decommissioning(producer: Producer, time: float) -> None:
    """
    Decommission the plants past their lifetime.

    Parameters
    ----------
    producer
        Producer whose plants are decommissioned.
    time
        Current time, in years.
    """
    for p, plant in enumerate(producer.plants):
        lifetime = plant.lifetime.get()
        running, _ = retire_past_age(producer.increments[p], lifetime, time)
        producer.increments[p] = running
