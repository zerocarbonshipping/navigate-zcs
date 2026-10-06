# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Producer pipeline planning: inertia, uptake metrics and feed-constrained uptake."""

from __future__ import annotations

from math import ceil
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import UtilityID
from navigate.core.increment import PlantIncrement
from navigate.economics.decision import calculate_two_axis_uptake
from navigate.economics.metric import calculate_age_levelized_cost
from navigate.util import YEAR, calculate_inertia, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.producer import Producer
    from navigate.core.types_ import ForecastInput
    from navigate.util.types_ import FloatArray, FloatLike


def perform_pipeline_planning(
    producer: Producer, timeline: FloatArray, time_step: float, idx: int
) -> None:
    """
    Plan new plant additions to the pipeline based on supply/demand gap.

    Parameters
    ----------
    producer
        The producer to plan for.
    timeline
        Simulation timeline, days.
    time_step
        Current time-step size, days.
    idx
        Current time-step index.
    """
    inertia_increments = calculate_inertia_increments(producer, time_step, idx)

    # the production just added through inertia already covers part of the
    # supply/demand gap. get_fair_share_demand returns the stored arrays, so the
    # dict is copied here and subtraction stays out of place, leaving the stored
    # demand untouched
    demand = dict(producer.expectation.get_fair_share_demand())

    for p, plant in enumerate(producer.assets):
        production = plant.expectation.get_production(idx) * inertia_increments[p]
        fuel_name = plant.fuel.name
        demand[fuel_name] = demand[fuel_name] - production

    export_distribution = producer.expectation.get_export_distribution(idx=idx)

    # the inter metric also checks that there is sufficient future offtake to
    # merit building plants
    for plant in producer.assets:
        _calculate_uptake_inter_metric(
            plant, demand, producer.minimum_offtake_duration, timeline, idx
        )
        _calculate_uptake_intra_metric(plant, export_distribution, idx)

    demand_multipliers = np.array(
        [
            plant.expectation.get_demand_newbuilds()
            if producer.allow_plant[plant.name]
            else 0.0
            for plant in producer.assets
        ]
    )

    model_increments = np.zeros_like(inertia_increments)
    maximum_development = producer.maximum_development.get() * time_step / YEAR

    ramp_up = producer.maximum_ramp_up.get()
    maximum_increase = min(producer.current_utilization + ramp_up, 1.0)
    maximum_development *= maximum_increase

    # the inertia-based increments already count against the development limit
    maximum_development -= np.sum(inertia_increments)

    if maximum_development > 0.0:
        modelled_uptakes = calculate_modelled_uptake(producer)
        demand_limits = np.array(
            [
                min(multiplier / maximum_development, 1.0)
                for multiplier in demand_multipliers
            ]
        )
        constrained_uptakes = calculate_constrained_uptakes(
            producer, modelled_uptakes, maximum_development, demand_limits, idx
        )
        model_increments = maximum_development * constrained_uptakes

    increments = np.add(inertia_increments, model_increments)

    # the utilization carries into the next time step's ramp-up constraint
    producer.current_utilization = float(
        divide_nonzero(
            np.sum(increments), producer.maximum_development.get() * time_step / YEAR
        )
    )

    dt = time_step / YEAR

    for p, plant in enumerate(producer.assets):
        if increments[p] == 0.0:
            continue

        lead_time = plant.lead_time.get()

        # the pipeline is sorted by descending age, so the new increment is
        # inserted at the position its lead time gives it
        pinc = producer.pipeline[p]
        new_age = -lead_time

        if len(pinc):
            ages = np.array([inc.age for inc in pinc])
            i = int(np.searchsorted(-ages, -new_age, side="right"))
        else:
            i = 0

        pinc.insert(i, PlantIncrement(increments[p], new_age, dt, decided=0.0))

    total_increments = np.sum(increments)
    producer.profile.set_development(idx, total_increments)

    producer.current_uptake = divide_nonzero(
        increments, total_increments, default=1.0 / increments.size
    )


