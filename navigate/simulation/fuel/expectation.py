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
    from collections.abc import Collection, Iterator

    from navigate.core.expectations import PlantExpectation
    from navigate.core.increment import PlantIncrement
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray


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
        Simulation timeline, in days.
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
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    times = timeline[idx:]

    for producer in producers.values():
        _calculate_export_expectation(producer, times, idx)


def _calculate_port_expectation(port: Port, times: FloatArray, idx: int) -> None:
    """Set the port's limits, costs, overwrites and shore-power terms."""
    expectation = port.expectation

    for key, value in port.bunkering_limits.items():
        if value is not None:
            expectation.set_bunkering_limit(key, idx, value.get(times))

    for key, value in port.handling_costs.items():
        expectation.set_handling_cost(key, idx, value.get(times))

    for key, value in port.bunker_price_overwrites.items():
        if value is not None:
            expectation.set_bunker_price_overwrite(key, idx, value.get(times))

    for key, value in port.bunker_wtt_overwrites.items():
        if value is not None:
            expectation.set_bunker_wtt_overwrite(*key, idx, value.get(times))

    share = port.shore_power_connection_share.get(times)

    # convert from USD/MWh to USD/GJ, and ton/MWh to ton/GJ
    cost = port.shore_power_cost.get(times) / MWH_TO_GJ
    factors: dict[str, FloatArray] = {}
    for key, value in port.shore_power_emission_factors.items():
        factors[key] = value.get(times) / MWH_TO_GJ

    expectation.set_shore_power_connection_share(idx, share)
    expectation.set_shore_power_cost(idx, cost)

    for key, value in factors.items():
        expectation.set_shore_power_emission_factor(key, idx, value)


def _calculate_export_expectation(
    producer: Producer, times: FloatArray, idx: int
) -> None:
    """Set the producer's expected export distribution."""
    if not producer.export_distribution:
        return

    expectation = producer.expectation
    exports: dict[str, FloatArray] = {}

    for key, value in producer.export_distribution.items():
        exports[key] = value.get(times)

    # at steps where the total is not positive, ports share exports equally
    total = sum(exports.values())
    default = 1.0 / len(exports)

    for port_name, export in exports.items():
        share = divide_nonzero(export, total, default=default)
        expectation.set_export_distribution(port_name, idx, share)


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
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    times = timeline[idx:]
    plants = producer.plants
    in_service = producer.increments
    in_pipeline = producer.pipeline

    # every plant carries the same emissions, so an arbitrary one names them
    emission_names = plants[0].expectation.get_emissions()
    mix = _ProductionMix((len(plants), times.size), emission_names)

    existing = _calculate_cohort_production(plants, in_service, mix, timeline, idx)
    pipeline = _calculate_cohort_production(plants, in_pipeline, mix, timeline, idx)
    newbuild = _calculate_newbuild_production(producer, mix, times, idx)

    guaranteed = existing + pipeline
    expected = guaranteed + newbuild

    for p, plant in enumerate(plants):
        cost, wtt = mix.calculate_averages(p)

        producer.expectation.set_guaranteed_production(plant.name, idx, guaranteed[p])
        producer.expectation.set_expected_production(plant.name, idx, expected[p])
        plant.expectation.set_expected_production_cost(idx, cost)

        for key, value in wtt.items():
            plant.expectation.set_expected_production_wtt(key, idx, value)

        if expected[p, 0] > TOLERANCE:
            plant.results.instantaneous_cost[idx] = cost[0]

            for key, value in wtt.items():
                plant.results.instantaneous_wtt[key][idx] = value[0]


