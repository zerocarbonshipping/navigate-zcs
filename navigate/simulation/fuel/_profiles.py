# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The rates plant increments carry over time, until their retirement.

A plant runs from its delivery and reserves its feed from its decision. Either ends
with its retirement, which removes the rate uniformly over the window up to it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.cohort import calculate_share_below
from navigate.util import drop_negligible

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


def calculate_cohort_running(
    increment: PlantIncrement, rate: float, lifetime: float, times: FloatArray
) -> FloatArray:
    """Calculate the rate a delivered or pipeline increment carries while running."""
    added = rate * increment.count
    window = increment.age_span
    delivery = increment.entered
    retirement = delivery + lifetime

    delivered = _spread_delivery(added, delivery, window, times)
    return _calculate_running_profile(added, delivered, retirement, window, times)


def calculate_newbuild_running(
    plant: Plant, rate: float, time: float, window: float, times: FloatArray
) -> FloatArray:
    """Calculate the rate the newbuilds decided at `time` carry while running."""
    lifetime = plant.lifetime.get(time)
    lead_time = plant.lead_time.get(time)

    # the delivery of the last expected increment, as increments enter uniformly
    # over the time step
    delivery = time + lead_time
    retirement = delivery + lifetime

    delivered = _spread_delivery(rate, delivery, window, times)
    return _calculate_running_profile(rate, delivered, retirement, window, times)


def calculate_cohort_reserved(
    increment: PlantIncrement, rate: float, lifetime: float, times: FloatArray
) -> FloatArray:
    """
    Calculate the rate a delivered or pipeline increment reserves.

    It is decided already, so it reserves the whole rate from the first of the times.
    """
    added = rate * increment.count
    window = increment.age_span
    retirement = increment.entered + lifetime

    return _calculate_reserved_profile(added, 0, retirement, window, times)


def calculate_newbuild_reserved(
    plant: Plant, rate: float, t: int, time: float, window: float, times: FloatArray
) -> FloatArray:
    """
    Calculate the rate the newbuilds decided at `time` reserve.

    They reserve the whole rate from the `t`-th of the times, their decision.
    """
    lifetime = plant.lifetime.get(time)
    lead_time = plant.lead_time.get(time)

    delivery = time + lead_time
    retirement = delivery + lifetime

    return _calculate_reserved_profile(rate, t, retirement, window, times)


def _calculate_running_profile(
    rate: float,
    delivered: FloatArray,
    retirement: float,
    window: float,
    times: FloatArray,
) -> FloatArray:
    """
    Calculate the rate an increment carries at each of the times, which are sorted.

    It accumulates what is delivered and retires up to each time.

    Parameters
    ----------
    rate
        Rate the increment carries, such as production or feed, in tons/year.
    delivered
        Part of the rate delivered at each of the times, in tons/year.
    retirement
        Time the last of the rate retires at, in years.
    window
        Window over which the rate retires, in years.
    times
        Times the profile is evaluated at, in years.

    Returns
    -------
    FloatArray
        The rate carried at each of the times, in tons/year.
    """
    # once all of the rate has retired, the sum is zero to rounding
    retired = _spread_uniformly(rate, retirement, window, times)
    return drop_negligible(np.cumsum(delivered - retired), rate)


def _calculate_reserved_profile(
    rate: float,
    entry: int,
    retirement: float,
    window: float,
    times: FloatArray,
) -> FloatArray:
    """
    Calculate the rate an increment reserves at each of the times, in any order.

    It reserves the whole rate from the `entry`-th time on, less the share retired by
    each time.

    Parameters
    ----------
    rate
        Rate the increment reserves, such as feed, in tons/year.
    entry
        Index of the first of the times the rate is reserved at.
    retirement
        Time the last of the rate retires at, in years.
    window
        Window over which the rate retires, in years.
    times
        Times the profile is evaluated at, in years.

    Returns
    -------
    FloatArray
        The rate reserved at each of the times, in tons/year.
    """
    is_entered = np.arange(times.size) >= entry
    retired = calculate_share_below(retirement - window, retirement, times)
    return rate * is_entered * (1.0 - retired)


def _spread_delivery(
    rate: float, delivery: float, window: float, times: FloatArray
) -> FloatArray:
    """Spread the rate an increment enters with over the window up to its delivery."""
    if delivery > 0.0:
        return _spread_uniformly(rate, delivery, window, times)

    # an increment delivered by the simulation start enters in full at the first time
    delivered = np.zeros_like(times)
    delivered[0] = rate
    return delivered


def _spread_uniformly(
    rate: float, end: float, window: float, times: FloatArray
) -> FloatArray:
    """
    Spread a rate uniformly over the window from `end - window` to `end`.

    Each time takes the part of the window since the previous time; the part
    beyond the last time is left out.
    """
    spread = np.zeros_like(times)
    start = end - window
    remaining = window
    t = np.argmax(start < times)

    # the remainder of the window carries the rounding of the dates it is taken from
    scale = max(abs(end), window)

    while remaining > 0.0:
        if start >= times[-1]:
            break

        partial = min(times[t], end) - start
        spread[t] = partial / window * rate

        t += 1
        start += partial
        remaining = float(drop_negligible(remaining - partial, scale))

    return spread
