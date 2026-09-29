# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from math import ceil
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import UtilityID
from navigate.core.increment import Increment
from navigate.economics.decision import calculate_two_axis_uptake
from navigate.economics.metric import calculate_age_levelized_cost
from navigate.util import YEAR, calculate_inertia, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.producer import Producer

logger = logging.getLogger(__name__)


def perform_pipeline_planning(producer: Producer, timeline, time_step, idx):
    """
    Plan new plant additions to the pipeline based on supply/demand gap.

    Parameters
    ----------
    producer
        The producer to plan for.
    timeline : np.ndarray
        Simulation timeline.
    time_step : float
        Current time-step size.
    idx : int
        Current time-step index.
    """
    # calculate the increments being build due to inertia
    inertia_increments = calculate_inertia_increments(producer, time_step, idx)

    # reduce the supply/demand gap by the amount
    # of production just added due to inertia
    demand = producer.expectation.get_fair_share_demand()

    for p, plant in enumerate(producer.assets):
        # calculate total added production
        # from inertia and subtract from
        # the demand of the fuel
        production = plant.expectation.get_production(idx) * inertia_increments[p]
        demand[plant.fuel.name] -= production

    # calculate the "levelized multiplier"
    # which is used as the metric for uptake
    # across fuel pathways. Further, check
    # that there is sufficient future offtake
    # to merit building plants
    export_distribution = producer.expectation.get_export_distribution(idx=idx)

    for _p, plant in enumerate(producer.assets):
        _calculate_uptake_inter_metric(
            plant, demand, producer.minimum_offtake_duration, timeline, idx
        )
        _calculate_uptake_intra_metric(plant, export_distribution, idx)

    # extract the maximum number of newbuild
    # plants that may enter the pipeline
    demand_multipliers = np.array(
        [
            plant.expectation.get_demand_newbuilds()
            if producer.allow_plant[plant.name]
            else 0.0
            for plant in producer.assets
        ]
    )

    # calculate the modelled increments of each plant
    model_increments = np.zeros_like(inertia_increments)
    maximum_development = producer.maximum_development.get() * time_step / YEAR

    # constrain the development by
    # the maximum increase fraction
    ramp_up = producer.maximum_ramp_up.get()
    maximum_increase = min(producer.current_utilization + ramp_up, 1.0)
    maximum_development *= maximum_increase

    # remove the already added inertia-based increments
    maximum_development -= np.sum(inertia_increments)

    if maximum_development > 0.0:
        # calculate the optimal shares
        # based on investment metrics
        modelled_uptakes = calculate_modelled_uptake(producer)

        # calculate maximum possible share
        # based on demanded multipliers
        demand_limits = np.array(
            [
                min(multiplier / maximum_development, 1.0)
                for multiplier in demand_multipliers
            ]
        )

        # calculate the maximum allowable share
        # based on the available feed and
        # accounting for maximum plant demand
        constrained_uptakes = calculate_constrained_uptakes(
            producer, modelled_uptakes, maximum_development, demand_limits, idx
        )

        # calculate the model increments
        model_increments = maximum_development * constrained_uptakes

    # add the inertia and modelled increments together
    increments = np.add(inertia_increments, model_increments)

    # define the utilization for use in the next time-step
    producer.current_utilization = divide_nonzero(
        np.sum(increments), producer.maximum_development.get() * time_step / YEAR
    )

    # add increments to the pipeline
    dt = time_step / YEAR

    for p, plant in enumerate(producer.assets):
        if increments[p] == 0.0:
            continue

        lead_time = plant.lead_time.get()

        # insert into the descending-sorted pipeline
        # at the correct position for the new lead time
        pinc = producer.pipeline[p]
        new_age = -lead_time

        if len(pinc):
            ages = np.array([inc.age for inc in pinc])
            i = int(np.searchsorted(-ages, -new_age, side="right"))
        else:
            i = 0

        pinc.insert(i, Increment(increments[p], new_age, dt, decided=0.0))

    # assign total development to profile
    total_increments = np.sum(increments)
    producer.profile.set_development(idx, total_increments)

    # set current uptake
    producer.current_uptake = divide_nonzero(
        increments, total_increments, default=1.0 / increments.size
    )


