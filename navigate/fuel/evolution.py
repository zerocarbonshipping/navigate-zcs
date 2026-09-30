# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Producer evolution: decommissioning, delivery, feed availability and outlook."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.increment import PlantIncrement
from navigate.fuel.planning import (
    calculate_constrained_uptakes,
    perform_pipeline_planning,
)
from navigate.util import (
    TOLERANCE,
    YEAR,
    divide_nonzero,
    get_increment_origin_indexes,
    slice_dict,
)

if TYPE_CHECKING:
    from collections.abc import Collection

    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray, IntArray

logger = logging.getLogger(__name__)


def _accumulate_weighted_cost(
    incs: list[PlantIncrement],
    plant: Plant,
    origins: IntArray,
    production: FloatArray,
    today: float,
    times: FloatArray,
    emissions: Collection[str],
    p: int,
    cost: FloatArray,
    weight: FloatArray,
    wtt: dict[str, FloatArray],
) -> None:
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
        interval = _calculate_increment_production_interval(
            total_production, delivery, decommission, inc.age_span * YEAR, times
        )

        cost[p, :] += interval * expectation.get_levelized_production_cost(origins[i])
        weight[p, :] += interval

        for e in emissions:
            wtt[e][p, :] += interval * expectation.get_production_wtt(e, origins[i])


def _calculate_increment_production_interval(
    production: float,
    delivery: float,
    decommission: float,
    time_step: float,
    times: FloatArray,
) -> FloatArray:
    """
    Calculate the production profile over time for a single increment.

    Parameters
    ----------
    production
        Production that will enter at the delivery date (sum of all plants being
        delivered), tons/year.
    delivery
        Time at which production was or will be delivered, days.
    decommission
        Time at which production will be decommissioned, days.
    time_step
        Time-step duration over which production was or will be delivered, days.
    times
        Future times from the simulation timeline (timeline[idx:]), days.

    Returns
    -------
    FloatArray
        The production active at each of the times, tons/year.
    """
    # ignore small increments to avoid round-off issues
    tol = 1e-5

    end = times[-1]
    output = np.zeros_like(times)

    time_delivery = delivery - time_step
    delivery_period = time_step

    if delivery <= 0.0:
        # an existing increment is already delivered, so all its production is
        # assigned at t=0
        output[0] = production

    else:
        # the plants are delivered continuously over the time step, the first in
        # 'delivery - time_step' time
        t_delivery = np.argmax(time_delivery < times)

        while delivery_period > tol:
            if time_delivery >= end:
                break

            end_point = np.minimum(times[t_delivery], delivery)
            partial = end_point - time_delivery
            scaling = partial / time_step
            output[t_delivery] = scaling * production

            t_delivery += 1
            time_delivery += partial
            delivery_period -= partial

    # the plants are decommissioned continuously over the time step, the first in
    # 'decommission - time_step' time
    time_decommission = decommission - time_step
    t_decom = np.argmax(time_decommission < times)
    decommission_period = time_step

    while decommission_period > tol:
        # the end of the simulation also covers decommissioning beyond the timeline
        if time_decommission >= end:
            break

        end_point = np.minimum(times[t_decom], decommission)
        partial = end_point - time_decommission
        scaling = partial / time_step

        # subtract rather than assign, as the time step may also hold part of the
        # increment's delivery
        output[t_decom] -= scaling * production

        t_decom += 1
        time_decommission += partial
        decommission_period -= partial

    return np.cumsum(output)