class _ProductionMix:
    """Accumulate each plant's production-weighted cost and WTT over the times."""

    def __init__(self, shape: tuple[int, int], emission_names: Collection[str]) -> None:
        self.cost: FloatArray = np.zeros(shape)
        self.weight: FloatArray = np.zeros(shape)
        self.wtt: dict[str, FloatArray] = {}

        for emission_name in emission_names:
            self.wtt[emission_name] = np.zeros(shape)

    def add(
        self,
        p: int,
        production: FloatArray,
        expectation: PlantExpectation,
        origin: int | np.signedinteger,
    ) -> None:
        """Add plant `p`'s production at the cost and WTT of its decision `origin`."""
        self.cost[p] += production * expectation.get_levelized_production_cost(origin)
        self.weight[p] += production

        for emission_name, wtt in self.wtt.items():
            wtt[p] += production * expectation.get_production_wtt(emission_name, origin)

    def calculate_averages(self, p: int) -> tuple[FloatArray, dict[str, FloatArray]]:
        """Calculate plant `p`'s production-weighted average cost and WTT."""
        weight = self.weight[p]
        cost = divide_nonzero(self.cost[p], weight)

        wtt: dict[str, FloatArray] = {}
        for emission_name, values in self.wtt.items():
            wtt[emission_name] = divide_nonzero(values[p], weight)

        return cost, wtt


def _calculate_cohort_production(
    plants: list[Plant],
    cohorts: list[list[PlantIncrement]],
    mix: _ProductionMix,
    timeline: FloatArray,
    idx: int,
) -> FloatArray:
    """
    Calculate each plant's production from its increments, adding it to the mix.

    Each increment enters and exits uniformly over its age span, as pipeline
    delivery and decommissioning move it.

    Parameters
    ----------
    plants
        Plants of the producer.
    cohorts
        Increments of each plant, all delivered or all in the pipeline.
    mix
        Production mix the increments are added to.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Production of each plant at each of the times from idx on, in tons/year.
    """
    years = timeline / YEAR
    times = timeline[idx:]
    profiles = np.zeros((len(plants), times.size))

    for p, plant, increment, origin in _iterate_increments(plants, cohorts, years, idx):
        production = plant.expectation.get_production(origin)
        decision = times[0] - increment.decided * YEAR
        lifetime = plant.lifetime.get()
        lifetime_then = plant.lifetime.get(decision)

        profile = _calculate_cohort_profile(increment, production, lifetime, times)
        weight = _calculate_cohort_profile(increment, production, lifetime_then, times)
        profiles[p] += profile
        mix.add(p, weight, plant.expectation, origin)

    return profiles


def _iterate_increments(
    plants: list[Plant],
    cohorts: list[list[PlantIncrement]],
    years: FloatArray,
    idx: int,
) -> Iterator[tuple[int, Plant, PlantIncrement, np.signedinteger]]:
    """Yield each plant's increments with the time-step index each was decided at."""
    for p, plant in enumerate(plants):
        increments = cohorts[p]
        if not increments:
            continue

        decided = np.array([increment.decided for increment in increments])
        origins = find_origin_indexes(years, years[idx], decided)

        for increment, origin in zip(increments, origins, strict=True):
            yield p, plant, increment, origin


def _calculate_cohort_profile(
    increment: PlantIncrement, production: float, lifetime: float, times: FloatArray
) -> FloatArray:
    """Calculate a delivered or pipeline increment's production at each of the times."""
    added = production * increment.multiplier
    delivery = times[0] - increment.age * YEAR
    window = increment.age_span * YEAR
    return _calculate_increment_production(added, delivery, lifetime, window, times)


