# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Feed availability and the feed-constrained uptake of plant types."""

from __future__ import annotations

import logging
from itertools import compress
from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.cohort import (
    calculate_share_below,
    extends_past,
    find_origin_indexes,
)
from navigate.util import TOLERANCE, YEAR, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.increment import PlantIncrement
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray, IntArray

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
        The producer.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    years = timeline / YEAR
    current_year = years[idx]

    # the existing and pipeline feed below are summed from zero
    producer.expectation.reset_feed_totals()

    _calculate_plant_feed_consumption(producer, idx)
    _calculate_existing_feed(producer, years, current_year)
    _calculate_pipeline_feed(producer, years, current_year)
    _calculate_feed_gaps(producer, timeline, idx)


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
        Potential additional consumption per feed at the given time-step index, in
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


def calculate_feed_masses(
    plant: Plant, multipliers: FloatArray, origins: IntArray
) -> dict[str, float]:
    """
    Calculate the feed mass a set of increments of a plant type uses, per feed.

    Production and feed use are those of when the plants were decided.

    Parameters
    ----------
    plant
        The plant type of the increments.
    multipliers
        Number of plants in each increment.
    origins
        Time-step index at which each increment was decided.

    Returns
    -------
    dict[str, float]
        Feed mass per feed name, in tons/year.
    """
    production = plant.expectation.get_production(origins)
    conversions = plant.expectation.get_feed_conversions(origins)

    feed_masses: dict[str, float] = {}
    for feed_name, conversion in conversions.items():
        feed_masses[feed_name] = np.sum(production * conversion * multipliers)

    return feed_masses


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


def _calculate_existing_feed(
    producer: Producer, years: FloatArray, current_year: float
) -> None:
    """
    Add the feed used by the plants still running once new plants are built.

    Parameters
    ----------
    producer
        The producer.
    years
        Simulation timeline, in years.
    current_year
        Current year of the simulation.
    """
    for plant, increments in zip(producer.plants, producer.increments, strict=True):
        multipliers, decided = _find_continued_increments(plant, increments)

        if not multipliers.size:
            continue

        origins = find_origin_indexes(years, current_year, decided)
        feed_masses = calculate_feed_masses(plant, multipliers, origins)

        for key, value in feed_masses.items():
            producer.expectation.add_existing_feed(key, value)


def _calculate_pipeline_feed(
    producer: Producer, years: FloatArray, current_year: float
) -> None:
    """
    Add the feed used by the plants in the pipeline.

    Parameters
    ----------
    producer
        The producer.
    years
        Simulation timeline, in years.
    current_year
        Current year of the simulation.
    """
    for plant, increments in zip(producer.plants, producer.pipeline, strict=True):
        if not increments:
            continue

        multipliers = np.array([increment.multiplier for increment in increments])
        decided = np.array([increment.decided for increment in increments])
        origins = find_origin_indexes(years, current_year, decided)
        feed_masses = calculate_feed_masses(plant, multipliers, origins)

        for key, value in feed_masses.items():
            producer.expectation.add_pipeline_feed(key, value)


def _find_continued_increments(
    plant: Plant, increments: list[PlantIncrement]
) -> tuple[FloatArray, FloatArray]:
    """
    Find the plants of each increment still running once new plants are built.

    Increments decommissioned before new plants could be built do not count. As the
    model is continuous, an increment straddling that boundary adds its share below
    the boundary after the increments still running.

    Parameters
    ----------
    plant
        The plant type of the increments.
    increments
        Increments of the plant type, oldest first.

    Returns
    -------
    tuple[FloatArray, FloatArray]
        The number of plants of each continued increment and the years since it was
        decided.
    """
    lifetime = plant.lifetime.get()
    lead_time = plant.lead_time.get()
    boundary = lifetime - lead_time

    ages = np.array([increment.age for increment in increments])
    continued = lifetime - ages > lead_time

    if not continued.any():
        return np.empty(0), np.empty(0)

    running = list(compress(increments, continued))
    start = np.argmax(continued)

    multipliers = [increment.multiplier for increment in running]
    decided = [increment.decided for increment in running]

    for increment in increments[start:]:
        if not extends_past(increment, boundary):
            continue

        share = calculate_share_below(increment, boundary)
        multipliers.append(increment.multiplier * share)
        decided.append(increment.decided)

    return np.array(multipliers), np.array(decided)


def _calculate_feed_gaps(producer: Producer, timeline: FloatArray, idx: int) -> None:
    """
    Set the gap between the feed supply and the feed the plants use, per feed.

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

        lead_times: list[float] = []
        for plant in producer.plants:
            if expectation.get_plant_feed_consumption(plant.name, feed_name) > 0.0:
                lead_times.append(plant.lead_time.get())

        if not lead_times:
            continue

        # the availability gap uses the constraint one minimum lead time ahead;
        # the minimum across plants guarantees consistency with the constraint
        supply = constraint.get(times + min(lead_times) * YEAR)
        existing = expectation.get_existing_feed(feed_name)
        pipeline = expectation.get_pipeline_feed(feed_name)
        gap = supply - (existing + pipeline)

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

        expectation.set_feed_gap(feed_name, idx, gap)


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
        Potential additional consumption per feed at the given time-step index, in
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
