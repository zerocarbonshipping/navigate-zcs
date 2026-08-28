# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.increment import Increment
from navigate.fuel.planning import calculate_constrained_uptakes
from navigate.fuel.utils import calculate_increment_production_interval
from navigate.util import TOLERANCE, YEAR, divide_nonzero, get_increments_origin_index, slice_dict

if TYPE_CHECKING:
    from navigate.core.nodes.producer import Producer

logger = logging.getLogger(__name__)


def _accumulate_weighted_cost(incs: list[Increment], plant, origins: np.ndarray,
                              production: np.ndarray, today: float, times: np.ndarray,
                              emissions: list, p: int,
                              cost: np.ndarray, weight: np.ndarray,
                              WTT: dict[str, np.ndarray]) -> None:
    """
    Accumulate weighted production cost and emissions for a set of increments.
    Shared by the existing-plant and pipeline sections of the evolution expectation.
    """

    expectation = plant.expectation

    for i, inc in enumerate(incs):

        lifetime = plant.lifetime.get(today - inc.decided * YEAR)
        delivery = today - inc.age * YEAR
        decommission = delivery + lifetime * YEAR

        total_production = production[i] * inc.multiplier
        interval = calculate_increment_production_interval(total_production,
                                                           delivery,
                                                           decommission,
                                                           inc.dt * YEAR,
                                                           times)

        cost[p, :] += interval * expectation.get_levelized_production_cost(origins[i])
        weight[p, :] += interval

        for e in emissions:
            WTT[e][p, :] += interval * expectation.get_production_WTT(e, origins[i])


def perform_decommissioning(producer: Producer, idx: int) -> None:
    """
    Decommission increments that have exceeded their asset's lifetime.

    Parameters
    ----------
    producer
        The producer instance.
    idx
        Current time-step index.
    """

    for a, asset in enumerate(producer.assets):

        incs = producer.increments[a]
        lifetime = asset.lifetime.get()

        # remove all increments past their lifetime
        producer.increments[a] = [inc for inc in incs if inc.age < lifetime]

        # partially decommission increments whose dt spans the lifetime boundary
        for inc in producer.increments[a]:

            if inc.age + inc.dt > lifetime:

                alpha = (lifetime - inc.age) / inc.dt
                decommissioning = inc.multiplier * (1. - alpha)

                inc.multiplier -= decommissioning
                inc.dt = lifetime - inc.age