def _calculate_uptake_inter_metric(
    plant, demand, minimum_offtake_duration, timeline, idx
):
    """
    Calculate the business-case metric used to choose a fuel pathway.

    This is based on the expected future gap between supply and demand and the number of
    plants required to satisfy that gap.

    Parameters
    ----------
    plant : Plant
        Plant for which inter uptake metric is being calculated.
    demand : dict[str, np.ndarray]
        The expected demand per fuel pathway that is not satisfied by current supply.
    minimum_offtake_duration : Scalar | calculator node
        The minimum duration of offtake to justify building a plant.
    timeline : np.ndarray
        Simulation timeline.
    idx : int
        Current time-step index.
    """
    expectation = plant.expectation

    # the discount rate of the plants are used
    # to discount the future multipliers. The
    # logic is that if the demand is dwindling
    # over time it means less than the immediate
    # demand as the production can be sold to
    # other industries later on
    discount_rate = plant.cost_of_capital.get()

    # define the timeline at which to
    # evaluate the future multipliers
    evaluation_timeline = _get_plant_evaluation_timeline(plant, timeline, idx)

    # extract the yearly production from a single plant
    production = expectation.get_production(idx)

    # recalculate the fair share of the
    # demand for the fuel the plant can
    # produce to fit with a business cost
    # flow length
    fuel = plant.fuel
    fuel_name = fuel.name
    lhv = fuel.lower_heating_value.get()
    demand_int = np.interp(evaluation_timeline, timeline, demand[fuel_name], left=0.0)

    # calculate the maximum equivalent
    # multipliers over time
    demand_multipliers = demand_int / production

    # calculate the maximum number of multipliers
    # which merit sufficient offtake
    lifetime = plant.lifetime.get()

    if minimum_offtake_duration is not None:
        minimum_duration = minimum_offtake_duration.get()
    else:
        minimum_duration = lifetime

    # the lowest equivalent multiplier within
    # the sufficient offtake duration is used
    # as maximum number of plants which it
    # makes sense to sanction
    to_ = min(min(ceil(minimum_duration), ceil(lifetime)), demand_int.size)
    demand_newbuilds = max(np.amin(demand_multipliers[:to_]), 0)

    # calculate the age-levelized demand (energy-based)
    demand_energy = demand_int * lhv
    metric = calculate_age_levelized_cost(demand_energy, lifetime, discount_rate)

    # assign to expectations
    expectation.set_demand_newbuilds(demand_newbuilds)
    expectation.set_inter_fuel_metric(metric)


def _calculate_uptake_intra_metric(plant, export_distribution, idx):
    """
    Calculate the business-case metric used to choose a plant within a fuel pathway.

    This is based on the average delivered levelized cost of fuel for a given plant.

    Parameters
    ----------
    plant : Plant
         Plant for which intra uptake metric is being calculated.
    export_distribution : dict[str, float]
        Fraction of fuel production that is exported to each port.
    idx : int
        Current time-step index.
    """
    expectation = plant.expectation

    # calculate the average exported levelized
    # delivery cost across ports
    metric = 0.0

    for port_name, export in export_distribution.items():
        lcof = expectation.get_levelized_delivered_cost(port_name, idx)
        metric += export * lcof

    expectation.set_intra_fuel_metric(metric)


def _get_plant_evaluation_timeline(plant, timeline, idx):
    """
    Build the timeline at which cash flows should be evaluated.

    Parameters
    ----------
    plant : Plant
        Plant for which evaluation timeline is built.
    timeline : np.ndarray
        Simulation timeline.
    idx : int
        Current time-step index.

    Returns
    -------
    np.ndarray
        Evaluation timeline.
    """
    lifetime = plant.lifetime.get()
    lead_time = plant.lead_time.get()

    return (
        np.arange(ceil(lead_time), ceil(lifetime + lead_time), dtype=np.float64) * YEAR
        + timeline[idx]
    )