def _calculate_newbuild_production(
    producer: Producer, mix: _ProductionMix, times: FloatArray, idx: int
) -> FloatArray:
    """
    Calculate each plant's production from the newbuilds decided at future times.

    The newbuilds decided at each time are added to the mix, and their feed
    consumption constrains the uptakes at the times after.

    Parameters
    ----------
    producer
        The producer.
    mix
        Production mix the newbuilds are added to.
    times
        Future times from the simulation timeline (timeline[idx:]), in days.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Production of each plant at each of the times, in tons/year.
    """
    plants = producer.plants
    jump_start = producer.jump_start_fraction.get()
    profiles = np.zeros((len(plants), times.size))
    feed_consumption = {key: np.zeros_like(times) for key in producer.feed_constraints}

    # without initial production the supply/demand interaction never starts, as
    # no supply is expected and thus no demand; a partially uniform uptake
    # expectation weighted by the jump-start fraction starts it
    allowed = np.array([producer.allow_plant[plant.name] for plant in plants])
    uniform = np.zeros_like(producer.current_uptake)
    uniform[allowed] = 1.0 / np.count_nonzero(allowed)
    uptakes = (1.0 - jump_start) * producer.current_uptake + jump_start * uniform
    limits = allowed.astype(float)

    # likewise, without previous development the expectation needs a minimum of
    # development potential to jump-start production
    current_utilization = producer.current_utilization
    utilization = current_utilization if current_utilization > 0.0 else jump_start

    # t=0 is already in the pipeline from the current time step's planning
    for t in range(1, times.size):
        time = times[t]
        origin = idx + t
        time_step = times[t] - times[t - 1]
        dt = time_step / YEAR

        # the utilization is only accounted for if the model is ramp-up
        # constrained; otherwise the model cannot increase the utilization over
        # time when the demand equals the supply
        ramp_up = producer.maximum_ramp_up.get(time) * dt
        utilization = min(utilization + ramp_up, 1.0)

        development = utilization * producer.maximum_development.get(time) * dt
        consumption = slice_dict(feed_consumption, t)
        constrained_uptakes = calculate_constrained_uptakes(
            producer, uptakes, development, limits, origin, consumption
        )

        for p, plant in enumerate(plants):
            # the production of a plant is locked when it is decided, not when it
            # is delivered, so it is read at time 't'
            expectation = plant.expectation
            production = expectation.get_production(origin)
            added = development * constrained_uptakes[p] * production

            profile = _calculate_newbuild_profile(plant, added, time, time_step, times)
            profiles[p] += profile
            mix.add(p, profile, expectation, origin)

            # the feed gap moves everything forward by the lead time: it is the gap
            # of what can enter the pipeline at 't', not the gap at 't + lead_time'
            conversions = expectation.get_feed_conversions(origin)
            for feed_name, conversion in conversions.items():
                feed_consumption[feed_name][t:] += added * conversion

    return profiles


def _calculate_newbuild_profile(
    plant: Plant, added: float, time: float, window: float, times: FloatArray
) -> FloatArray:
    """Calculate the production at each of the times of newbuilds decided at `time`."""
    lifetime = plant.lifetime.get(time)
    lead_time = plant.lead_time.get(time)

    # the delivery of the last expected increment, as increments enter uniformly
    # over the time step
    delivery = time + lead_time * YEAR
    return _calculate_increment_production(added, delivery, lifetime, window, times)


def _calculate_increment_production(
    production: float,
    delivery: float,
    lifetime: float,
    window: float,
    times: FloatArray,
) -> FloatArray:
    """
    Calculate the production profile over time for a single increment.

    Parameters
    ----------
    production
        Production that will enter at the delivery date (sum of all plants being
        delivered), in tons/year.
    delivery
        Time at which production was or will be delivered, in days.
    lifetime
        Time production stays in service after its delivery, in years.
    window
        Window over which production was or will be delivered, and will be
        decommissioned, in days.
    times
        Future times from the simulation timeline (timeline[idx:]), in days.

    Returns
    -------
    FloatArray
        The production active at each of the times, in tons/year.
    """
    if delivery <= 0.0:
        # an existing increment is already delivered, so all its production is
        # assigned at t=0
        delivered = np.zeros_like(times)
        delivered[0] = production
    else:
        delivered = _spread_uniformly(production, delivery, window, times)

    decommission = delivery + lifetime * YEAR
    decommissioned = _spread_uniformly(production, decommission, window, times)

    return np.cumsum(delivered - decommissioned)


def _spread_uniformly(
    production: float, end: float, window: float, times: FloatArray
) -> FloatArray:
    """
    Spread production uniformly over the window from `end - window` to `end`.

    Each time takes the part of the window since the previous time; the part
    beyond the last time is left out.
    """
    # a remainder of the window below the tolerance is round-off
    tolerance = 1e-5

    spread = np.zeros_like(times)
    start = end - window
    remaining = window
    t = np.argmax(start < times)

    while remaining > tolerance:
        if start >= times[-1]:
            break

        partial = min(times[t], end) - start
        spread[t] = partial / window * production

        t += 1
        start += partial
        remaining -= partial

    return spread