def calculate_evolution_expectation(producer: Producer, timeline, idx):
    """
    Calculate the expected future evolution of production from existing plants,
    pipeline, and newbuilds.

    Parameters
    ----------
    producer
        The producer.
    timeline : np.ndarray
        Simulation timeline.
    idx : int
        Current time-step index.
    """

    idx_ = np.s_[idx:]
    years = timeline / YEAR
    times = timeline[idx_]
    today = times[0]
    future = (times - today) / YEAR

    if idx == 0:
        time_steps = np.insert((timeline[1:] - timeline[:-1]), 0, YEAR)
    else:
        time_steps = (timeline[idx:] - timeline[idx - 1:-1])

    year_steps = time_steps / YEAR

    n = len(producer.assets)

    # need a list of emissions names which is extracted
    # from the expectation of an arbitrary plant
    emissions = producer.assets[0].expectation.get_emissions() if n > 0 else []

    # pre-allocating containers for calculation of
    # average expected production cost and emissions
    cost = np.zeros((n, times.size))
    WTT = {emission_name: np.zeros((n, times.size)) for emission_name in emissions}
    weight = np.zeros((n, times.size))

    # loop over plant types and subtract
    # expected future decommissioning from the
    # baseline to establish the future baseline
    existing = np.zeros((n, times.size))

    for p, plant in enumerate(producer.assets):

        incs = producer.increments[p]
        if not len(incs):
            continue

        # calculate the production capacity per increment
        decided = np.array([inc.decided for inc in incs])
        multipliers = np.array([inc.multiplier for inc in incs])
        ages = np.array([inc.age for inc in incs])

        origins = get_increments_origin_index(years, years[idx], decided)
        production = plant.expectation.get_production(origins)

        # calculate cumulative decommissioning expectation
        lifetime = plant.lifetime.get()
        cum_production = np.cumsum(multipliers * production)
        cum_decommissioning = np.interp(future, (lifetime - ages), cum_production, left=0.)

        # start the baseline with
        # the current production
        existing[p, :] = np.dot(multipliers, production)

        # subtract from the baseline
        # of current production
        existing[p, :] -= cum_decommissioning

        _accumulate_weighted_cost(incs, plant, origins, production,
                                  today, times, emissions, p, cost, weight, WTT)

    # loop over plant types and add
    # the pipeline to the baseline
    pipeline = np.zeros((n, times.size))

    for p, plant in enumerate(producer.assets):

        pinc = producer.pipeline[p]
        if not len(pinc):
            continue

        lifetime = plant.lifetime.get()

        # calculate the production capacity per increment
        decided = np.array([inc.decided for inc in pinc])
        multipliers = np.array([inc.multiplier for inc in pinc])
        ages = np.array([inc.age for inc in pinc])

        origins = get_increments_origin_index(years, years[idx], decided)
        production = plant.expectation.get_production(origins)

        # calculate cumulative pipeline delivery expectation
        # ages are negative; -ages gives time-to-delivery (ascending)
        cum_production = np.cumsum(multipliers * production)
        cum_pipeline = np.interp(future, -ages, cum_production, left=0.)

        # account for their future decommissioning
        cum_decommissioning = np.interp(future, lifetime - ages, cum_production, left=0.)

        # add the near-term arrival of the pipeline and
        # the long-term decommissioning of the pipeline
        pipeline[p, :] = cum_pipeline - cum_decommissioning

        _accumulate_weighted_cost(pinc, plant, origins, production,
                                  today, times, emissions, p, cost, weight, WTT)

    # if no initial production exists, the supply/demand interaction
    # is never initiated due to no expected supply and thus no expected
    # demand. This is accounted for by introducing a partially uniform
    # uptake expectation weighted by the jump-start fraction
    allowed = np.array([producer.allow_plant[plant.name] for plant in producer.assets], dtype=bool)
    total = np.count_nonzero(allowed)
    uniform = np.zeros_like(producer.current_uptake)
    uniform[allowed] = 1. / total

    jump_start = producer.jump_start_fraction
    uptakes = (1. - jump_start) * producer.current_uptake + jump_start * uniform

    # define the uptake limits when constraining the uptake for feed
    uptake_limits = np.zeros_like(uptakes)
    uptake_limits[allowed] = 1.

    # similarly if no development has previously occurred it
    # is necessary to jump-start the expectation process
    if producer.current_utilization > 0.:
        utilization = producer.current_utilization
    else:
        # a minimum of development potential is required
        # to jump-start production from the producer
        utilization = jump_start

    newbuild = np.zeros((n, times.size))
    feed_consumption = {feed_name: np.zeros_like(times) for feed_name in producer.feed_constraints}

    for t, time in enumerate(times):

        # skip the time-step since t=0 has already been
        # added to the pipeline during the current
        # time-step's pipeline planning
        if t == 0:
            continue

        time_step = time_steps[t]
        year_step = year_steps[t]

        # the utilization is only accounted for if the model
        # is ramp-up constrained. Otherwise, the model is unable
        # to increase the utilization over time in case the
        # demand is equal to the supply
        ramp_up = producer.maximum_ramp_up.get(time) * year_step
        utilization = min(utilization + ramp_up, 1.)

        # calculate the number of plants that can be
        # developed at the given future time-step
        maximum_development = utilization * producer.maximum_development.get(time) * year_step

        # extract the added feed consumption
        # at the given future time-step
        consumption = slice_dict(feed_consumption, t)

        constrained_uptakes = calculate_constrained_uptakes(producer,
                                                            uptakes,
                                                            maximum_development,
                                                            uptake_limits,
                                                            idx + t,
                                                            additional_consumption=consumption)

        for p, plant in enumerate(producer.assets):

            lifetime = plant.lifetime.get(time)
            lead_time = plant.lead_time.get(time)

            # calculate the delivery and the decommission time
            # of the last expected increment, remembering that
            # increments enter uniformly over the time-step
            delivery = time + lead_time * YEAR
            decommission = delivery + lifetime * YEAR

            # production is extracted at time 't' since the
            # production capacity of the plant is locked at
            # the time it is decided to build it, not the
            # day it is delivered
            expectation = plant.expectation
            production = expectation.get_production(idx + t)
            total_production = maximum_development * constrained_uptakes[p] * production

            # calculate the period over which production will exist
            newbuild_production = calculate_increment_production_interval(total_production,
                                                                          delivery,
                                                                          decommission,
                                                                          time_step,
                                                                          times)

            # add the production to the total newbuild production
            newbuild[p, :] += newbuild_production

            # calculate the impact the new production will
            # have on the expected production costs
            newbuild_cost = expectation.get_levelized_production_cost(idx + t)
            cost[p, :] += newbuild_production * newbuild_cost
            weight[p, :] += newbuild_production

            # calculate the impact the new production will
            # have on the expected production emissions
            for e in emissions:

                newbuild_WTT = expectation.get_production_WTT(e, idx + t)
                WTT[e][p, :] += newbuild_production * newbuild_WTT

            # update the additional feed consumption
            # dict to account for what has been added as
            # new production
            conversions = expectation.get_feed_mass(idx=idx + t)
            for feed_name, conversion in conversions.items():

                # the feed gap moves everything forward by
                # 'lead_time' duration to look at the gap of what
                # can be put in the pipeline at 't', not what the
                # gap will be in 't+lead_time' years
                feed_consumption[feed_name][t:] += total_production * conversion

    # normalize the weighted averages by the weight
    cost_avg = divide_nonzero(cost, weight)
    WTT_avg = {emission_name: divide_nonzero(unit_WTT, weight) for emission_name, unit_WTT in WTT.items()}

    # transfer expected production
    for p, plant in enumerate(producer.assets):
        producer.expectation.set_existing_production(idx, plant.name, existing[p, :])
        producer.expectation.set_pipeline_production(idx, plant.name, pipeline[p, :])
        producer.expectation.set_newbuild_production(idx, plant.name, newbuild[p, :])

    supply = existing[:, 0] + pipeline[:, 0] + newbuild[:, 0]

    # transfer expected production cost and emissions
    for p, plant in enumerate(producer.assets):

        plant.expectation.set_expected_production_cost(idx, cost_avg[p, :])

        for e in plant.expectation.get_emissions():
            plant.expectation.set_expected_production_WTT(idx, e, WTT_avg[e][p, :])

    # transfer expectation to profile
    for p, plant in enumerate(producer.assets):

        if supply[p] > TOLERANCE:

            plant.profile.set_instantaneous_cost(idx, cost_avg[p, 0])

            for e in plant.expectation.get_emissions():
                plant.profile.set_instantaneous_WTT(idx, e, WTT_avg[e][p, 0])