def _calculate_uptake_inter_metric(
    plant: Plant,
    demand: dict[str, FloatArray],
    minimum_offtake_duration: ForecastInput,
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate the business-case metric used to choose a fuel pathway.

    This is based on the expected future gap between supply and demand and the number of
    plants required to satisfy that gap.

    Parameters
    ----------
    plant
        Plant for which inter uptake metric is being calculated.
    demand
        The expected demand per fuel pathway that is not satisfied by current supply,
        tons/year.
    minimum_offtake_duration
        The minimum duration of offtake to justify building a plant, years.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    expectation = plant.expectation

    # the plant's discount rate discounts the future multipliers: dwindling
    # demand is worth less than immediate demand, since the production can be
    # sold to other industries later on
    discount_rate = plant.cost_of_capital.get()

    evaluation_timeline = _get_plant_evaluation_timeline(plant, timeline, idx)
    production = expectation.get_production(idx)

    fuel = plant.fuel
    lhv = fuel.lower_heating_value.get()

    # the fair-share demand is re-sampled onto the plant's business cash-flow
    # horizon, its operating years after the lead time
    demand_int = np.interp(evaluation_timeline, timeline, demand[fuel.name], left=0.0)
    demand_multipliers = demand_int / production

    lifetime = plant.lifetime.get()
    minimum_duration = minimum_offtake_duration.get()

    # the lowest equivalent multiplier within the sufficient offtake duration is
    # the most plants it makes sense to sanction
    to_ = min(min(ceil(minimum_duration), ceil(lifetime)), demand_int.size)
    demand_newbuilds = max(np.amin(demand_multipliers[:to_]), 0)

    demand_energy = demand_int * lhv
    metric = calculate_age_levelized_cost(demand_energy, lifetime, discount_rate)

    expectation.set_demand_newbuilds(demand_newbuilds)
    expectation.set_inter_fuel_metric(metric)


def _calculate_uptake_intra_metric(
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
    metric = 0.0

    for port_name, export in export_distribution.items():
        lcof = float(expectation.get_levelized_delivered_cost(port_name, idx))
        metric += float(export) * lcof

    expectation.set_intra_fuel_metric(metric)


def _get_plant_evaluation_timeline(
    plant: Plant, timeline: FloatArray, idx: int
) -> FloatArray:
    """
    Build the timeline at which cash flows should be evaluated.

    Parameters
    ----------
    plant
        Plant for which evaluation timeline is built.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Evaluation timeline, days.
    """
    lifetime = plant.lifetime.get()
    lead_time = plant.lead_time.get()

    evaluation_timeline: FloatArray = (
        np.arange(ceil(lead_time), ceil(lifetime + lead_time), dtype=np.float64) * YEAR
        + timeline[idx]
    )

    return evaluation_timeline


def calculate_inertia_increments(
    producer: Producer, time_step: float, idx: int
) -> FloatArray:
    """
    Calculate the increments being built due to inertia from previous uptake.

    Parameters
    ----------
    producer
        The producer.
    time_step
        Current time-step size, days.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Inertia-based increments per plant type, number of plants.
    """
    # the uptake shares decay by the inertia here, before the inertia-related
    # newbuilds, so the decay happens at every time step
    producer.current_uptake *= calculate_inertia(producer.inertia.get(), time_step)

    for p, plant in enumerate(producer.assets):
        if not producer.allow_plant[plant.name]:
            producer.current_uptake[p] = 0.0

    # inertia only happens if the producer is development constrained
    increments = np.zeros((len(producer.assets),))

    # the current utilization is the previous time step's, as this step's
    # planning has not run yet
    maximum_development = (
        producer.current_utilization
        * producer.maximum_development.get()
        * time_step
        / YEAR
    )

    if maximum_development > 0.0:
        demand_multipliers = np.array(
            [
                plant.expectation.get_demand_newbuilds()
                if producer.allow_plant[plant.name]
                else 0.0
                for plant in producer.assets
            ]
        )
        demand_limits = np.array(
            [
                min(multiplier / maximum_development, 1.0)
                for multiplier in demand_multipliers
            ]
        )

        uptake = producer.current_uptake
        constrained_uptake = calculate_constrained_uptakes(
            producer, uptake, maximum_development, demand_limits, idx
        )
        increments = constrained_uptake * maximum_development

        for feed_name, constraint in producer.feed_constraints.items():
            if constraint is None:
                continue

            added_consumption = 0.0

            for p, plant in enumerate(producer.assets):
                consumption = producer.expectation.get_plant_feed_consumption(
                    plant.name, feed_name
                )
                added_consumption += consumption * increments[p]

            original_gap = producer.expectation.get_feed_gap(feed_name, idx)
            new_gap = original_gap - added_consumption
            producer.expectation.set_feed_gap(idx, feed_name, new_gap)

    return increments


def calculate_modelled_uptake(producer: Producer) -> FloatArray:
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
    try:
        index, plants = zip(
            *(
                (i, plant)
                for i, plant in enumerate(producer.assets)
                if producer.allow_plant[plant.name] and plant.expectation.is_in_demand()
            ),
            strict=True,
        )

    except ValueError:
        # unpacking the empty zip fails when no plant is in demand: nothing is taken up
        return np.zeros((len(producer.assets),))

    group_keys = [plant.fuel.name for plant in plants]
    metrics_intra = [plant.expectation.get_intra_fuel_metric() for plant in plants]
    metrics_inter = [plant.expectation.get_inter_fuel_metric() for plant in plants]

    uptake = calculate_two_axis_uptake(
        group_keys=group_keys,
        metrics_intra=metrics_intra,
        metrics_inter=metrics_inter,
        intra_utility=UtilityID.LOWER_LOG_RATIO,
        inter_utility=UtilityID.HIGHER_LOG_RATIO,
        intra_odds=producer.fuel_cost_sensitivity.get(),
        inter_odds=producer.fuel_demand_sensitivity.get(),
        context=str(producer),
    )

    uptake_padded = np.zeros(len(producer.assets))

    for i, p in enumerate(index):
        uptake_padded[p] = uptake[i]

    return uptake_padded


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

        for p, plant in enumerate(producer.assets):
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

        for _p, plant in enumerate(producer.assets):
            key = (plant.name, feed_name)

            if scaling == np.inf:
                spend_map[key] = np.inf
            else:
                spend_map[key] *= scaling

    limits = np.ones_like(uptakes)
    for p, plant in enumerate(producer.assets):
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