def _calculate_increments_production(
    incs: list[PlantIncrement],
    production: FloatArray,
    lifetime: float,
    today: float,
    times: FloatArray,
) -> FloatArray:
    """
    Calculate the combined production profile of a set of increments over time.

    Each increment enters and exits uniformly over its age span, as pipeline
    delivery and decommissioning move it.

    Parameters
    ----------
    incs
        Increments of one plant type, delivered or in the pipeline.
    production
        Production per plant of each increment, tons/year.
    lifetime
        Lifetime of the plant, years.
    today
        Current time, days.
    times
        Future times from the simulation timeline (timeline[idx:]), days.

    Returns
    -------
    FloatArray
        Production at each of the times, tons/year.
    """
    total = np.zeros_like(times)

    for inc, plant_production in zip(incs, production, strict=True):
        delivery = today - inc.age * YEAR
        decommission = delivery + lifetime * YEAR

        total += _calculate_increment_production_interval(
            plant_production * inc.multiplier,
            delivery,
            decommission,
            inc.age_span * YEAR,
            times,
        )

    return total


def perform_decommissioning(producer: Producer) -> None:
    """
    Decommission increments that have exceeded their asset's lifetime.

    Parameters
    ----------
    producer
        The producer instance.
    """
    for a, asset in enumerate(producer.assets):
        incs = producer.increments[a]
        lifetime = asset.lifetime.get()

        producer.increments[a] = [inc for inc in incs if inc.age < lifetime]

        # partially decommission increments whose age_span spans the lifetime boundary
        for inc in producer.increments[a]:
            if inc.age + inc.age_span > lifetime:
                alpha = (lifetime - inc.age) / inc.age_span
                decommissioning = inc.multiplier * (1.0 - alpha)

                inc.multiplier -= decommissioning
                inc.age_span = lifetime - inc.age