def perform_pipeline_delivery(producer: Producer, idx: int) -> None:
    """
    Deliver plants from the pipeline that have passed their lead time.

    Pipeline increments use negative ages (time since delivery, negative = not yet
    delivered). After aging with += dt, delivered increments have age >= 0 and
    transfer directly to active production without sign-flipping.

    Parameters
    ----------
    producer
        The producer instance.
    idx
        Current time-step index.
    """

    for p in range(len(producer.assets)):

        pinc = producer.pipeline[p]
        incs = producer.increments[p]
        last_idx = None

        for i in range(len(pinc)):

            pinc_i = pinc[i]
            increment = pinc_i.multiplier

            if pinc_i.age >= 0.:

                # fully delivered: age already represents
                # time since delivery, no sign-flipping needed
                incs.append(Increment(increment, pinc_i.age, pinc_i.dt,
                                      decided=pinc_i.decided))

                last_idx = i

            else:

                # deliver plants from the ongoing
                # increment if the earliest-entered part
                # has crossed zero (based on an assumption
                # of plants entering uniformly over
                # a time-step)
                if pinc_i.age + pinc_i.dt > 0.:

                    alpha = -pinc_i.age / pinc_i.dt
                    remaining = increment * alpha
                    delivered = increment - remaining
                    delivered_dt = pinc_i.age + pinc_i.dt

                    # add a new increment for the delivered
                    # portion. 'decided' is kept consistent
                    # with the original increment to ensure
                    # later use of origin index remains consistent
                    incs.append(Increment(delivered, 0., delivered_dt,
                                          decided=pinc_i.decided))

                    # shrink the pipeline portion and truncate
                    # the time-step to maintain the assumption
                    # of uniformity
                    pinc_i.multiplier = remaining
                    pinc_i.dt = -pinc_i.age

        # remove the delivered increments from the pipeline
        if last_idx is not None:
            producer.pipeline[p] = pinc[(last_idx + 1):]


