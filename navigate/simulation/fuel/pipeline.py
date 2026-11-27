# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plants moving through the pipeline: delivery, and planning from the supply gap."""

from __future__ import annotations

from math import ceil
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import UtilityID
from navigate.core.increment import PlantIncrement
from navigate.simulation.cohort import calculate_share_below, find_insertion_index
from navigate.simulation.economics import (
    build_operating_flows,
    calculate_levelized_cost,
    calculate_two_axis_uptake,
)
from navigate.simulation.fuel.feed import calculate_constrained_uptakes
from navigate.util import divide_nonzero, drop_negligible

if TYPE_CHECKING:
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray


def perform_pipeline_delivery(producer: Producer, time: float) -> None:
    """
    Deliver plants from the pipeline that have passed their lead time.

    A pipeline increment enters service at its delivery, so its age is negative
    until then. An increment whose delivery the time reaches, to rounding, transfers
    whole to active production, and one whose age span reaches past the time is
    split.

    Parameters
    ----------
    producer
        The producer.
    time
        Current time, in years.
    """
    for p, pipeline in enumerate(producer.pipeline):
        operating = producer.increments[p]
        waiting = []

        for increment in pipeline:
            share = calculate_share_below(increment, 0.0, time)

            if share == 0.0:
                # a delivery carries the rounding of the lead time it was planned
                # ahead by, so one past the time only to rounding is delivered now
                increment.entered = min(increment.entered, time)
                operating.append(increment)

            elif share == 1.0:
                waiting.append(increment)

            else:
                # plants enter uniformly over the age span, so the part past the time
                # is delivered now and the rest keeps its span up to its delivery;
                # both keep the decision and origin of the increment
                remaining = increment.count * share
                delivered = PlantIncrement(
                    count=increment.count - remaining,
                    entered=time,
                    age_span=increment.youngest_age(time) + increment.age_span,
                    origin=increment.origin,
                    decided=increment.decided,
                )

                operating.append(delivered)
                increment.count = remaining
                increment.age_span = -increment.youngest_age(time)
                waiting.append(increment)

        producer.pipeline[p] = waiting


def perform_pipeline_planning(
    producer: Producer, timeline: FloatArray, time_step: float, idx: int
) -> None:
    """
    Plan new plant additions to the pipeline based on supply/demand gap.

    The plant types share the development limit and the feed by their uptake metrics.
    The plant types of a fuel share its supply gap, so together they build no more
    than the gap.

    Parameters
    ----------
    producer
        The producer to plan for.
    timeline
        Simulation timeline, in years.
    time_step
        Current time-step size, in years.
    idx
        Current time-step index.
    """
    expectation = producer.expectation
    development = producer.maximum_development.get() * time_step
    offtake_duration = producer.minimum_offtake_duration.get()

    for plant in producer.plants:
        fuel_name = plant.fuel.name
        required = expectation.fair_share_production[fuel_name]
        demand = expectation.fair_share_demand[fuel_name]
        shares = expectation.export_share[fuel_name].at[idx]

        _calculate_demand_newbuilds(plant, required, offtake_duration, timeline, idx)
        _calculate_inter_fuel_metric(plant, demand, timeline, idx)
        _calculate_intra_fuel_metric(plant, shares, idx)

    newbuilds = _calculate_newbuilds(producer, development, idx)

    # a count negligible against the producer's plants, operating or in the pipeline,
    # is no plant, whether a rounding residue or the tail of a logit, so no cohort is
    # built from it
    groups = [*producer.increments, *producer.pipeline]
    stock = sum(increment.count for group in groups for increment in group)
    newbuilds = drop_negligible(newbuilds, stock + np.sum(newbuilds))

    # the new plants enter the pipeline one lead time ahead of delivery
    time = timeline[idx]
    additions = zip(producer.plants, producer.pipeline, newbuilds, strict=True)

    for plant, pipeline, count in additions:
        if count == 0.0:
            continue

        delivery = time + plant.lead_time.get()
        index = find_insertion_index(pipeline, delivery)
        increment = PlantIncrement(
            count=count,
            entered=delivery,
            age_span=time_step,
            origin=idx,
            decided=time,
        )
        pipeline.insert(index, increment)

    total = np.sum(newbuilds)
    even_share = 1.0 / newbuilds.size

    producer.current_uptake = divide_nonzero(newbuilds, total, default=even_share)
    producer.results.development[idx] = total


