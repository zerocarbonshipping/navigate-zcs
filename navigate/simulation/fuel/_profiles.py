# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The rates plant increments carry over time, from their delivery to retirement."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.cohort import find_origin_indexes
from navigate.util import YEAR

if TYPE_CHECKING:
    from collections.abc import Iterator

    from navigate.core.increment import PlantIncrement
    from navigate.core.nodes.plant import Plant
    from navigate.util.types_ import FloatArray


def iterate_increments(
    plants: list[Plant],
    cohorts: list[list[PlantIncrement]],
    timeline: FloatArray,
    idx: int,
) -> Iterator[tuple[int, Plant, PlantIncrement, np.signedinteger]]:
    """Yield each plant's increments with the time-step index each was decided at."""
    years = timeline / YEAR

    for p, plant in enumerate(plants):
        increments = cohorts[p]
        if not increments:
            continue

        decided = np.array([increment.decided for increment in increments])
        origins = find_origin_indexes(years, years[idx], decided)

        for increment, origin in zip(increments, origins, strict=True):
            yield p, plant, increment, origin


def calculate_cohort_running(
    increment: PlantIncrement, rate: float, lifetime: float, times: FloatArray
) -> FloatArray:
    """
    Calculate the rate a delivered or pipeline increment carries while running.

    Its age counts back from the first of the times, the current time.
    """
    added = rate * increment.multiplier
    window = increment.age_span * YEAR
    delivery = times[0] - increment.age * YEAR
    retirement = delivery + lifetime * YEAR

    entered = _spread_delivery(added, delivery, window, times)
    return _calculate_increment_profile(added, entered, retirement, window, times)


def calculate_newbuild_running(
    plant: Plant, rate: float, time: float, window: float, times: FloatArray
) -> FloatArray:
    """Calculate the rate the newbuilds decided at `time` carry while running."""
    lifetime = plant.lifetime.get(time)
    lead_time = plant.lead_time.get(time)

    # the delivery of the last expected increment, as increments enter uniformly
    # over the time step
    delivery = time + lead_time * YEAR
    retirement = delivery + lifetime * YEAR

    entered = _spread_delivery(rate, delivery, window, times)
    return _calculate_increment_profile(rate, entered, retirement, window, times)


def _calculate_increment_profile(
    rate: float,
    entered: FloatArray,
    retirement: float,
    window: float,
    times: FloatArray,
) -> FloatArray:
    """
    Calculate the rate an increment carries at each of the times.

    Parameters
    ----------
    rate
        Rate the increment carries, such as production or feed, in tons/year.
    entered
        Part of the rate entering at each of the times, in tons/year.
    retirement
        Time the last of the rate retires at, in days.
    window
        Window over which the rate retires, in days.
    times
        Times the profile is evaluated at, in days.

    Returns
    -------
    FloatArray
        The rate carried at each of the times, in tons/year.
    """
    retired = _spread_uniformly(rate, retirement, window, times)
    return np.cumsum(entered - retired)


def _spread_delivery(
    rate: float, delivery: float, window: float, times: FloatArray
) -> FloatArray:
    """Spread the rate an increment enters with over the window up to its delivery."""
    # an increment delivered by the simulation start enters in full at the first time
    if delivery <= 0.0:
        return _enter_at(rate, 0, times)

    return _spread_uniformly(rate, delivery, window, times)


def _enter_at(rate: float, index: int, times: FloatArray) -> FloatArray:
    """Enter the whole rate at one of the times."""
    entered = np.zeros_like(times)
    entered[index] = rate
    return entered


def _spread_uniformly(
    rate: float, end: float, window: float, times: FloatArray
) -> FloatArray:
    """
    Spread a rate uniformly over the window from `end - window` to `end`.

    Each time takes the part of the window since the previous time; the part
    beyond the last time is left out.
    """
    # a remainder of the window below the tolerance is round-off
    tolerance = 1e-5

    spread = np.zeros_like(times)
    start = end - window
    remaining = window
    t = np.argmax(start < times)

    while remaining > tolerance:
        if start >= times[-1]:
            break

        partial = min(times[t], end) - start
        spread[t] = partial / window * rate

        t += 1
        start += partial
        remaining -= partial

    return spread