def calculate_feed_availability(producer: Producer, timeline, idx) -> None:
    """
    Calculate the gap between feed used in current and pipeline production
    and the available supply.

    Parameters
    ----------
    producer
        The producer instance.
    timeline : np.ndarray
        Simulation timeline.
    idx : int
        Current time-step index.
    """

    # reset additive properties of expectations
    # to prepare for adding up feed demand
    producer.expectation.reset_additive_properties()

    times = timeline[idx:]
    years = timeline / YEAR
    today = years[idx]

    # create a map of the feed used in
    # production per plant and feed
    # this is used later for constraining
    # uptake shares based on feed
    for feed_name, constraint in producer.feed_constraints.items():

        if constraint is None:
            continue

        for plant in producer.assets:

            plant_name = plant.name
            expectation = plant.expectation

            # calculate the feed used per plant
            production = expectation.get_production(idx)
            conversion = expectation.get_feed_mass(feed_name, idx)
            mass = production * conversion

            producer.expectation.set_plant_feed_consumption(plant_name, feed_name, mass)

    # add the existing production currently on stream
    for p, plant in enumerate(producer.assets):

        incs = producer.increments[p]
        if not len(incs):
            continue

        # if the increments will be decommissioned before
        # the new plants are built, they are not counted
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

        # find the index of the first increment which is
        # continued and account for partial decommissioning
        # related to a continuous model
        start = np.argmax(continued)

        for i in range(start, continued.size):

            increment_i = multipliers[i]
            age_i = ages[i]
            dt_i = incs[i].dt

            if age_i + dt_i > (lifetime - lead_time):

                alpha = ((lifetime - lead_time) - age_i) / dt_i
                remaining = increment_i * alpha

                existing_increments = np.append(existing_increments, remaining)
                existing_decided = np.append(existing_decided, decided_arr[i])

        # extract the production capacity and use of
        # feed at the time the plants were built
        expectation = plant.expectation
        origins = get_increments_origin_index(years, today, existing_decided)
        production = expectation.get_production(origins)
        conversions = expectation.get_feed_mass(idx=origins)

        for feed_name, conversion in conversions.items():

            feed_mass = np.sum(production * conversion * existing_increments)
            producer.expectation.add_existing_feed(feed_name, feed_mass)

    # add the planned future production from the pipeline
    for p, plant in enumerate(producer.assets):

        pinc = producer.pipeline[p]
        if not len(pinc):
            continue

        expectation = plant.expectation

        decided = np.array([inc.decided for inc in pinc])
        multipliers = np.array([inc.multiplier for inc in pinc])

        origins = get_increments_origin_index(years, today, decided)
        production = expectation.get_production(origins)
        conversions = expectation.get_feed_mass(idx=origins)

        for feed_name, conversion in conversions.items():

            feed_mass = np.sum(production * conversion * multipliers)
            producer.expectation.add_pipeline_feed(feed_name, feed_mass)

    # calculate the availability gap
    for feed_name, constraint in producer.feed_constraints.items():

        if constraint is None:
            continue

        # calculate the minimum lead time across all plants and
        # use the future constraint for the availability gap.
        # Minimum is used as opposed to average to ensure
        # guaranteed consistency with the constraint
        lead_times = [plant.lead_time.get() for plant in producer.assets
                      if producer.expectation.get_plant_feed_consumption(plant.name, feed_name) > 0.]

        if not lead_times:
            continue

        minimum_lead_time = np.amin(lead_times)

        # calculate future supply
        supply = constraint.get(times + minimum_lead_time * YEAR)

        # calculate demand from existing plants
        # and plants already in the pipeline
        existing = producer.expectation.get_existing_feed(feed_name)
        pipeline = producer.expectation.get_pipeline_feed(feed_name)
        demand = existing + pipeline

        # calculate the supply-demand gap
        gap = supply - demand

        # it is possible to have an over-demand of
        # feed if the model is initialized with
        # an initial capacity of plants which uses
        # more feed than the constraint allows.
        # This is not corrected for internally, but
        # instead flagged via a warning as it indicates
        # an issue in the input data.
        # TODO: Remove if scrapping for negatives gets implemented
        if gap[0] < -TOLERANCE:
            logger.warning("{}: {} tons/year more '{}' feed is being used than is available."
                           .format(producer, round(-gap[0]), feed_name))

            gap = 0.

        producer.expectation.set_feed_gap(idx, feed_name, gap)


