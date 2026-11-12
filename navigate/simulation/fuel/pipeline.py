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
    build_operating_flows,
    calculate_levelized_cost,
    calculate_two_axis_uptake,
)
from navigate.simulation.fuel.feed import (
    calculate_constrained_uptakes,
    calculate_feed_spends,
)
from navigate.util import YEAR, calculate_step_inertia, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray


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
    limit and of the feed. The plant types of a fuel share its supply gap, so
    together they build no more than the gap.

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
    ramp_up = producer.maximum_ramp_up.get() * dt
    offtake_duration = producer.minimum_offtake_duration.get()

    inertia = _calculate_inertia_newbuilds(producer, limit, time_step, idx)
    demand = _calculate_uncovered_demand(producer, inertia, idx)

    for plant in producer.plants:
        shares = producer.expectation.get_export_shares(plant.fuel.name, idx)

        _calculate_inter_fuel_metric(plant, demand, offtake_duration, timeline, idx)
        _calculate_intra_fuel_metric(plant, shares, idx)

    # the utilization is the previous time step's, and the inertia already counts
    # against the development limit
    utilization = min(producer.current_utilization + ramp_up, 1.0)
    development = limit * utilization - np.sum(inertia)
    modelled = _calculate_modelled_newbuilds(producer, inertia, development, idx)
    newbuilds = inertia + modelled

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

    limits = _calculate_demand_limits(producer, uptakes, development)
    uptakes = calculate_constrained_uptakes(producer, uptakes, development, limits, idx)
    return development * uptakes


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
    producer: Producer, inertia: FloatArray, development: float, idx: int
) -> FloatArray:
    """
    Calculate the plants built from the uptake metrics.

    They share the feed the plants built through inertia leave.

    Parameters
    ----------
    producer
        The producer.
    inertia
        Number of plants of each type built through inertia.
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

    feed_spends = calculate_feed_spends(producer, inertia)
    uptakes = _calculate_modelled_uptakes(producer)
    limits = _calculate_demand_limits(producer, uptakes, development)
    uptakes = calculate_constrained_uptakes(
        producer, uptakes, development, limits, idx, feed_spends
    )
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
        if producer.allow_plant[plant.name]:
            newbuilds[p] = plant.expectation.get_demand_newbuilds()

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


def _calculate_inter_fuel_metric(
    plant: Plant,
    demand: dict[str, FloatArray],
    offtake_duration: float,
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate the business-case metric used to choose a fuel pathway.

    The metric is the expected unmet demand for the plant's fuel, as energy, per
    discounted operating year of the plant: levelized on the same years and weights as
    the plant's levelized production cost. The number of plants required to satisfy the
    gap also checks that there is sufficient future offtake to merit building plants.

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
    lead_time = plant.lead_time.get()
    lifetime = plant.lifetime.get()
    lhv = fuel.lower_heating_value.get()
    discount_rate = plant.cost_of_capital.get()
    production = expectation.get_production(idx)

    # the fair-share demand is re-sampled onto the calendar-year grid of the plant's
    # cash flows, the one its levelized production cost is built on
    year_starts, operating = build_operating_flows(lead_time, lifetime, timeline[idx])
    yearly_demand = np.interp(year_starts, timeline, demand[fuel.name], left=0.0)

    # the lowest equivalent multiplier within the sufficient offtake duration is
    # the most plants it makes sense to sanction, among the years from commissioning
    operating_demand = yearly_demand[ceil(lead_time) :]
    horizon = min(ceil(offtake_duration), ceil(lifetime), operating_demand.size)
    multipliers = operating_demand[:horizon] / production
    newbuilds = max(np.amin(multipliers), 0.0)

    # the plant's discount rate discounts the demand: dwindling demand is worth less
    # than immediate demand, since the production can be sold to other industries
    # later on
    energy = yearly_demand * lhv * operating
    metric = calculate_levelized_cost(energy, operating, discount_rate)

    expectation.set_demand_newbuilds(newbuilds)
    expectation.set_inter_fuel_metric(metric)


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
    metric = expectation.get_levelized_production_cost(idx)

    for port_name, share in shares.items():
        delivery_cost = expectation.get_levelized_delivery_cost(port_name, idx)
        metric += share * delivery_cost

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
