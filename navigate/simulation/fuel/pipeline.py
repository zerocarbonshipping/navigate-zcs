# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plants moving through the pipeline: delivery, and planning from the supply gap."""

from __future__ import annotations

from math import ceil
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import UtilityID
from navigate.core.increment import PlantIncrement
from navigate.simulation.cohort import (
    calculate_share_below,
    extends_past,
    find_insertion_index,
)
from navigate.simulation.economics import (
    calculate_age_levelized_cost,
    calculate_two_axis_uptake,
)
from navigate.simulation.fuel.feed import (
    calculate_constrained_uptakes,
    calculate_feed_spend,
)
from navigate.util import YEAR, calculate_step_inertia, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray, FloatLike


def perform_pipeline_delivery(producer: Producer) -> None:
    """
    Deliver plants from the pipeline that have passed their lead time.

    Pipeline increments use negative ages (time since delivery, negative = not yet
    delivered). After aging with += dt, delivered increments have age >= 0 and
    transfer directly to active production without sign-flipping.

    Parameters
    ----------
    producer
        The producer.
    """
    for operating, pipeline in zip(producer.increments, producer.pipeline, strict=True):
        fully_delivered = 0

        for increment in pipeline:
            if increment.age >= 0.0:
                # the age already counts the time since delivery
                operating.append(increment)
                fully_delivered += 1

            elif extends_past(increment, 0.0):
                # plants enter uniformly over the age span, so the part past zero is
                # delivered and the rest keeps its span up to zero; the delivered part
                # keeps 'decided', so its origin index stays that of the increment
                share = calculate_share_below(increment, 0.0)
                remaining = increment.multiplier * share
                delivered = PlantIncrement(
                    multiplier=increment.multiplier - remaining,
                    age=0.0,
                    age_span=increment.age + increment.age_span,
                    decided=increment.decided,
                )

                operating.append(delivered)
                increment.multiplier = remaining
                increment.age_span = -increment.age

        # the pipeline is sorted oldest first, so the fully delivered come first
        del pipeline[:fully_delivered]


def perform_pipeline_planning(
    producer: Producer, timeline: FloatArray, time_step: float, idx: int
) -> None:
    """
    Plan new plant additions to the pipeline based on supply/demand gap.

    The plants built through inertia come first and cover part of the gap; the
    plants modelled from the uptake metrics share what is left of the development
    limit.

    Parameters
    ----------
    producer
        The producer to plan for.
    timeline
        Simulation timeline, in days.
    time_step
        Current time-step size, in days.
    idx
        Current time-step index.
    """
    dt = time_step / YEAR
    limit = producer.maximum_development.get() * dt
    ramp_up = producer.maximum_ramp_up.get()
    offtake_duration = producer.minimum_offtake_duration.get()

    inertia_newbuilds = _calculate_inertia_newbuilds(producer, limit, time_step, idx)
    _calculate_inertia_feed_gaps(producer, inertia_newbuilds, idx)
    demand = _calculate_uncovered_demand(producer, inertia_newbuilds, idx)

    export_distribution = producer.expectation.get_export_distribution(idx=idx)

    for plant in producer.plants:
        _calculate_inter_fuel_metric(plant, demand, offtake_duration, timeline, idx)
        _calculate_intra_fuel_metric(plant, export_distribution, idx)

    # the utilization is the previous time step's, and the inertia already counts
    # against the development limit
    utilization = min(producer.current_utilization + ramp_up, 1.0)
    development = limit * utilization - np.sum(inertia_newbuilds)
    modelled_newbuilds = _calculate_modelled_newbuilds(producer, development, idx)
    newbuilds = inertia_newbuilds + modelled_newbuilds

    # the new plants enter the pipeline one lead time ahead of delivery
    additions = zip(producer.plants, producer.pipeline, newbuilds, strict=True)

    for plant, pipeline, count in additions:
        if count == 0.0:
            continue

        age = -plant.lead_time.get()
        index = find_insertion_index(pipeline, age)
        increment = PlantIncrement(multiplier=count, age=age, age_span=dt, decided=0.0)
        pipeline.insert(index, increment)

    total = np.sum(newbuilds)
    even_share = 1.0 / newbuilds.size

    # the utilization carries into the next time step's ramp-up constraint
    producer.current_utilization = float(divide_nonzero(total, limit))
    producer.current_uptake = divide_nonzero(newbuilds, total, default=even_share)
    producer.results.development[idx] = total