def define_existing_pipeline(producer: Producer, timeline: np.ndarray) -> None:
    """
    Define the initial number of plants of each plant type in the production pipeline, and derive
    the initial uptake and development-constraint utilization from it.

    Parameters
    ----------
    producer
        Producer to define the pipeline for.
    timeline
        Simulation timeline.
    """

    # pre-allocate internal pipeline to appropriate length
    for _p in range(len(producer.assets)):
        producer.pipeline.append([])

    for p, (_name, pipeline) in enumerate(producer.existing_pipelines.items()):

        if pipeline is None:
            continue

        # extract the planned capacity
        # and the dates at which it will
        # arrive from the pipeline
        planned_delivery = pipeline.get_x()
        planned_capacity = pipeline.get_y()

        # interpolate with the timeline
        # to ensure exact overlap with
        # simulation dates
        planned_capacity = np.interp(timeline, planned_delivery, planned_capacity)

        # calculate the increments in which
        # the planned capacity arrives
        incremental_delivery = timeline / YEAR
        incremental_capacity = np.insert(np.diff(planned_capacity), 0, planned_capacity[0])

        # remove zero increments
        non_zeros = incremental_capacity > 0.
        incremental_delivery = incremental_delivery[non_zeros]
        incremental_capacity = incremental_capacity[non_zeros]

        # calculate the increment time-step sizes
        # at which increments entered. It is assumed
        # that the first multiplier increment was
        # entered over a year
        incremental_dt = np.insert(np.diff(incremental_delivery), 0, 1.)

        # recalculate incremental capacity
        # to number of plant increments
        plant = producer.assets[p]
        capacity = plant.capacity.get()
        incremental_plants = incremental_capacity / capacity

        # calculate the time since each project was FID'ed
        lead_time = plant.lead_time.get()

        # pipeline uses negative ages (not yet delivered)
        producer.pipeline[p] = [
            Increment(multiplier=m, age=-d, dt=t, decided=lead_time - d)
            for m, d, t in zip(incremental_plants, incremental_delivery, incremental_dt)
        ]

        # assign to profile
        producer.profile.set_development(0, np.sum(incremental_plants))

    # define the current uptake by an inertia
    # based average over the pipeline
    n = len(producer.assets)
    sum_weights = 0.
    uptake = np.zeros((n,), dtype=np.float64)
    inertia = producer.inertia.get()

    for p in range(n):

        pinc = producer.pipeline[p]
        if not len(pinc):
            continue

        # TODO: this may need to be based on continuous compound growth?
        lead_time = producer.assets[p].lead_time.get()
        ages = np.array([inc.age for inc in pinc])
        multipliers = np.array([inc.multiplier for inc in pinc])
        weights = inertia ** (np.maximum(lead_time + ages, 0.))

        uptake[p] = np.dot(multipliers, weights)
        sum_weights += np.sum(weights)

    producer.current_uptake = divide_nonzero(uptake, np.sum(uptake), default=1. / uptake.size)

    # the latest value of the development constraint
    # is used rather than an average over backwards
    # extrapolation. This is done as it difficult to
    # define the backwards period due to inconsistency
    # between pipeline and lead time and the potentially
    # varying lead time of different plants
    maximum_development = producer.maximum_development.get()
    average_development = divide_nonzero(np.sum(uptake), sum_weights)

    producer.current_utilization = min(divide_nonzero(average_development, maximum_development), 1.)


def calculate_export_expectation(producer: Producer, timeline: np.ndarray, idx: int) -> None:
    """
    Calculate the expected export distribution of the producer over the remaining timeline.

    Parameters
    ----------
    producer
        Producer to calculate the export distribution for.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    """

    times = timeline[idx:]

    if not producer.export_distribution:
        return

    # calculate export distribution
    exports = {port_name: export.get(times) for port_name, export in producer.export_distribution.items()}
    norm = sum(exports.values())

    # default to equal export distribution if nothing is defined
    default = 1. / len(producer.export_distribution)

    for port_name, export in exports.items():
        producer.expectation.set_export_distribution(idx, port_name, divide_nonzero(export, norm, default=default))
