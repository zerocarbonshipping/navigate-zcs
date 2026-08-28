# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import UtilityID
from navigate.core.increment import Increment
from navigate.economics.decision import calculate_two_axis_uptake
from navigate.fuel.utils import (
    calculate_constrained_shares,
    calculate_uptake_inter_metric,
    calculate_uptake_intra_metric,
)
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
        calculate_uptake_inter_metric(plant, demand, producer.minimum_offtake_duration, timeline, idx)
        calculate_uptake_intra_metric(plant, export_distribution, idx)

    # extract the maximum number of newbuild
    # plants that may enter the pipeline
    demand_multipliers = np.array([plant.expectation.get_demand_newbuilds()
                                   if producer.allow_plant[plant.name] else 0.
                                   for plant in producer.assets])

    # calculate the modelled increments of each plant
    model_increments = np.zeros_like(inertia_increments)
    maximum_development = producer.maximum_development.get() * time_step / YEAR

    # constrain the development by
    # the maximum increase fraction
    ramp_up = producer.maximum_ramp_up.get()
    maximum_increase = min(producer.current_utilization + ramp_up, 1.)
    maximum_development *= maximum_increase

    # remove the already added inertia-based increments
    maximum_development -= np.sum(inertia_increments)

    if maximum_development > 0.:

        # calculate the optimal shares
        # based on investment metrics
        modelled_uptakes = calculate_modelled_uptake(producer)

        # calculate maximum possible share
        # based on demanded multipliers
        demand_limits = np.array([min(multiplier / maximum_development, 1.) for multiplier in demand_multipliers])

        # calculate the maximum allowable share
        # based on the available feed and
        # accounting for maximum plant demand
        constrained_uptakes = calculate_constrained_uptakes(producer, modelled_uptakes,
                                                            maximum_development, demand_limits, idx)

        # calculate the model increments
        model_increments = maximum_development * constrained_uptakes

    # add the inertia and modelled increments together
    increments = np.add(inertia_increments, model_increments)

    # define the utilization for use in the next time-step
    producer.current_utilization = divide_nonzero(
        np.sum(increments), producer.maximum_development.get() * time_step / YEAR)

    # add increments to the pipeline
    dt = time_step / YEAR

    for p, plant in enumerate(producer.assets):

        if increments[p] == 0.:
            continue

        lead_time = plant.lead_time.get()

        # insert into the descending-sorted pipeline
        # at the correct position for the new lead time
        pinc = producer.pipeline[p]
        new_age = -lead_time

        if len(pinc):
            ages = np.array([inc.age for inc in pinc])
            i = int(np.searchsorted(-ages, -new_age, side='right'))
        else:
            i = 0

        pinc.insert(i, Increment(increments[p], new_age, dt, decided=0.))

    # assign total development to profile
    total_increments = np.sum(increments)
    producer.profile.set_development(idx, total_increments)

    # set current uptake
    producer.current_uptake = divide_nonzero(increments, total_increments, default=1. / increments.size)


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
            producer.current_uptake[p] = 0.

    # inertia only happens if the producer is development constrained
    increments = np.zeros((len(producer.assets),))

    # calculate the possible development capacity
    # accounting for the utilization from last year
    maximum_development = producer.current_utilization * producer.maximum_development.get() * time_step / YEAR

    if maximum_development > 0.:

        # extract the maximum number of newbuild
        # plants that may enter the pipeline
        demand_multipliers = np.array([plant.expectation.get_demand_newbuilds()
                                       if producer.allow_plant[plant.name] else 0.
                                       for plant in producer.assets])

        # calculate maximum possible share
        # based on demanded multipliers
        demand_limits = np.array([min(multiplier / maximum_development, 1.) for multiplier in demand_multipliers])

        # adjust the uptake shares to account for feed constraints
        uptake = producer.current_uptake
        constrained_uptake = calculate_constrained_uptakes(producer, uptake, maximum_development, demand_limits, idx)

        # calculate the inertia-based increments
        increments = constrained_uptake * maximum_development

        # subtract the feed consumption
        # from the inertia based increments
        # from the feed gap
        for feed_name, constraint in producer.feed_constraints.items():

            if constraint is None:
                continue

            added_consumption = 0.

            for p, plant in enumerate(producer.assets):

                plant_name = plant.name

                # calculate the feed used per plant
                consumption = producer.expectation.get_plant_feed_consumption(plant_name, feed_name)
                added_consumption += consumption * increments[p]

            original_gap = producer.expectation.get_feed_gap(feed_name, idx)
            new_gap = original_gap - added_consumption
            producer.expectation.set_feed_gap(idx, feed_name, new_gap)

    return increments


def calculate_modelled_uptake(producer: Producer) -> np.ndarray:
    """
    Calculate the relative uptake share of each plant type using a two-axis discrete choice model
    grouped by fuel pathway.

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

        index, plants = zip(*((i, plant) for i, plant in enumerate(producer.assets)
                            if producer.allow_plant[plant.name]
                            and plant.expectation.is_in_demand()))

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
    uptake_padded = np.zeros((len(producer.assets)))

    for i, p in enumerate(index):
        uptake_padded[p] = uptake[i]

    return uptake_padded


def calculate_constrained_uptakes(producer: Producer, uptakes, development, limits, idx,
                                  additional_consumption=None):
    """
    Iteratively constrain uptake shares to respect feed availability.

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
        Uptake-shares adhering to the feed constraint at the specified amount of development.
    """

    # TODO: make it assignable
    tolerance = 1e-3

    # iterative over
    current_uptakes = uptakes
    converged = False

    while not converged:

        # calculate limits based on
        # the available feed
        new_limits = calculate_feed_uptake_limit_iteration(producer, development,
                                                           current_uptakes,
                                                           idx,
                                                           additional_consumption)

        # the feed uptake limits are not
        # allowed to be less restrictive than
        # the demand based on uptakes
        new_limits = np.minimum(new_limits, limits)

        # calculate the constrained uptake
        # shares based on the maximum allowable
        # share of each plant related to the
        # supply/demand gap
        new_uptakes, utilization = calculate_constrained_shares(uptakes, new_limits)

        # if there is no change in uptakes from
        # the previous iteration the algorithm
        # has converged
        if np.sum(np.abs(current_uptakes - new_uptakes)) < tolerance:
            converged = True

        current_uptakes = new_uptakes

    return current_uptakes


def calculate_feed_uptake_limit_iteration(producer: Producer, development, uptakes, idx,
                                          additional_consumption=None):
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

        additional_consumption.setdefault(feed_name, 0.)
        total_spend.setdefault(feed_name, 0.)

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

        if not spend > 0.:
            continue

        gap = producer.expectation.get_feed_gap(feed_name, idx) - additional_consumption[feed_name]
        scaling = max(gap / spend, 0.)

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
        current_limit = 1.

        for feed_name in total_spend:

            key = (plant_name, feed_name)
            consumption = producer.expectation.get_plant_feed_consumption(*key) * development

            if not consumption > 0.:
                continue

            # back-calculate uptake with the scaled spend
            new_limit = spend_map[key] / consumption

            # find the most restrictive uptake
            current_limit = min(current_limit, new_limit)

        limits[p] = current_limit

    return limits
