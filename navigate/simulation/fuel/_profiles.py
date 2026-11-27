# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The rates plant increments carry over time, by the rules of the producer's evolution.

An increment's plants are spread uniformly over its age span. Pipeline delivery puts
a plant in service at age 0, and decommissioning retires it at the lifetime of the
time-step it runs at, never to return. A plant runs from its delivery and reserves
its feed from its decision, until decommissioning retires it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.cohort import calculate_share_kept, calculate_share_younger

if TYPE_CHECKING:
    from collections.abc import Iterator

    from navigate.core.increment import PlantIncrement
    from navigate.core.nodes.plant import Plant
    from navigate.util.types_ import FloatArray


def iterate_increments(
    plants: list[Plant], cohorts: list[list[PlantIncrement]]
) -> Iterator[tuple[int, Plant, PlantIncrement]]:
    """Yield each plant's increments, with the plant and its index."""
    for p, plant in enumerate(plants):
        for increment in cohorts[p]:
            yield p, plant, increment


def calculate_running_rate(
    plant: Plant,
    increment: PlantIncrement,
    rate: float,
    times: FloatArray,
    first_pending: int,
) -> FloatArray:
    """
    Calculate the rate an increment carries while running at each of the times.

    Its plants run once delivered and until decommissioned at the plant lifetime of
    each time-step from `first_pending` on; before it, they keep running.

    Parameters
    ----------
    plant
        Plant type of the increment.
    increment
        Increment of the plant type.
    rate
        Rate one plant carries, such as production, in tons/year.
    times
        Times of the time-steps, from the current one on, in years.
    first_pending
        Step of the horizon from which the decommissioning is still to run.

    Returns
    -------
    FloatArray
        Rate the increment carries at each of the times, in tons/year.
    """
    pending = np.s_[first_pending:]
    steps = times[pending]
    lifetimes = plant.lifetime.get(steps)

    kept = np.ones_like(times)
    kept[pending] = calculate_share_kept(increment, steps, lifetimes, steps, lifetimes)
    undelivered = calculate_share_younger(increment, 0.0, times)

    # plants not yet delivered are younger than any lifetime, so they lie inside kept
    return rate * increment.count * (kept - undelivered)


def calculate_reserved_rate(
    plant: Plant,
    increment: PlantIncrement,
    rate: float,
    times: FloatArray,
    first_pending: int,
    delivery: FloatArray,
) -> FloatArray:
    """
    Calculate the rate an increment reserves at the deliveries of plants decided.

    Its plants reserve the rate from their decision until decommissioned at the
    plant lifetime of each time-step from `first_pending` on. A delivery reads the
    plants decommissioning left by the last time-step before it that are younger than
    the lifetime at delivery; beyond the last of the times no time-step runs, so a
    delivery past it reads the lifetime there.

    Parameters
    ----------
    plant
        Plant type of the increment.
    increment
        Increment of the plant type, decided by the first of the deliveries.
    rate
        Rate one plant reserves, such as feed, in tons/year.
    times
        Times of the time-steps, from the current one on, in years.
    first_pending
        Step of the horizon from which the decommissioning is still to run.
    delivery
        Delivery of each plant decided, in years, in any order.

    Returns
    -------
    FloatArray
        Rate the increment reserves at each of the deliveries, in tons/year.
    """
    steps = times[first_pending:]
    step_lifetimes = plant.lifetime.get(steps)
    lifetimes = plant.lifetime.get(np.minimum(delivery, times[-1]))
    kept = calculate_share_kept(increment, steps, step_lifetimes, delivery, lifetimes)

    return rate * increment.count * kept