def _calculate_newbuilds(
    producer: Producer, development: float, idx: int
) -> FloatArray:
    """
    Calculate the plants built from the uptake metrics.

    They share the development within their fuels' gaps and the feed.

    Parameters
    ----------
    producer
        The producer.
    development
        Number of plants the producer may build over the time step.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Number of plants of each type built.
    """
    if development <= 0.0:
        return np.zeros(len(producer.plants))

    uptakes = _calculate_uptakes(producer)
    limits = _calculate_demand_limits(producer, uptakes, development)
    uptakes = calculate_constrained_uptakes(producer, uptakes, development, limits, idx)
    return development * uptakes


def _calculate_demand_limits(
    producer: Producer, uptakes: FloatArray, development: float
) -> FloatArray:
    """
    Calculate each plant type's uptake limit from its fuel's gap, shared by its plants.

    A plant type's demand newbuilds state its fuel's gap as a number of its plants, so
    its uptake fills the fraction development * uptake / newbuilds of the gap. The
    plant types of a fuel share the gap in proportion to their uptakes, or evenly
    where none of them has uptake, and their limits fill it unless one of them reaches
    the whole development.

    Parameters
    ----------
    producer
        The producer.
    uptakes
        Uptake share of each plant type.
    development
        Number of plants built over the time step.

    Returns
    -------
    FloatArray
        Uptake limit per plant type, zero for a plant type not allowed, without
        demand, or without uptake where another plant type of its fuel has uptake.
    """
    newbuilds = np.zeros(len(producer.plants))
    spends = dict.fromkeys(producer.fuels, 0.0)
    counts = dict.fromkeys(producer.fuels, 0)

    for p, plant in enumerate(producer.plants):
        if producer.allow_plants[plant.name]:
            newbuilds[p] = plant.expectation.demand_newbuilds

        if newbuilds[p] > 0.0:
            spends[plant.fuel.name] += development * uptakes[p] / newbuilds[p]
            counts[plant.fuel.name] += 1

    limits = np.zeros(len(producer.plants))

    for p, plant in enumerate(producer.plants):
        if newbuilds[p] == 0.0:
            continue

        fuel_name = plant.fuel.name

        if spends[fuel_name] > 0.0:
            # one factor per fuel scales its uptakes up to the gap, which keeps the
            # split between its plant types that the intra-fuel choice made
            limit = uptakes[p] / spends[fuel_name]
        else:
            # a fuel without uptake can still take surplus from the other fuels
            limit = newbuilds[p] / (development * counts[fuel_name])

        limits[p] = min(limit, 1.0)

    return limits