def calculate_inertia_increments(producer: Producer, time_step, idx):
    """
    Calculate the increments being built due to inertia from previous uptake.

    Parameters
    ----------
    producer
        The producer.
    time_step : float
        Current time-step size.
    idx : int
        Current time-step index.

    Returns
    -------
    np.ndarray
        Inertia-based increments per plant type.
    """
    # reduce the current uptake shares by the
    # inertia prior to calculating inertia
    # related newbuilds. This is done here
    # to ensure it occurs at every time-step
    producer.current_uptake *= calculate_inertia(producer.inertia.get(), time_step)

    # adjust the current uptake to account for disallowed plants
    for p, plant in enumerate(producer.assets):
        if not producer.allow_plant[plant.name]:
            producer.current_uptake[p] = 0.0

    # inertia only happens if the producer is development constrained
    increments = np.zeros((len(producer.assets),))

    # calculate the possible development capacity
    # accounting for the utilization from last year
    maximum_development = (
        producer.current_utilization
        * producer.maximum_development.get()
        * time_step
        / YEAR
    )

    if maximum_development > 0.0:
        # extract the maximum number of newbuild
        # plants that may enter the pipeline
        demand_multipliers = np.array(
            [
                plant.expectation.get_demand_newbuilds()
                if producer.allow_plant[plant.name]
                else 0.0
                for plant in producer.assets
            ]
        )

        # calculate maximum possible share
        # based on demanded multipliers
        demand_limits = np.array(
            [
                min(multiplier / maximum_development, 1.0)
                for multiplier in demand_multipliers
            ]
        )

        # adjust the uptake shares to account for feed constraints
        uptake = producer.current_uptake
        constrained_uptake = calculate_constrained_uptakes(
            producer, uptake, maximum_development, demand_limits, idx
        )

        # calculate the inertia-based increments
        increments = constrained_uptake * maximum_development

        # subtract the feed consumption
        # from the inertia based increments
        # from the feed gap
        for feed_name, constraint in producer.feed_constraints.items():
            if constraint is None:
                continue

            added_consumption = 0.0

            for p, plant in enumerate(producer.assets):
                plant_name = plant.name

                # calculate the feed used per plant
                consumption = producer.expectation.get_plant_feed_consumption(
                    plant_name, feed_name
                )
                added_consumption += consumption * increments[p]

            original_gap = producer.expectation.get_feed_gap(feed_name, idx)
            new_gap = original_gap - added_consumption
            producer.expectation.set_feed_gap(idx, feed_name, new_gap)

    return increments


def calculate_modelled_uptake(producer: Producer) -> np.ndarray:
    """
    Calculate each plant type's relative uptake share.

    Uses a two-axis discrete choice model grouped by fuel pathway.

    Parameters
    ----------
    producer
        The producer.

    Returns
    -------
    np.ndarray
        Uptake shares per plant type.
    """
    # extract allowed plants and index map
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
        # if none of the plants are in demand, the zip
        # fails which means there should be no uptake
        return np.zeros((len(producer.assets),))

    index = np.array(index)

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

    # pad the uptake shares back to the original length
    uptake_padded = np.zeros(len(producer.assets))

    for i, p in enumerate(index):
        uptake_padded[p] = uptake[i]

    return uptake_padded