def _calculate_inertia_newbuilds(
    producer: Producer, limit: float, time_step: float, idx: int
) -> FloatArray:
    """
    Calculate the plants built due to inertia from the previous uptake.

    The previous uptake shares decay by the inertia and build their share of the
    development the previous utilization allows.

    Parameters
    ----------
    producer
        The producer.
    limit
        Number of plants the producer may build over the time step.
    time_step
        Current time-step size, in days.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Number of plants of each type built through inertia.
    """
    development = limit * producer.current_utilization

    if development <= 0.0:
        return np.zeros(len(producer.plants))

    decay = calculate_step_inertia(producer.inertia.get(), time_step)
    allowed = [producer.allow_plant[plant.name] for plant in producer.plants]
    uptakes = np.where(allowed, producer.current_uptake * decay, 0.0)

    limits = _calculate_demand_limits(producer, development)
    uptakes = calculate_constrained_uptakes(producer, uptakes, development, limits, idx)
    return development * uptakes


def _calculate_inertia_feed_gaps(
    producer: Producer, newbuilds: FloatArray, idx: int
) -> None:
    """
    Take the feed the plants built through inertia use off the feed gaps.

    Parameters
    ----------
    producer
        The producer.
    newbuilds
        Number of plants of each type built through inertia.
    idx
        Current time-step index.
    """
    expectation = producer.expectation

    for feed_name, constraint in producer.feed_constraint.items():
        if constraint is None:
            continue

        spend = calculate_feed_spend(producer, feed_name, newbuilds)
        gap = expectation.get_feed_gap(feed_name, idx)
        expectation.set_feed_gap(idx, feed_name, gap - spend)


def _calculate_uncovered_demand(
    producer: Producer, newbuilds: FloatArray, idx: int
) -> dict[str, FloatArray]:
    """
    Calculate the fair-share demand left once the inertia's production covers some.

    Parameters
    ----------
    producer
        The producer.
    newbuilds
        Number of plants of each type built through inertia.
    idx
        Current time-step index.

    Returns
    -------
    dict[str, FloatArray]
        Demand per fuel pathway not covered by the inertia, in tons/year.
    """
    # the getter returns the stored arrays, so the subtraction stays out of place
    demand = dict(producer.expectation.get_fair_share_demand())

    for plant, count in zip(producer.plants, newbuilds, strict=True):
        production = plant.expectation.get_production(idx) * count
        fuel_name = plant.fuel.name
        demand[fuel_name] = demand[fuel_name] - production

    return demand


def _calculate_modelled_newbuilds(
    producer: Producer, development: float, idx: int
) -> FloatArray:
    """
    Calculate the plants built from the uptake metrics.

    Parameters
    ----------
    producer
        The producer.
    development
        Number of plants left to build over the time step.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Number of plants of each type built from the uptake metrics.
    """
    if development <= 0.0:
        return np.zeros(len(producer.plants))

    uptakes = _calculate_modelled_uptakes(producer)
    limits = _calculate_demand_limits(producer, development)
    uptakes = calculate_constrained_uptakes(producer, uptakes, development, limits, idx)
    return development * uptakes


def _calculate_demand_limits(producer: Producer, development: float) -> FloatArray:
    """
    Calculate each plant type's uptake limit from the plants its demand merits.

    Parameters
    ----------
    producer
        The producer.
    development
        Number of plants built over the time step.

    Returns
    -------
    FloatArray
        Uptake limit per plant type, zero for a plant type not allowed.
    """
    limits: list[float] = []

    for plant in producer.plants:
        is_allowed = producer.allow_plant[plant.name]
        newbuilds = plant.expectation.get_demand_newbuilds() if is_allowed else 0.0
        limits.append(min(newbuilds / development, 1.0))

    return np.array(limits)