def _calculate_demand_newbuilds(
    plant: Plant,
    required: FloatArray,
    offtake_duration: float,
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate the number of plants the producer's fair-share production supports.

    Parameters
    ----------
    plant
        Plant for which the newbuilds are being calculated.
    required
        The production of the plant's fuel the producer is expected to add to its
        guaranteed production, in tons/year.
    offtake_duration
        The minimum duration of offtake to justify building a plant, in years.
    timeline
        Simulation timeline, in years.
    idx
        Current time-step index.
    """
    lead_time = plant.lead_time.get()
    lifetime = plant.lifetime.get()
    output = plant.expectation.production[idx]

    year_starts, _ = build_operating_flows(lead_time, lifetime, timeline[idx])
    yearly_required = np.interp(year_starts, timeline, required, left=0.0)

    # the lowest plant count the production supports within the sufficient offtake
    # duration is the most plants it makes sense to sanction, among the years from
    # commissioning
    operating_required = yearly_required[ceil(lead_time) :]
    horizon = min(ceil(offtake_duration), ceil(lifetime), operating_required.size)
    counts = operating_required[:horizon] / output

    plant.expectation.demand_newbuilds = max(np.amin(counts), 0.0)


def _calculate_inter_fuel_metric(
    plant: Plant, demand: FloatArray, timeline: FloatArray, idx: int
) -> None:
    """
    Calculate the business-case metric used to choose a fuel pathway.

    The metric is the expected unmet demand for the plant's fuel, as energy, per
    discounted operating year of the plant: levelized on the same years and weights as
    the plant's levelized production cost.

    Parameters
    ----------
    plant
        Plant for which inter uptake metric is being calculated.
    demand
        The producer's fair share of the demand for the plant's fuel that guaranteed
        supply leaves unmet at the ports, in tons/year.
    timeline
        Simulation timeline, in years.
    idx
        Current time-step index.
    """
    lead_time = plant.lead_time.get()
    lifetime = plant.lifetime.get()
    lhv = plant.fuel.lower_heating_value.get()
    discount_rate = plant.cost_of_capital.get()

    # the fair-share demand is re-sampled onto the calendar-year grid of the plant's
    # cash flows, the one its levelized production cost is built on
    year_starts, operating = build_operating_flows(lead_time, lifetime, timeline[idx])
    yearly_demand = np.interp(year_starts, timeline, demand, left=0.0)

    # the plant's discount rate discounts the demand: dwindling demand is worth less
    # than immediate demand, since the production can be sold to other industries
    # later on
    energy = yearly_demand * lhv * operating
    metric = calculate_levelized_cost(energy, operating, discount_rate)

    plant.expectation.inter_fuel_metric = metric


def _calculate_intra_fuel_metric(
    plant: Plant, shares: dict[str, float], idx: int
) -> None:
    """
    Calculate the business-case metric used to choose a plant within a fuel pathway.

    The metric is the plant's levelized cost of fuel delivered: its levelized
    production cost plus its levelized delivery cost to each port, weighted by the
    share of the fuel exported there.

    Parameters
    ----------
    plant
        Plant for which intra uptake metric is being calculated.
    shares
        Share of the plant's fuel exported to each port at the time step.
    idx
        Current time-step index.
    """
    expectation = plant.expectation
    metric = expectation.levelized_production_cost[idx]

    for port_name, share in shares.items():
        delivery_cost = expectation.levelized_delivery_cost[port_name][idx]
        metric += share * delivery_cost

    expectation.intra_fuel_metric = metric


def _calculate_uptakes(producer: Producer) -> FloatArray:
    """
    Calculate each plant type's relative uptake share.

    Uses a two-axis discrete choice model grouped by fuel pathway.

    Parameters
    ----------
    producer
        The producer.

    Returns
    -------
    FloatArray
        Uptake shares per plant type.
    """
    index: list[int] = []
    plants: list[Plant] = []

    for p, plant in enumerate(producer.plants):
        is_in_demand = plant.expectation.inter_fuel_metric > 0.0

        if producer.allow_plants[plant.name] and is_in_demand:
            index.append(p)
            plants.append(plant)

    if not plants:
        return np.zeros(len(producer.plants))

    group_keys = [plant.fuel.name for plant in plants]
    intra_metrics = [plant.expectation.intra_fuel_metric for plant in plants]
    inter_metrics = [plant.expectation.inter_fuel_metric for plant in plants]

    uptakes = calculate_two_axis_uptake(
        group_keys=group_keys,
        intra_metrics=intra_metrics,
        inter_metrics=inter_metrics,
        intra_utility=UtilityID.LOWER_LOG_RATIO,
        inter_utility=UtilityID.HIGHER_LOG_RATIO,
        intra_odds=producer.variant_sensitivity.get(),
        inter_odds=producer.fuel_sensitivity.get(),
        context=str(producer),
    )

    padded = np.zeros(len(producer.plants))
    padded[index] = uptakes

    return padded
