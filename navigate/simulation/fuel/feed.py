# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Feed availability and the feed-constrained uptake of plant types."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.cohort import (
    calculate_share_below,
    extends_past,
    find_origin_indexes,
)
from navigate.util import TOLERANCE, YEAR, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray, FloatLike

logger = logging.getLogger(__name__)


def calculate_feed_availability(
    producer: Producer, timeline: FloatArray, idx: int
) -> None:
    """
    Calculate the gap between feed used and the available feed supply.

    Feed used covers both current and pipeline production.

    Parameters
    ----------
    producer
        The producer instance.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    # the existing and pipeline feed below are summed from zero
    producer.expectation.reset_additive_properties()

    times = timeline[idx:]
    years = timeline / YEAR
    today = years[idx]

    # the feed used per plant and feed constrains the uptake shares later on
    for feed_name, constraint in producer.feed_constraints.items():
        if constraint is None:
            continue

        for plant in producer.plants:
            expectation = plant.expectation
            current_production = float(expectation.get_production(idx))
            current_conversion = float(expectation.get_feed_mass(feed_name, idx))
            mass = current_production * current_conversion

            producer.expectation.set_plant_feed_consumption(plant.name, feed_name, mass)

    for p, plant in enumerate(producer.plants):
        incs = producer.increments[p]
        if not len(incs):
            continue

        # increments decommissioned before new plants could be built do not count
        lifetime = plant.lifetime.get()
        lead_time = plant.lead_time.get()
        ages = np.array([inc.age for inc in incs])
        continued = (lifetime - ages) > lead_time

        if np.all(~continued):
            continue

        multipliers = np.array([inc.multiplier for inc in incs])
        decided_arr = np.array([inc.decided for inc in incs])

        existing_increments = multipliers[continued]
        existing_decided = decided_arr[continued]

        # the first continued increment may be partly decommissioned, as the
        # model is continuous
        start = np.argmax(continued)
        boundary = lifetime - lead_time

        for i in range(start, continued.size):
            if extends_past(incs[i], boundary):
                alpha = calculate_share_below(incs[i], boundary)
                remaining = multipliers[i] * alpha

                existing_increments = np.append(existing_increments, remaining)
                existing_decided = np.append(existing_decided, decided_arr[i])

        # production and feed use are those of when the plants were built
        expectation = plant.expectation
        origins = find_origin_indexes(years, today, existing_decided)
        production = expectation.get_production(origins)
        conversions = expectation.get_feed_masses(origins)

        for feed_name, conversion in conversions.items():
            feed_mass = np.sum(production * conversion * existing_increments)
            producer.expectation.add_existing_feed(feed_name, feed_mass)

    for p, plant in enumerate(producer.plants):
        pinc = producer.pipeline[p]
        if not len(pinc):
            continue

        expectation = plant.expectation

        decided = np.array([inc.decided for inc in pinc])
        multipliers = np.array([inc.multiplier for inc in pinc])

        origins = find_origin_indexes(years, today, decided)
        production = expectation.get_production(origins)
        conversions = expectation.get_feed_masses(origins)

        for feed_name, conversion in conversions.items():
            feed_mass = np.sum(production * conversion * multipliers)
            producer.expectation.add_pipeline_feed(feed_name, feed_mass)

    for feed_name, constraint in producer.feed_constraints.items():
        if constraint is None:
            continue

        # the availability gap uses the constraint one minimum lead time ahead;
        # the minimum across plants guarantees consistency with the constraint
        lead_times = [
            plant.lead_time.get()
            for plant in producer.plants
            if producer.expectation.get_plant_feed_consumption(plant.name, feed_name)
            > 0.0
        ]

        if not lead_times:
            continue

        minimum_lead_time = np.amin(lead_times)
        supply = constraint.get(times + minimum_lead_time * YEAR)

        existing = producer.expectation.get_existing_feed(feed_name)
        pipeline = producer.expectation.get_pipeline_feed(feed_name)
        demand = existing + pipeline

        gap = supply - demand

        # an initial capacity of plants using more feed than the constraint allows
        # over-demands the feed; this signals an issue in the input data, so it is
        # flagged with a warning rather than corrected for internally
        # TODO: Remove if scrapping for negatives gets implemented
        if gap[0] < -TOLERANCE:
            logger.warning(
                "%s: %s tons/year more '%s' feed is being used than is available.",
                producer,
                round(-gap[0]),
                feed_name,
            )

            gap = np.zeros_like(gap)

        producer.expectation.set_feed_gap(idx, feed_name, gap)


def calculate_constrained_uptakes(
    producer: Producer,
    uptakes: FloatArray,
    development: float,
    limits: FloatArray,
    idx: int,
    additional_consumption: dict[str, FloatLike] | None = None,
) -> FloatArray:
    """
    Constrain uptake shares iteratively to respect feed availability.

    Parameters
    ----------
    producer
        The producer.
    uptakes
        Desired uptake-shares if the model is unconstrained.
    development
        Number of plants built over the time step.
    limits
        An array of uptake limits for each plant.
    idx
        Current time-step index.
    additional_consumption
        Potential additional consumption per feed at the given time-step index,
        tons/year.

    Returns
    -------
    FloatArray
        Uptake-shares adhering to the feed constraint at the specified amount of
        development.
    """
    # TODO: make it assignable
    tolerance = 1e-3

    current_uptakes = uptakes
    converged = False

    while not converged:
        new_limits = calculate_feed_uptake_limit_iteration(
            producer, development, current_uptakes, idx, additional_consumption
        )

        # the feed limits may not be looser than the demand-based limits
        new_limits = np.minimum(new_limits, limits)
        new_uptakes, _utilization = _calculate_constrained_shares(uptakes, new_limits)

        if np.sum(np.abs(current_uptakes - new_uptakes)) < tolerance:
            converged = True

        current_uptakes = new_uptakes

    return current_uptakes


def calculate_feed_uptake_limit_iteration(
    producer: Producer,
    development: float,
    uptakes: FloatArray,
    idx: int,
    additional_consumption: dict[str, FloatLike] | None = None,
) -> FloatArray:
    """
    Calculate feed-based uptake limits for a single iteration.

    Parameters
    ----------
    producer
        The producer.
    development
        Number of plants built over the time step.
    uptakes
        Uptakes-shares for the given iteration.
    idx
        Current time-step index.
    additional_consumption
        Potential additional consumption per feed at the given time-step index,
        tons/year.

    Returns
    -------
    FloatArray
        Uptake limit per plant from the most restrictive feed constraint.
    """
    if additional_consumption is None:
        additional_consumption = {}

    spend_map: dict[tuple[str, str], float] = {}
    total_spend: dict[str, float] = {}

    for feed_name, constraint in producer.feed_constraints.items():
        if constraint is None:
            continue

        additional_consumption.setdefault(feed_name, 0.0)
        total_spend.setdefault(feed_name, 0.0)

        for p, plant in enumerate(producer.plants):
            key = (plant.name, feed_name)
            consumption = producer.expectation.get_plant_feed_consumption(*key)

            spend = consumption * uptakes[p] * development
            spend_map[key] = spend
            total_spend[feed_name] += spend

    for feed_name, spend in total_spend.items():
        if not spend > 0.0:
            continue

        feed_gap = float(producer.expectation.get_feed_gap(feed_name, idx))
        gap = feed_gap - float(additional_consumption[feed_name])
        scaling = max(gap / spend, 0.0)

        for _p, plant in enumerate(producer.plants):
            key = (plant.name, feed_name)

            if scaling == np.inf:
                spend_map[key] = np.inf
            else:
                spend_map[key] *= scaling

    limits = np.ones_like(uptakes)
    for p, plant in enumerate(producer.plants):
        plant_name = plant.name
        current_limit = 1.0

        for feed_name in total_spend:
            key = (plant_name, feed_name)
            consumption = (
                producer.expectation.get_plant_feed_consumption(*key) * development
            )

            if not consumption > 0.0:
                continue

            new_limit = spend_map[key] / consumption
            current_limit = min(current_limit, new_limit)

        limits[p] = current_limit

    return limits


def _calculate_constrained_shares(
    shares: FloatArray, maximums: FloatArray
) -> tuple[FloatArray, float]:
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
    shares
        Uptake shares across all options, must sum to unity.
    maximums
        Maximum possible share for each option. Does not need to sum to unity.

    Returns
    -------
    tuple[FloatArray, float]
        Constrained uptake shares and the utilization share if the problem is
        over-constrained.
    """
    surplus = np.maximum(shares - maximums, 0.0)
    deficit = np.maximum(maximums - shares, 0.0)

    unutilized = max(1.0 - np.sum(maximums), 0.0)

    fraction = min(float(divide_nonzero(np.sum(surplus), np.sum(deficit))), 1.0)

    has_surplus = surplus > 0.0
    constrained_shares = np.where(has_surplus, maximums, shares + deficit * fraction)

    return constrained_shares, 1.0 - unutilized
