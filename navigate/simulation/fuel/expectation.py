# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Expectations producers and ports set for later phases and other domains."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.cohort import find_origin_indexes
from navigate.simulation.fuel.feed import calculate_constrained_uptakes
from navigate.util import (
    MWH_TO_GJ,
    TOLERANCE,
    YEAR,
    divide_nonzero,
    slice_dict,
)

if TYPE_CHECKING:
    from collections.abc import Collection

    from navigate.core.increment import PlantIncrement
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray, IntArray


def calculate_port_expectations(
    ports: dict[str, Port], timeline: FloatArray, idx: int
) -> None:
    """
    Calculate each port's bunkering, handling, overwrite and shore-power expectations.

    Parameters
    ----------
    ports
        All ports in the simulation.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    times = timeline[idx:]

    for port in ports.values():
        _calculate_port_expectation(port, times, idx)


def calculate_export_expectations(
    producers: dict[str, Producer], timeline: FloatArray, idx: int
) -> None:
    """
    Calculate each producer's expected export distribution over the ports.

    Parameters
    ----------
    producers
        All producers in the simulation.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    times = timeline[idx:]

    for producer in producers.values():
        _calculate_export_expectation(producer, times, idx)


def _calculate_port_expectation(port: Port, times: FloatArray, idx: int) -> None:
    """Set the port's limits, costs, overwrites and shore-power terms."""
    expectation = port.expectation

    for key, value in port.bunkering_limit.items():
        if value is not None:
            expectation.set_bunkering_limit(idx, key, value.get(times))

    for key, value in port.handling_cost.items():
        expectation.set_handling_cost(idx, key, value.get(times))

    for key, value in port.bunker_price_overwrite.items():
        if value is not None:
            expectation.set_bunker_price_overwrite(idx, key, value.get(times))

    for key, value in port.bunker_wtt_overwrite.items():
        if value is not None:
            expectation.set_bunker_wtt_overwrite(idx, *key, value.get(times))

    # shore power (convert from USD/MWh to USD/GJ, and ton/MWh to ton/GJ)
    cost = port.shore_power_cost.get(times) / MWH_TO_GJ
    share = port.shore_power_connection_share.get(times)
    expectation.set_shore_power_cost(idx, cost)
    expectation.set_shore_power_connection_share(idx, share)

    for key, value in port.shore_power_emission_factor.items():
        factor = value.get(times) / MWH_TO_GJ
        expectation.set_shore_power_emission_factor(idx, key, factor)


def _calculate_export_expectation(
    producer: Producer, times: FloatArray, idx: int
) -> None:
    """Set the producer's expected export distribution."""
    if not producer.export_distribution:
        return

    exports: dict[str, FloatArray] = {}
    for key, value in producer.export_distribution.items():
        exports[key] = value.get(times)

    total = sum(exports.values())

    # at steps where the total is not positive, ports share exports equally
    default = 1.0 / len(exports)

    expectation = producer.expectation

    for port_name, export in exports.items():
        share = divide_nonzero(export, total, default=default)
        expectation.set_export_distribution(idx, port_name, share)


def calculate_producer_evolution_expectation(
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

    n = len(producer.plants)

    # every plant carries the same emissions, so an arbitrary one names them
    emissions = producer.plants[0].expectation.get_emissions() if n > 0 else []

    cost = np.zeros((n, times.size))
    wtt = {emission_name: np.zeros((n, times.size)) for emission_name in emissions}
    weight = np.zeros((n, times.size))

    existing = np.zeros((n, times.size))

    for p, plant in enumerate(producer.plants):
        incs = producer.increments[p]
        if not len(incs):
            continue

        decided = np.array([inc.decided for inc in incs])
        origins = find_origin_indexes(years, years[idx], decided)
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

    for p, plant in enumerate(producer.plants):
        pinc = producer.pipeline[p]
        if not len(pinc):
            continue

        decided = np.array([inc.decided for inc in pinc])
        origins = find_origin_indexes(years, years[idx], decided)
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
        [producer.allow_plant[plant.name] for plant in producer.plants], dtype=bool
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

        for p, plant in enumerate(producer.plants):
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

    guaranteed = existing + pipeline
    expected = guaranteed + newbuild

    for p, plant in enumerate(producer.plants):
        name = plant.name
        producer.expectation.set_guaranteed_production(idx, name, guaranteed[p, :])
        producer.expectation.set_expected_production(idx, name, expected[p, :])

    for p, plant in enumerate(producer.plants):
        plant.expectation.set_expected_production_cost(idx, cost_avg[p, :])

        for e in plant.expectation.get_emissions():
            plant.expectation.set_expected_production_wtt(idx, e, wtt_avg[e][p, :])

    supply = expected[:, 0]
    for p, plant in enumerate(producer.plants):
        if supply[p] > TOLERANCE:
            plant.profile.set_instantaneous_cost(idx, cost_avg[p, 0])

            for e in plant.expectation.get_emissions():
                plant.profile.set_instantaneous_wtt(idx, e, wtt_avg[e][p, 0])


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