def calculate_evolution_expectation(
    producer: Producer, timeline: FloatArray, idx: int
) -> None:
    """
    Calculate the expected future evolution of production.

    Covers existing plants, the pipeline, and newbuilds.

    Parameters
    ----------
    producer
        The producer.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    idx_ = np.s_[idx:]
    years = timeline / YEAR
    times = timeline[idx_]
    today = times[0]

    if idx == 0:
        time_steps = np.insert((timeline[1:] - timeline[:-1]), 0, YEAR)
    else:
        time_steps = timeline[idx:] - timeline[idx - 1 : -1]

    year_steps = time_steps / YEAR

    n = len(producer.assets)

    # every plant carries the same emissions, so an arbitrary one names them
    emissions = producer.assets[0].expectation.get_emissions() if n > 0 else []

    cost = np.zeros((n, times.size))
    wtt = {emission_name: np.zeros((n, times.size)) for emission_name in emissions}
    weight = np.zeros((n, times.size))

    existing = np.zeros((n, times.size))

    for p, plant in enumerate(producer.assets):
        incs = producer.increments[p]
        if not len(incs):
            continue

        decided = np.array([inc.decided for inc in incs])
        origins = get_increment_origin_indexes(years, years[idx], decided)
        production = np.asarray(plant.expectation.get_production(origins))

        existing[p, :] = _calculate_increments_production(
            incs, production, plant.lifetime.get(), today, times
        )

        _accumulate_weighted_cost(
            incs,
            plant,
            origins,
            production,
            today,
            times,
            emissions,
            p,
            cost,
            weight,
            wtt,
        )

    pipeline = np.zeros((n, times.size))

    for p, plant in enumerate(producer.assets):
        pinc = producer.pipeline[p]
        if not len(pinc):
            continue

        decided = np.array([inc.decided for inc in pinc])
        origins = get_increment_origin_indexes(years, years[idx], decided)
        production = np.asarray(plant.expectation.get_production(origins))

        pipeline[p, :] = _calculate_increments_production(
            pinc, production, plant.lifetime.get(), today, times
        )

        _accumulate_weighted_cost(
            pinc,
            plant,
            origins,
            production,
            today,
            times,
            emissions,
            p,
            cost,
            weight,
            wtt,
        )

    # without initial production the supply/demand interaction never starts, as
    # no supply is expected and thus no demand; a partially uniform uptake
    # expectation weighted by the jump-start fraction starts it
    allowed = np.array(
        [producer.allow_plant[plant.name] for plant in producer.assets], dtype=bool
    )
    total = np.count_nonzero(allowed)
    uniform = np.zeros_like(producer.current_uptake)
    uniform[allowed] = 1.0 / total

    jump_start = producer.jump_start_fraction.get()
    uptakes = (1.0 - jump_start) * producer.current_uptake + jump_start * uniform

    uptake_limits = np.zeros_like(uptakes)
    uptake_limits[allowed] = 1.0

    # likewise, without previous development the expectation needs a minimum of
    # development potential to jump-start production
    if producer.current_utilization > 0.0:
        utilization = producer.current_utilization
    else:
        utilization = jump_start

    newbuild = np.zeros((n, times.size))
    feed_consumption = {
        feed_name: np.zeros_like(times) for feed_name in producer.feed_constraints
    }

    for t, time in enumerate(times):
        # t=0 is already in the pipeline from the current time step's planning
        if t == 0:
            continue

        time_step = time_steps[t]
        year_step = year_steps[t]

        # the utilization is only accounted for if the model is ramp-up
        # constrained; otherwise the model cannot increase the utilization over
        # time when the demand equals the supply
        ramp_up = producer.maximum_ramp_up.get(time) * year_step
        utilization = min(utilization + ramp_up, 1.0)

        maximum_development = (
            utilization * producer.maximum_development.get(time) * year_step
        )
        consumption = slice_dict(feed_consumption, t)

        constrained_uptakes = calculate_constrained_uptakes(
            producer,
            uptakes,
            maximum_development,
            uptake_limits,
            idx + t,
            additional_consumption=consumption,
        )

        for p, plant in enumerate(producer.assets):
            lifetime = plant.lifetime.get(time)
            lead_time = plant.lead_time.get(time)

            # the delivery and decommission times of the last expected increment,
            # as increments enter uniformly over the time step
            delivery = time + lead_time * YEAR
            decommission = delivery + lifetime * YEAR

            # the production capacity of a plant is locked when it is decided, not
            # when it is delivered, so production is read at time 't'
            expectation = plant.expectation
            plant_production = float(expectation.get_production(idx + t))
            total_production = (
                maximum_development * constrained_uptakes[p] * plant_production
            )

            newbuild_production = _calculate_increment_production_interval(
                total_production, delivery, decommission, time_step, times
            )
            newbuild[p, :] += newbuild_production

            newbuild_cost = expectation.get_levelized_production_cost(idx + t)
            cost[p, :] += newbuild_production * newbuild_cost
            weight[p, :] += newbuild_production

            for e in emissions:
                newbuild_wtt = expectation.get_production_wtt(e, idx + t)
                wtt[e][p, :] += newbuild_production * newbuild_wtt

            conversions = expectation.get_feed_masses(idx + t)
            for feed_name, conversion in conversions.items():
                # the feed gap moves everything forward by the lead time: it is the
                # gap of what can enter the pipeline at 't', not the gap at
                # 't + lead_time'
                feed_consumption[feed_name][t:] += total_production * conversion

    cost_avg = divide_nonzero(cost, weight)
    wtt_avg = {
        emission_name: divide_nonzero(unit_wtt, weight)
        for emission_name, unit_wtt in wtt.items()
    }

    for p, plant in enumerate(producer.assets):
        producer.expectation.set_existing_production(idx, plant.name, existing[p, :])
        producer.expectation.set_pipeline_production(idx, plant.name, pipeline[p, :])
        producer.expectation.set_newbuild_production(idx, plant.name, newbuild[p, :])

    supply = existing[:, 0] + pipeline[:, 0] + newbuild[:, 0]

    for p, plant in enumerate(producer.assets):
        plant.expectation.set_expected_production_cost(idx, cost_avg[p, :])

        for e in plant.expectation.get_emissions():
            plant.expectation.set_expected_production_wtt(idx, e, wtt_avg[e][p, :])

    for p, plant in enumerate(producer.assets):
        if supply[p] > TOLERANCE:
            plant.profile.set_instantaneous_cost(idx, cost_avg[p, 0])

            for e in plant.expectation.get_emissions():
                plant.profile.set_instantaneous_wtt(idx, e, wtt_avg[e][p, 0])


def perform_pipeline_delivery(producer: Producer) -> None:
    """
    Deliver plants from the pipeline that have passed their lead time.

    Pipeline increments use negative ages (time since delivery, negative = not yet
    delivered). After aging with += dt, delivered increments have age >= 0 and
    transfer directly to active production without sign-flipping.

    Parameters
    ----------
    producer
        The producer instance.
    """
    for p in range(len(producer.assets)):
        pinc = producer.pipeline[p]
        incs = producer.increments[p]
        last_idx = None

        for i in range(len(pinc)):
            pinc_i = pinc[i]
            increment = pinc_i.multiplier

            if pinc_i.age >= 0.0:
                # fully delivered: the age already counts the time since delivery
                incs.append(
                    PlantIncrement(
                        increment, pinc_i.age, pinc_i.age_span, decided=pinc_i.decided
                    )
                )

                last_idx = i

            else:
                # the ongoing increment delivers the part that has crossed zero, as
                # plants enter uniformly over a time step
                if pinc_i.age + pinc_i.age_span > 0.0:
                    alpha = -pinc_i.age / pinc_i.age_span
                    remaining = increment * alpha
                    delivered = increment - remaining
                    delivered_dt = pinc_i.age + pinc_i.age_span

                    # the delivered portion keeps the original 'decided', so its
                    # origin index stays that of the original increment
                    incs.append(
                        PlantIncrement(
                            delivered, 0.0, delivered_dt, decided=pinc_i.decided
                        )
                    )

                    # shrink the pipeline portion and truncate its age span, to keep
                    # the plants entering uniformly
                    pinc_i.multiplier = remaining
                    pinc_i.age_span = -pinc_i.age

        if last_idx is not None:
            producer.pipeline[p] = pinc[(last_idx + 1) :]


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

        for plant in producer.assets:
            expectation = plant.expectation
            current_production = float(expectation.get_production(idx))
            current_conversion = float(expectation.get_feed_mass(feed_name, idx))
            mass = current_production * current_conversion

            producer.expectation.set_plant_feed_consumption(plant.name, feed_name, mass)

    for p, plant in enumerate(producer.assets):
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

        for i in range(start, continued.size):
            increment_i = multipliers[i]
            age_i = ages[i]
            dt_i = incs[i].age_span

            if age_i + dt_i > (lifetime - lead_time):
                alpha = ((lifetime - lead_time) - age_i) / dt_i
                remaining = increment_i * alpha

                existing_increments = np.append(existing_increments, remaining)
                existing_decided = np.append(existing_decided, decided_arr[i])

        # production and feed use are those of when the plants were built
        expectation = plant.expectation
        origins = get_increment_origin_indexes(years, today, existing_decided)
        production = expectation.get_production(origins)
        conversions = expectation.get_feed_masses(origins)

        for feed_name, conversion in conversions.items():
            feed_mass = np.sum(production * conversion * existing_increments)
            producer.expectation.add_existing_feed(feed_name, feed_mass)

    for p, plant in enumerate(producer.assets):
        pinc = producer.pipeline[p]
        if not len(pinc):
            continue

        expectation = plant.expectation

        decided = np.array([inc.decided for inc in pinc])
        multipliers = np.array([inc.multiplier for inc in pinc])

        origins = get_increment_origin_indexes(years, today, decided)
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
            for plant in producer.assets
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


def define_existing_pipeline(producer: Producer, timeline: FloatArray) -> None:
    """
    Define the initial number of plants of each type in the production pipeline.

    Also derives the initial uptake and development-constraint utilization from the
    pipeline counts.

    Parameters
    ----------
    producer
        Producer to define the pipeline for.
    timeline
        Simulation timeline, days.
    """
    for _p in range(len(producer.assets)):
        producer.pipeline.append([])

    for p, (_name, pipeline) in enumerate(producer.existing_pipelines.items()):
        if pipeline is None:
            continue

        planned_delivery = pipeline.x
        planned_capacity = pipeline.y

        # interpolating on the timeline makes the deliveries overlap the
        # simulation dates exactly
        planned_capacity = np.interp(timeline, planned_delivery, planned_capacity)

        incremental_delivery = timeline / YEAR
        incremental_capacity = np.insert(
            np.diff(planned_capacity), 0, planned_capacity[0]
        )

        non_zeros = incremental_capacity > 0.0
        incremental_delivery = incremental_delivery[non_zeros]
        incremental_capacity = incremental_capacity[non_zeros]

        # the first increment is assumed to have entered over a year
        incremental_dt = np.insert(np.diff(incremental_delivery), 0, 1.0)

        plant = producer.assets[p]
        capacity = plant.capacity.get()
        incremental_plants = incremental_capacity / capacity

        # a project was decided one lead time before its delivery
        lead_time = plant.lead_time.get()

        # the pipeline uses negative ages, as its plants are not yet delivered
        producer.pipeline[p] = [
            PlantIncrement(multiplier=m, age=-d, age_span=t, decided=lead_time - d)
            for m, d, t in zip(
                incremental_plants, incremental_delivery, incremental_dt, strict=True
            )
        ]

        producer.profile.set_development(0, np.sum(incremental_plants))

    # the current uptake is an inertia-weighted average over the pipeline
    n = len(producer.assets)
    sum_weights = 0.0
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
        weights = inertia ** (np.maximum(lead_time + ages, 0.0))

        uptake[p] = np.dot(multipliers, weights)
        sum_weights += np.sum(weights)

    producer.current_uptake = divide_nonzero(
        uptake, np.sum(uptake), default=1.0 / uptake.size
    )

    # the latest value of the development constraint is used, since the period
    # to average it back over is hard to define: the pipeline and the lead time
    # are inconsistent, and the lead time varies between plants
    maximum_development = producer.maximum_development.get()
    average_development = divide_nonzero(np.sum(uptake), sum_weights)

    producer.current_utilization = min(
        float(divide_nonzero(average_development, maximum_development)), 1.0
    )


def calculate_export_expectation(
    producer: Producer, timeline: FloatArray, idx: int
) -> None:
    """
    Calculate the producer's expected export distribution over the remaining timeline.

    Parameters
    ----------
    producer
        Producer to calculate the export distribution for.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    times = timeline[idx:]

    if not producer.export_distribution:
        return

    exports = {
        port_name: export.get(times)
        for port_name, export in producer.export_distribution.items()
    }
    norm = sum(exports.values())

    # default to equal export distribution if nothing is defined
    default = 1.0 / len(producer.export_distribution)

    for port_name, export in exports.items():
        producer.expectation.set_export_distribution(
            idx, port_name, divide_nonzero(export, norm, default=default)
        )


def perform_progression(producer: Producer, timeline: FloatArray, idx: int) -> None:
    """
    Progress the existing production in time.

    Covers decommissioning, pipeline delivery, and the resulting feed availability.

    Parameters
    ----------
    producer
        The producer instance.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    perform_decommissioning(producer)
    perform_pipeline_delivery(producer)
    calculate_feed_availability(producer, timeline, idx)


def perform_planning(
    producer: Producer, timeline: FloatArray, time_step: float, idx: int
) -> None:
    """
    Plan new plants into the pipeline from the fuel supply/demand gap.

    Also refreshes the evolution expectation used to quantify the next gap.

    Parameters
    ----------
    producer
        The producer instance.
    timeline
        Simulation timeline, days.
    time_step
        Current time-step size, days.
    idx
        Current time-step index.
    """
    perform_pipeline_planning(producer, timeline, time_step, idx)

    # the feed gap is updated again before the evolution expectation, to account
    # for the plants just added to the pipeline
    calculate_feed_availability(producer, timeline, idx)
    calculate_evolution_expectation(producer, timeline, idx)
