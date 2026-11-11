# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Expectations producers and ports set for later phases and other domains."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.fuel._profiles import (
    calculate_cohort_running,
    calculate_newbuild_reserved,
    calculate_newbuild_running,
    iterate_increments,
)
from navigate.simulation.fuel.feed import (
    calculate_constrained_uptakes,
    calculate_feed_delivery,
)
from navigate.util import (
    MWH_TO_GJ,
    TOLERANCE,
    YEAR,
    divide_nonzero,
    slice_dict,
)

if TYPE_CHECKING:
    from collections.abc import Collection

    from navigate.core.expectations import PlantExpectation
    from navigate.core.increment import PlantIncrement
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)


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
    producers: dict[str, Producer],
    ports: dict[str, Port],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate the share of each producer's fuels exported to each port.

    Parameters
    ----------
    producers
        All producers in the simulation.
    ports
        All ports in the simulation.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    times = timeline[idx:]
    fuel_names: set[str] = set()

    for producer in producers.values():
        fuel_names.update(producer.fuels)

    allowed_ports = _allowed_ports_per_fuel(ports, fuel_names)

    for producer in producers.values():
        _calculate_export_expectation(producer, allowed_ports, times, idx)


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
    producer: Producer,
    allowed_ports: dict[str, list[str]],
    times: FloatArray,
    idx: int,
) -> None:
    """
    Set the share of each of the producer's fuels exported to each port.

    A fuel goes to the ports allowing it, by the producer's export weights normalized
    over those ports, and equally among them where none of them carries a positive
    weight. The other ports take none of it.

    Parameters
    ----------
    producer
        The producer.
    allowed_ports
        Names of the ports allowing each fuel the producers make.
    times
        Future times from the simulation timeline (timeline[idx:]), in days.
    idx
        Current time-step index.
    """
    expectation = producer.expectation
    weights: dict[str, FloatArray] = {}

    for key, value in producer.export_distribution.items():
        weights[key] = value.get(times)

    for fuel_name in producer.fuels:
        allowed = allowed_ports[fuel_name]

        if not allowed:
            logger.debug(
                'Fuel("%s") is not allowed for bunkering in any port. Any existing '
                "production from %s is inaccessible during bunkering.",
                fuel_name,
                producer,
            )

        shares = _calculate_export_shares(weights, allowed)

        for key, value in shares.items():
            expectation.set_export_share(fuel_name, key, idx, value)


def _allowed_ports_per_fuel(
    ports: dict[str, Port], fuel_names: Collection[str]
) -> dict[str, list[str]]:
    """
    List the names of the ports allowing each fuel to be bunkered.

    Parameters
    ----------
    ports
        All ports in the simulation.
    fuel_names
        Names of the fuels.

    Returns
    -------
    dict[str, list[str]]
        Names of the ports allowing each fuel.
    """
    allowed_ports: dict[str, list[str]] = {}

    for fuel_name in fuel_names:
        allowed_ports[fuel_name] = []

        for port_name, port in ports.items():
            if port.bunkering_allowed[fuel_name]:
                allowed_ports[fuel_name].append(port_name)

    return allowed_ports


def _calculate_export_shares(
    weights: dict[str, FloatArray], allowed: list[str]
) -> dict[str, FloatArray]:
    """
    Calculate the share of a producer's export to each port.

    The allowed ports share the export by their weights normalized over them, and
    equally where none of them carries a positive weight. The other ports take none.

    Parameters
    ----------
    weights
        Export weight of the producer to every port in the simulation.
    allowed
        Names of the ports sharing the export.

    Returns
    -------
    dict[str, FloatArray]
        Share of the export to every port in the simulation.
    """
    shares = {port_name: np.zeros_like(weight) for port_name, weight in weights.items()}

    if not allowed:
        return shares

    # at steps where the allowed ports carry no positive weight, they share it equally
    total = sum(weights[port_name] for port_name in allowed)
    default = 1.0 / len(allowed)

    for port_name in allowed:
        shares[port_name] = divide_nonzero(weights[port_name], total, default=default)

    return shares


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
    times = timeline[idx:]
    profiles = np.zeros((len(plants), times.size))
    increments = iterate_increments(plants, cohorts, timeline, idx)

    for p, plant, increment, origin in increments:
        production = plant.expectation.get_production(origin)
        decision = times[0] - increment.decided * YEAR
        lifetime = plant.lifetime.get()
        lifetime_then = plant.lifetime.get(decision)

        profile = calculate_cohort_running(increment, production, lifetime, times)
        weight = calculate_cohort_running(increment, production, lifetime_then, times)
        profiles[p] += profile
        mix.add(p, weight, plant.expectation, origin)

    return profiles


def _calculate_newbuild_production(
    producer: Producer, mix: _ProductionMix, times: FloatArray, idx: int
) -> FloatArray:
    """
    Calculate each plant's production from the newbuilds decided at future times.

    The newbuilds decided at each time are added to the mix, and the feed they
    reserve constrains the uptakes at the times after.

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
    reserved_feed = _ReservedFeed(producer, times)

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
        consumption = slice_dict(reserved_feed.reserved, t)
        constrained_uptakes = calculate_constrained_uptakes(
            producer, uptakes, development, limits, origin, consumption
        )

        for p, plant in enumerate(plants):
            # the production of a plant is locked when it is decided, not when it
            # is delivered, so it is read at time 't'
            expectation = plant.expectation
            production = expectation.get_production(origin)
            added = development * constrained_uptakes[p] * production

            profile = calculate_newbuild_running(plant, added, time, time_step, times)
            profiles[p] += profile
            mix.add(p, profile, expectation, origin)
            reserved_feed.add(plant, added, t, time, time_step, origin)

    return profiles


class _ReservedFeed:
    """Accumulate the feed the newbuilds reserve, per constrained feed."""

    def __init__(self, producer: Producer, times: FloatArray) -> None:
        self.deliveries: dict[str, FloatArray] = {}
        self.reserved: dict[str, FloatArray] = {}

        for feed_name, constraint in producer.feed_constraints.items():
            if constraint is None:
                continue

            delivery = calculate_feed_delivery(producer, feed_name, times)
            if delivery is not None:
                self.deliveries[feed_name] = delivery
                self.reserved[feed_name] = np.zeros_like(times)

    def add(
        self,
        plant: Plant,
        added: float,
        t: int,
        time: float,
        window: float,
        origin: int,
    ) -> None:
        """Reserve the feed of `added` production of `plant` decided at `time`."""
        for feed_name, times in self.deliveries.items():
            conversion = plant.expectation.get_feed_conversion(feed_name, origin)
            feed = added * conversion

            reserved = calculate_newbuild_reserved(plant, feed, t, time, window, times)
            self.reserved[feed_name] += reserved
