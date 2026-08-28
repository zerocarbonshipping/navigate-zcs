# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from math import ceil
from typing import TYPE_CHECKING

import numpy as np

from navigate.economics.metric import calculate_age_levelized_cost
from navigate.util import YEAR, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.producer import Producer

logger = logging.getLogger(__name__)


def calculate_uptake_inter_metric(plant, demand, minimum_offtake_duration, timeline, idx):
    """
    Calculate the business case evaluation metric which is used to decide on a specific fuel pathway.
    This is based on the expected future gap between supply and demand and the number of plants required
    to satisfy that gap.

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
    evaluation_timeline = get_plant_evaluation_timeline(plant, timeline, idx)

    # extract the yearly production from a single plant
    production = expectation.get_production(idx)

    # recalculate the fair share of the
    # demand for the fuel the plant can
    # produce to fit with a business cost
    # flow length
    fuel = plant.fuel
    fuel_name = fuel.name
    lhv = fuel.lower_heating_value.get()
    demand_int = np.interp(evaluation_timeline, timeline, demand[fuel_name], left=0.)

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


def calculate_uptake_intra_metric(plant, export_distribution, idx):
    """
    Calculate the business case evaluation metric which is used to decide on a specific plant after the fuel pathway
    has been decided.
    This is based on the average delivered levelized cost of fuel for a given plant.

    Parameters
    ----------
    plant : Plant
         Plant for which intra uptake metric is being calculated.
    export_distribution : dict[str, np.ndarray]
        Fraction of fuel production that is exported to each port.
    idx : int
        Current time-step index.
    """

    expectation = plant.expectation

    # calculate the average exported levelized
    # delivery cost across ports
    metric = 0.

    for port_name, export in export_distribution.items():

        lcof = expectation.get_levelized_delivered_cost(port_name, idx)
        metric += export * lcof

    expectation.set_intra_fuel_metric(metric)


def get_plant_evaluation_timeline(plant, timeline, idx):
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

    return np.arange(ceil(lead_time), ceil(lifetime + lead_time), dtype=np.float64) * YEAR + timeline[idx]


def calculate_constrained_shares(shares, maximums):
    """
    This methods takes the optimal allocation from a discrete choice model and redistributes the shares between
    the options if certain allocations are larger than their maximum allowed share.

    Notice that this method redistributes the surplus from constrained shares to the other shares proportionally to
    the deficit of each share. Meaning the bigger the gap to the maximum the larger the fraction of the surplus it
    receives.

    TODO: Is this desired or should it be a perfectly equal share between the buckets with deficit?
    TODO: This probably requires an iterative algorithm to ensure redistribution does not break maximums.

    Parameters
    ----------
    shares : np.ndarray
        Uptake shares across all options, must sum to unity.
    maximums : np.ndarray
        Maximum possible share for each option. Does not need to sum to unity.

    Returns
    -------
    tuple[np.ndarray, float]
        Constrained uptake shares and the utilization share if the problem is over-constrained.
    """

    surplus = np.maximum(shares - maximums, 0.)
    deficit = np.maximum(maximums - shares, 0.)

    unutilized = max(1. - np.sum(maximums), 0.)

    fraction = min(divide_nonzero(np.sum(surplus), np.sum(deficit)), 1.)

    has_surplus = surplus > 0.
    constrained_shares = np.where(has_surplus, maximums, shares + deficit * fraction)

    return constrained_shares, 1. - unutilized


def calculate_increment_production_interval(production, delivery, decommission, time_step, times):
    """
    Calculate the production profile over time for a single increment.

    Parameters
    ----------
    production : float
        Production that will enter at the delivery date (sum of all plants being delivered).
    delivery : float
        Time at which production was or will be delivered.
    decommission : float
        Time at which production will be decommissioned.
    time_step : float
        Time-step duration over which production was or will be delivered.
    times : np.ndarray
        Future times from the simulation timeline (timeline[idx:]).

    Returns
    -------
    np.ndarray
        The period over which production will be active and the amount of production.
    """

    # ignore small increments to avoid round-off issues
    tol = 1e-5

    end = times[-1]
    output = np.zeros_like(times)

    time_delivery = delivery - time_step
    delivery_period = time_step

    if delivery <= 0.:

        # if delivery is negative it is because it is an existing
        # increment which has already been delivered and thus all
        # production is assigned at t=0
        t_delivery = 0
        output[t_delivery] = production

    else:

        # the plants are delivered continuously over the
        # length of the time-step with the first being
        # delivered in 'delivery - time_step' time
        t_delivery = np.argmax(time_delivery < times)

        while delivery_period > tol:

            # respect end of simulation boundary
            if time_delivery >= end:
                break

            # calculate the fraction of production being
            # delivered in the given time-step
            end_point = np.minimum(times[t_delivery], delivery)
            partial = end_point - time_delivery
            scaling = partial / time_step

            # calculate the expected production
            # entering over the given time-step
            output[t_delivery] = scaling * production

            # update for next step in sequential allocation
            t_delivery += 1
            time_delivery += partial
            delivery_period -= partial

    # the plants are decommissioned continuously over
    # the length of the time-step with the first being
    # decommissioned in 'decommission - time_step' time
    t_decom = np.argmax((decommission - time_step) < times)

    # argmax returns -1 if decommission is
    # never outside the timeline in which
    # case decommission does not happen
    if t_decom > t_delivery:

        time_decommission = decommission - time_step
        decommission_period = time_step

        while decommission_period > tol:

            # respect end of simulation boundary
            if time_decommission >= end:
                break

            # calculate the fraction of production being
            # delivered in the given time-step
            end_point = np.minimum(times[t_decom], decommission)
            partial = end_point - time_decommission
            scaling = partial / time_step

            # account for future decommissioning
            # of the expected plant
            # if t_decom < times.size:
            output[t_decom] = -scaling * production

            # update for next step in sequential allocation
            t_decom += 1
            time_decommission += partial
            decommission_period -= partial

    return np.cumsum(output)


def calculate_development_potential(producer: Producer, time_step: float, idx: int) -> None:
    """
    Calculate the development potential of the producer per fuel type.

    Parameters
    ----------
    producer
        The producer instance.
    time_step
        Current time-step size.
    idx
        Current time-step index.
    """

    # account for potential ramp-up constraints
    maximum_development = producer.maximum_development.get() * time_step / YEAR
    ramp_up = producer.maximum_ramp_up.get() * time_step / YEAR
    utilization = min(producer.current_utilization + ramp_up, 1.)
    maximum_development *= utilization

    # pre-allocate containers
    potential = {fuel_name: 0. for fuel_name in producer.get_fuels()}

    for plant in producer.assets:

        plant_name = plant.name
        fuel_name = plant.fuel.name
        production = plant.expectation.get_production(idx)

        # if the plant has become disallowed
        # it is removed from consideration
        uptake = 1. if producer.allow_plant[plant_name] else 0.

        # calculate the potential if no
        # feed constraints are included
        if maximum_development < np.inf:
            plant_potential = uptake * maximum_development
        else:
            plant_potential = np.inf

        # loop over feed and reduce the
        # plant potential in case a plant is
        # restricted by feed
        for feed_name, constraint in producer.feed_constraints.items():

            if constraint is None:
                continue

            mass = producer.expectation.get_plant_feed_consumption(plant_name, feed_name)

            if mass == 0.:
                continue

            gap = producer.expectation.get_feed_gap(feed_name, idx)
            potential_multipliers = uptake * gap / mass

            if potential_multipliers < plant_potential:
                plant_potential = potential_multipliers

        # add the plant potential
        potential[fuel_name] += plant_potential * production

    # transfer the development potential per fuel
    for fuel_name in producer.get_fuels():

        # TODO: can easily loop over export distribution to include shares going to ports
        producer.expectation.set_development_potential(fuel_name, potential[fuel_name])