def _calculate_inter_fuel_metric(
    plant: Plant,
    demand: dict[str, FloatArray],
    offtake_duration: float,
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate the business-case metric used to choose a fuel pathway.

    This is based on the expected future gap between supply and demand and the number of
    plants required to satisfy that gap, which also checks that there is sufficient
    future offtake to merit building plants.

    Parameters
    ----------
    plant
        Plant for which inter uptake metric is being calculated.
    demand
        The expected demand per fuel pathway that is not satisfied by current supply,
        in tons/year.
    offtake_duration
        The minimum duration of offtake to justify building a plant, in years.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    expectation = plant.expectation
    fuel = plant.fuel
    lifetime = plant.lifetime.get()
    lhv = fuel.lower_heating_value.get()
    discount_rate = plant.cost_of_capital.get()
    production = expectation.get_production(idx)

    # the fair-share demand is re-sampled onto the plant's business cash-flow
    # horizon, its operating years after the lead time
    times = _calculate_evaluation_timeline(plant, timeline, idx)
    operating_demand = np.interp(times, timeline, demand[fuel.name], left=0.0)

    # the lowest equivalent multiplier within the sufficient offtake duration is
    # the most plants it makes sense to sanction
    horizon = min(ceil(offtake_duration), ceil(lifetime), operating_demand.size)
    multipliers = operating_demand[:horizon] / production
    newbuilds = max(np.amin(multipliers), 0.0)

    # the plant's discount rate discounts the demand: dwindling demand is worth less
    # than immediate demand, since the production can be sold to other industries
    # later on
    energy = operating_demand * lhv
    metric = calculate_age_levelized_cost(energy, lifetime, discount_rate)

    expectation.set_demand_newbuilds(newbuilds)
    expectation.set_inter_fuel_metric(metric)


def _calculate_evaluation_timeline(
    plant: Plant, timeline: FloatArray, idx: int
) -> FloatArray:
    """
    Calculate the times at which a plant's cash flows are evaluated.

    Parameters
    ----------
    plant
        Plant for which evaluation timeline is built.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Evaluation timeline, in days.
    """
    lifetime = plant.lifetime.get()
    lead_time = plant.lead_time.get()
    years = np.arange(ceil(lead_time), ceil(lifetime + lead_time), dtype=np.float64)
    times: FloatArray = years * YEAR + timeline[idx]

    return times


def _calculate_intra_fuel_metric(
    plant: Plant, export_distribution: dict[str, FloatLike], idx: int
) -> None:
    """
    Calculate the business-case metric used to choose a plant within a fuel pathway.

    This is based on the average delivered levelized cost of fuel for a given plant.

    Parameters
    ----------
    plant
        Plant for which intra uptake metric is being calculated.
    export_distribution
        Fraction of fuel production that is exported to each port at the time step.
    idx
        Current time-step index.
    """
    expectation = plant.expectation
    production_cost = expectation.get_levelized_production_cost(idx)
    metric = 0.0

    for port_name, export in export_distribution.items():
        delivery_cost = expectation.get_levelized_delivery_cost(port_name, idx)
        delivered_cost = float(production_cost + delivery_cost)
        metric += float(export) * delivered_cost

    expectation.set_intra_fuel_metric(metric)


def _calculate_modelled_uptakes(producer: Producer) -> FloatArray:
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
        is_in_demand = plant.expectation.get_inter_fuel_metric() > 0.0

        if producer.allow_plant[plant.name] and is_in_demand:
            index.append(p)
            plants.append(plant)

    if not plants:
        return np.zeros(len(producer.plants))

    group_keys = [plant.fuel.name for plant in plants]
    intra_metrics = [plant.expectation.get_intra_fuel_metric() for plant in plants]
    inter_metrics = [plant.expectation.get_inter_fuel_metric() for plant in plants]

    uptakes = calculate_two_axis_uptake(
        group_keys=group_keys,
        intra_metrics=intra_metrics,
        inter_metrics=inter_metrics,
        intra_utility=UtilityID.LOWER_LOG_RATIO,
        inter_utility=UtilityID.HIGHER_LOG_RATIO,
        intra_odds=producer.fuel_cost_sensitivity.get(),
        inter_odds=producer.fuel_demand_sensitivity.get(),
        context=str(producer),
    )

    padded = np.zeros(len(producer.plants))
    padded[index] = uptakes

    return padded