def calculate_constrained_uptakes(
    producer: Producer, uptakes, development, limits, idx, additional_consumption=None
):
    """
    Constrain uptake shares iteratively to respect feed availability.

    Parameters
    ----------
    producer
        The producer.
    uptakes : np.ndarray
        Desired uptake-shares if the model is unconstrained.
    development : float
        Number of plants built per year.
    limits : np.ndarray
        An array of uptake limits for each plant.
    idx : int
        Current time-step index.
    additional_consumption : dict[str, float]
        Potential additional consumption at the given time-step index.

    Returns
    -------
    np.ndarray
        Uptake-shares adhering to the feed constraint at the specified amount of
        development.
    """
    # TODO: make it assignable
    tolerance = 1e-3

    # iterative over
    current_uptakes = uptakes
    converged = False

    while not converged:
        # calculate limits based on
        # the available feed
        new_limits = calculate_feed_uptake_limit_iteration(
            producer, development, current_uptakes, idx, additional_consumption
        )

        # the feed uptake limits are not
        # allowed to be less restrictive than
        # the demand based on uptakes
        new_limits = np.minimum(new_limits, limits)

        # calculate the constrained uptake
        # shares based on the maximum allowable
        # share of each plant related to the
        # supply/demand gap
        new_uptakes, _utilization = _calculate_constrained_shares(uptakes, new_limits)

        # if there is no change in uptakes from
        # the previous iteration the algorithm
        # has converged
        if np.sum(np.abs(current_uptakes - new_uptakes)) < tolerance:
            converged = True

        current_uptakes = new_uptakes

    return current_uptakes


def _calculate_constrained_shares(shares, maximums):
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
    shares : np.ndarray
        Uptake shares across all options, must sum to unity.
    maximums : np.ndarray
        Maximum possible share for each option. Does not need to sum to unity.

    Returns
    -------
    tuple[np.ndarray, float]
        Constrained uptake shares and the utilization share if the problem is
        over-constrained.
    """
    surplus = np.maximum(shares - maximums, 0.0)
    deficit = np.maximum(maximums - shares, 0.0)

    unutilized = max(1.0 - np.sum(maximums), 0.0)

    fraction = min(divide_nonzero(np.sum(surplus), np.sum(deficit)), 1.0)

    has_surplus = surplus > 0.0
    constrained_shares = np.where(has_surplus, maximums, shares + deficit * fraction)

    return constrained_shares, 1.0 - unutilized


def calculate_feed_uptake_limit_iteration(
    producer: Producer, development, uptakes, idx, additional_consumption=None
):
    """
    Calculate feed-based uptake limits for a single iteration.

    Parameters
    ----------
    producer
        The producer.
    development : float
        Number of plants built per year.
    uptakes : np.ndarray
        Uptakes-shares for the given iteration.
    idx : int
        Current time-step index.
    additional_consumption : dict[str, float]
        Potential additional consumption at the given time-step index.
    """
    if additional_consumption is None:
        additional_consumption = {}

    spend_map = {}
    total_spend = {}

    for feed_name, constraint in producer.feed_constraints.items():
        if constraint is None:
            continue

        additional_consumption.setdefault(feed_name, 0.0)
        total_spend.setdefault(feed_name, 0.0)

        for p, plant in enumerate(producer.assets):
            key = (plant.name, feed_name)
            consumption = producer.expectation.get_plant_feed_consumption(*key)

            # calculate the feed use that would
            # happen if building according to the
            # current uptake shares
            spend = consumption * uptakes[p] * development
            spend_map[key] = spend

            # save the total feed that would be used
            # if the current uptake shares were kept
            total_spend[feed_name] += spend

    # scale the possible spend per plant and feed
    for feed_name, spend in total_spend.items():
        if not spend > 0.0:
            continue

        gap = (
            producer.expectation.get_feed_gap(feed_name, idx)
            - additional_consumption[feed_name]
        )
        scaling = max(gap / spend, 0.0)

        for _p, plant in enumerate(producer.assets):
            key = (plant.name, feed_name)

            if scaling == np.inf:
                spend_map[key] = np.inf
            else:
                spend_map[key] *= scaling

    # for each plant calculate the most
    # restrictive feed constraint
    # and update the uptake shares based
    # on that
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

            # back-calculate uptake with the scaled spend
            new_limit = spend_map[key] / consumption

            # find the most restrictive uptake
            current_limit = min(current_limit, new_limit)

        limits[p] = current_limit

    return limits
