# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Feed availability and the feed-constrained uptake of plant types."""

from __future__ import annotations

import itertools
import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.fuel._profiles import (
    calculate_cohort_reserved,
    iterate_increments,
)
from navigate.util import TOLERANCE, YEAR, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)


def calculate_feed_availability(
    producer: Producer, timeline: FloatArray, idx: int
) -> None:
    """
    Calculate the gap between the feed supply and the feed reserved, over time.

    A plant reserves its feed from its decision until its retirement. The gap at each
    time is the supply for a plant decided then, after the feed reserved by the
    existing and pipeline plants still in service by its delivery.

    Parameters
    ----------
    producer
        The producer.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    _calculate_plant_feed_consumption(producer, idx)
    _calculate_feed_gaps(producer, timeline, idx)


def calculate_feed_delivery(
    producer: Producer, feed_name: str, times: FloatArray
) -> FloatArray | None:
    """
    Calculate the delivery of a plant decided at each of the times, for a feed.

    The feed gap is evaluated at these deliveries. Each lies the feed's lead time
    ahead: the shortest lead time at its decision of the plants using the feed, which
    keeps the gap consistent with the feed constraint for every one of them. A lead
    time falling faster than time advances leaves the deliveries out of order.

    Parameters
    ----------
    producer
        The producer.
    feed_name
        Name of the feed.
    times
        Times the plants are decided at, in days.

    Returns
    -------
    FloatArray | None
        Delivery of a plant decided at each of the times, in days; None where no
        plant uses the feed.
    """
    expectation = producer.expectation
    lead_times: list[FloatArray] = []

    for plant in producer.plants:
        if expectation.get_plant_feed_consumption(plant.name, feed_name) > 0.0:
            lead_times.append(plant.lead_time.get(times))

    if not lead_times:
        return None

    delivery: FloatArray = times + np.min(lead_times, axis=0) * YEAR
    return delivery


def calculate_constrained_uptakes(
    producer: Producer,
    uptakes: FloatArray,
    development: float,
    limits: FloatArray,
    idx: int,
    additional_consumption: dict[str, float] | None = None,
) -> FloatArray:
    """
    Constrain uptake shares iteratively to respect feed availability.

    Parameters
    ----------
    producer
        The producer.
    uptakes
        Desired uptake shares if the model is unconstrained.
    development
        Number of plants built over the time step.
    limits
        Uptake limit of each plant.
    idx
        Current time-step index.
    additional_consumption
        Feed newbuilds left out of the feed gap take at the time step, per feed, in
        tons/year; none where omitted.

    Returns
    -------
    FloatArray
        Uptake shares adhering to the feed constraint at the specified amount of
        development.
    """
    # TODO: make it assignable
    tolerance = 1e-3

    if additional_consumption is None:
        additional_consumption = {}

    current_uptakes = uptakes

    while True:
        feed_limits = _calculate_feed_limits(
            producer, development, current_uptakes, idx, additional_consumption
        )

        # the feed limits may not be looser than the demand-based limits
        new_limits = np.minimum(feed_limits, limits)
        new_uptakes = _calculate_constrained_shares(uptakes, new_limits)

        if np.sum(np.abs(current_uptakes - new_uptakes)) < tolerance:
            return new_uptakes

        current_uptakes = new_uptakes


def calculate_feed_spend(
    producer: Producer, feed_name: str, newbuilds: FloatArray
) -> float:
    """
    Calculate the feed a number of new plants of each type use.

    Parameters
    ----------
    producer
        The producer.
    feed_name
        Name of the feed.
    newbuilds
        Number of new plants of each type.

    Returns
    -------
    float
        Feed used, in tons/year.
    """
    expectation = producer.expectation
    spend = 0.0

    for plant, count in zip(producer.plants, newbuilds, strict=True):
        consumption = expectation.get_plant_feed_consumption(plant.name, feed_name)
        spend += consumption * count

    return spend


def calculate_feed_spends(
    producer: Producer, newbuilds: FloatArray
) -> dict[str, float]:
    """
    Calculate the feed a number of new plants of each type use, per constrained feed.

    Parameters
    ----------
    producer
        The producer.
    newbuilds
        Number of new plants of each type.

    Returns
    -------
    dict[str, float]
        Feed used per constrained feed, in tons/year.
    """
    spends: dict[str, float] = {}

    for feed_name, constraint in producer.feed_constraints.items():
        if constraint is not None:
            spends[feed_name] = calculate_feed_spend(producer, feed_name, newbuilds)

    return spends


def _calculate_plant_feed_consumption(producer: Producer, idx: int) -> None:
    """
    Set the feed a plant built at the time step uses, per constrained feed.

    It constrains the uptake shares later on.

    Parameters
    ----------
    producer
        The producer.
    idx
        Current time-step index.
    """
    expectation = producer.expectation

    for feed_name, constraint in producer.feed_constraints.items():
        if constraint is None:
            continue

        for plant in producer.plants:
            # Python floats, as the consumption divides the feed gaps into development
            # potentials, which a builtin sum() adds up
            production = float(plant.expectation.get_production(idx))
            conversion = float(plant.expectation.get_feed_conversion(feed_name, idx))
            consumption = production * conversion

            expectation.set_plant_feed_consumption(plant.name, feed_name, consumption)


def _calculate_feed_gaps(producer: Producer, timeline: FloatArray, idx: int) -> None:
    """
    Set the gap between the feed supply and the feed reserved, per constrained feed.

    Parameters
    ----------
    producer
        The producer.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    expectation = producer.expectation
    times = timeline[idx:]

    for feed_name, constraint in producer.feed_constraints.items():
        if constraint is None:
            continue

        delivery = calculate_feed_delivery(producer, feed_name, times)
        if delivery is None:
            continue

        supply = constraint.get(delivery)
        reserved = _calculate_cohort_feed(producer, feed_name, delivery, timeline, idx)
        gap = supply - reserved

        # an initial capacity of plants using more feed than the constraint allows
        # over-demands the feed, an issue in the input data that the warning flags;
        # the gap is floored at zero
        # TODO: Remove if scrapping for negatives gets implemented
        if gap[0] < -TOLERANCE:
            logger.warning(
                "%s: %s tons/year more '%s' feed is being used than is available.",
                producer,
                round(-gap[0]),
                feed_name,
            )

        expectation.set_feed_gap(feed_name, idx, np.maximum(gap, 0.0))


def _calculate_cohort_feed(
    producer: Producer,
    feed_name: str,
    times: FloatArray,
    timeline: FloatArray,
    idx: int,
) -> FloatArray:
    """
    Calculate the feed the existing and pipeline plants reserve at each of the times.

    Each increment reserves the feed it was decided with.

    Parameters
    ----------
    producer
        The producer.
    feed_name
        Name of the feed.
    times
        Times the profile is evaluated at, in days.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Feed reserved at each of the times, in tons/year.
    """
    plants = producer.plants
    now = timeline[idx]
    reserved = np.zeros_like(times)

    increments = itertools.chain(
        iterate_increments(plants, producer.increments, timeline, idx),
        iterate_increments(plants, producer.pipeline, timeline, idx),
    )

    for _, plant, increment, origin in increments:
        production = plant.expectation.get_production(origin)
        conversion = plant.expectation.get_feed_conversion(feed_name, origin)
        lifetime = plant.lifetime.get()

        feed = production * conversion
        reserved += calculate_cohort_reserved(increment, feed, lifetime, now, times)

    return reserved


def _calculate_feed_limits(
    producer: Producer,
    development: float,
    uptakes: FloatArray,
    idx: int,
    additional_consumption: dict[str, float],
) -> FloatArray:
    """
    Calculate feed-based uptake limits for a single iteration.

    A feed limits each plant consuming it to its uptake scaled so the feed spent fits
    into the feed gap; a feed with no spend leaves the uptake as it is.

    Parameters
    ----------
    producer
        The producer.
    development
        Number of plants built over the time step.
    uptakes
        Uptake shares for the given iteration.
    idx
        Current time-step index.
    additional_consumption
        Feed newbuilds left out of the feed gap take at the time step, per feed, in
        tons/year.

    Returns
    -------
    FloatArray
        Uptake limit per plant from the most restrictive feed constraint.
    """
    expectation = producer.expectation
    newbuilds = uptakes * development
    limits = np.ones_like(uptakes)

    for feed_name, constraint in producer.feed_constraints.items():
        if constraint is None:
            continue

        gap = expectation.get_feed_gap(feed_name, idx)
        additional = additional_consumption.get(feed_name, 0.0)
        spend = calculate_feed_spend(producer, feed_name, newbuilds)
        scaling = max((gap - additional) / spend, 0.0) if spend > 0.0 else 1.0

        # an unbounded feed limits no plant
        if scaling == np.inf:
            continue

        for p, plant in enumerate(producer.plants):
            consumption = expectation.get_plant_feed_consumption(plant.name, feed_name)

            if consumption * development > 0.0:
                limits[p] = min(limits[p], uptakes[p] * scaling)

    return limits


def _calculate_constrained_shares(
    uptakes: FloatArray, maximums: FloatArray
) -> FloatArray:
    """
    Redistribute discrete-choice shares that exceed their maximum allowed value.

    Starts from the optimal allocation of a discrete choice model, redistributing shares
    between options where an allocation exceeds its maximum allowed share.

    Notice that this method redistributes the surplus from constrained shares to the
    other shares proportionally to the deficit of each share. Meaning the bigger the gap
    to the maximum the larger the fraction of the surplus it receives.

    TODO: Is this desired or should it be a perfectly equal share between the buckets
    with deficit?
    TODO: This probably requires an iterative algorithm to ensure redistribution does
    not break maximums.

    Parameters
    ----------
    uptakes
        Uptake shares across all options, must sum to unity.
    maximums
        Maximum possible share for each option. Does not need to sum to unity.

    Returns
    -------
    FloatArray
        Constrained uptake shares.
    """
    surplus = np.maximum(uptakes - maximums, 0.0)
    deficit = np.maximum(maximums - uptakes, 0.0)

    fraction = min(float(divide_nonzero(np.sum(surplus), np.sum(deficit))), 1.0)

    has_surplus = surplus > 0.0
    return np.where(has_surplus, maximums, uptakes + deficit * fraction)
