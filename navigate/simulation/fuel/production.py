# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Levelized production cost, WTT emissions and feed use of each plant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import SourceDependencyID
from navigate.core.node_type import is_feedstock, is_process
from navigate.simulation.economics import (
    Component,
    add_capex,
    add_fixed_opex,
    add_fixed_wtt,
    add_variable_opex,
    add_variable_wtt,
    build_production_flow,
    calculate_levelized_cost,
)
from navigate.util import YEAR

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.process import Process
    from navigate.util.types_ import FloatArray


def calculate_plant_production_expectations(
    plant: Plant, emissions: dict[str, Emission], timeline: FloatArray, idx: int
) -> None:
    """
    Calculate the levelized cost, WTT emissions and feed use of a plant from a step on.

    The levelized cost covers the CAPEX and the fixed and variable OPEX of building
    and running the plant over its lifetime. A process living shorter than the plant,
    such as an electrolyzer stack, is replaced at the costs, emission factors and
    energy demand of its replacement time, while the conversion factors stay those of
    the investment time, so former and future feed use are calculated on one basis.
    The WTT per ton is that of the first operating year, the value at which the plant
    is certified.

    Parameters
    ----------
    plant
        Plant whose production is calculated.
    emissions
        All emissions in the simulation.
    timeline
        Simulation timeline, in days since the start of the simulation.
    idx
        Current time-step index.
    """
    _calculate_plant_production(plant, timeline, idx)

    expectation = plant.expectation
    process = plant.process

    component = None
    durations = None

    # TODO: drop the forward calculation once the fuel market expectation is simplified
    for t, time in enumerate(timeline[idx:], start=idx):
        lead_time = expectation.get_lead_time(t)
        lifetime = expectation.get_lifetime(t)

        # the flow sizes depend on the lead time and lifetime alone, so an
        # unchanged pair reuses the component instead of reallocating it
        if component is None or (lead_time, lifetime) != durations:
            component = _build_component(plant, process, emissions.keys(), time, t)
            durations = (lead_time, lifetime)
        else:
            component.reset(time)

        _add_process_tree(component, plant, process, 1.0, t)
        _calculate_unit_properties(component, plant, t)


def _calculate_plant_production(plant: Plant, timeline: FloatArray, idx: int) -> None:
    """
    Calculate the plant's lifetime, lead time, size and production from a step on.

    The size is the nameplate capacity, in tons/day; the production, in tons/year, is
    that capacity over a year at the plant's uptime.

    Parameters
    ----------
    plant
        Plant whose production is calculated.
    timeline
        Simulation timeline, in days since the start of the simulation.
    idx
        Current time-step index.
    """
    times = timeline[idx:]

    lifetime = plant.lifetime.get(times)
    lead_time = plant.lead_time.get(times)

    size = plant.capacity.get(times)
    capacity = size * YEAR

    uptime = plant.uptime.get(times)
    production = capacity * uptime

    expectation = plant.expectation
    expectation.set_lifetime(idx, lifetime)
    expectation.set_lead_time(idx, lead_time)
    expectation.set_size(idx, size)
    expectation.set_production(idx, production)


def _build_component(
    plant: Plant,
    process: Process,
    emission_names: Iterable[str],
    time_initial: float,
    idx: int,
) -> Component:
    """
    Build the empty component of a process for an investment at a given time.

    Its flows span the plant's lead time and lifetime at the step, and it carries the
    process's replacement cycle in the plant's region when the process has a lifetime.

    Parameters
    ----------
    plant
        Plant whose lead time and lifetime set the horizon.
    process
        Process the component holds the flows of.
    emission_names
        Names of the emissions to allocate a WTT flow for.
    time_initial
        Time of the investment decision, in days since the start of the simulation.
    idx
        Current time-step index.

    Returns
    -------
    Component
        Component with zeroed flows.
    """
    lead_time = float(plant.expectation.get_lead_time(idx))
    lifetime = float(plant.expectation.get_lifetime(idx))

    component = Component(lead_time, lifetime, time_initial, emission_names)
    component.attach_process_cycle(plant.region, process.name)

    return component


def _add_process_tree(
    component: Component,
    plant: Plant,
    process: Process,
    conversion: float,
    idx: int,
) -> None:
    """
    Add the flows of a process and of every feed under it to its component.

    The walk also records, in the plant's expectation, the mass of each process output
    and feedstock used per mass of fuel. A feed's conversion is locked at the time of
    investment.

    Parameters
    ----------
    component
        Component the flows of the process are added to.
    plant
        Plant the process tree belongs to.
    process
        Process at the root of the tree walked.
    conversion
        Mass of the process output per mass of fuel.
    idx
        Current time-step index.
    """
    expectation = plant.expectation
    time_initial = component.time_initial

    size = float(expectation.get_size(idx))
    production = float(expectation.get_production(idx))

    expectation.add_feed_mass(idx, process.name, conversion)

    _add_process_flows(component, plant, process, size, production, conversion)
    _add_energy_flows(component, plant, process, production, conversion)
    _add_transport_flows(component, plant, process, production, conversion)

    for feed, feed_ratio in zip(process.feeds, process.conversions, strict=True):
        feed_conversion = conversion * feed_ratio.get(time_initial)

        if is_feedstock(feed):
            expectation.add_feed_mass(idx, feed.name, feed_conversion)

            _add_feedstock_flows(component, plant, feed, production, feed_conversion)
            _add_transport_flows(component, plant, feed, production, feed_conversion)

        elif is_process(feed):
            # a subprocess gets its own component, since its lifetime and
            # replacement cycle differ from those of its parent
            emission_names = component.wtt_flows.keys()
            child = _build_component(plant, feed, emission_names, time_initial, idx)
            _add_process_tree(child, plant, feed, feed_conversion, idx)
            component.add_component(child)


def _add_process_flows(
    component: Component,
    plant: Plant,
    process: Process,
    size: float,
    production: float,
    conversion: float,
) -> None:
    """
    Add the CAPEX, fixed OPEX and fixed WTT of building and running a process.

    The CAPEX and OPEX rates are read at the process scale, the plant size times the
    conversion, so an intermediate process is sized to the fuel output it serves.

    Parameters
    ----------
    component
        Component the flows are added to.
    plant
        Plant whose region sets the rates.
    process
        Process whose rates are applied.
    size
        Size of the plant, in tons/day.
    production
        Production of the plant, in tons/year.
    conversion
        Mass of the process output per mass of fuel.
    """
    region = plant.region
    capex_rate = region.process_capex[process.name]
    opex_rate = region.process_opex[process.name]

    scale = size * conversion
    output = production * conversion

    def capex(time: float) -> float:
        return capex_rate.get(time, scale) * output

    def opex(time: float) -> float:
        return opex_rate.get(time, scale) * output

    def wtt(emission: str, time: float) -> float:
        wtt_rate = region.process_wtt[(process.name, emission)]
        return wtt_rate.get(time) * output

    add_capex(component, capex)
    add_fixed_opex(component, opex)
    add_fixed_wtt(component, wtt)


def _add_energy_flows(
    component: Component,
    plant: Plant,
    process: Process,
    production: float,
    conversion: float,
) -> None:
    """
    Add the cost and WTT of the energy a process draws from the plant's source.

    Parameters
    ----------
    component
        Component the flows are added to.
    plant
        Plant whose region and source set the rates.
    process
        Process whose energy demand is supplied.
    production
        Production of the plant, in tons/year.
    conversion
        Mass of the process output per mass of fuel.
    """
    region = plant.region
    source = plant.source
    energy_rate = region.process_energy[process.name]
    output = production * conversion

    def energy(time: float) -> float:
        return energy_rate.get(time) * output

    if source.dependency == SourceDependencyID.STANDALONE:
        # a standalone source is built with the plant, so its unit cost and emission
        # factors are locked at the time of investment even as a replaced process
        # changes the energy demand
        time_initial = component.time_initial
        capex_locked = region.source_capex[source.name].get(time_initial)
        opex_locked = region.source_opex[source.name].get(time_initial)

        def capex(time: float) -> float:
            return capex_locked * energy(time)

        def opex(time: float) -> float:
            return opex_locked * energy(time)

        def fixed_wtt(emission: str, time: float) -> float:
            wtt_locked = region.source_wtt[(source.name, emission)].get(time_initial)
            return wtt_locked * energy(time)

        add_capex(component, capex)
        add_fixed_opex(component, opex)
        add_fixed_wtt(component, fixed_wtt)

    elif source.dependency == SourceDependencyID.CONNECTED:
        # a connected source is bought at the prevailing price and emits at the
        # prevailing factors, so only the energy demand is locked, at investment and
        # at each replacement
        price = region.source_opex[source.name].get

        def variable_wtt(emission: str, time: FloatArray) -> FloatArray:
            return region.source_wtt[(source.name, emission)].get(time)

        add_variable_opex(component, energy, price)
        add_variable_wtt(component, energy, variable_wtt)


def _add_feedstock_flows(
    component: Component,
    plant: Plant,
    feedstock: Feedstock,
    production: float,
    conversion: float,
) -> None:
    """
    Add the variable cost and WTT of buying a feedstock.

    The feedstock mass per mass of fuel is locked at investment, while its price and
    emission factors vary with time.

    Parameters
    ----------
    component
        Component the flows are added to.
    plant
        Plant whose region sets the rates.
    feedstock
        Feedstock bought.
    production
        Production of the plant, in tons/year.
    conversion
        Mass of the feedstock per mass of fuel.
    """
    region = plant.region
    cost_rate = region.feedstock_cost[feedstock.name]

    def metric(time: float) -> float:
        return conversion

    def cost(time: FloatArray) -> FloatArray:
        return cost_rate.get(time) * production

    def wtt(emission: str, time: FloatArray) -> FloatArray:
        wtt_rate = region.feedstock_wtt[(feedstock.name, emission)]
        return wtt_rate.get(time) * production

    add_variable_opex(component, metric, cost)
    add_variable_wtt(component, metric, wtt)


def _add_transport_flows(
    component: Component,
    plant: Plant,
    feed: Process | Feedstock,
    production: float,
    conversion: float,
) -> None:
    """
    Add the variable cost and WTT of transporting a feed, if the plant delivers it.

    The mass moved per mass of fuel is locked at investment, while the transport's
    rates per ton-mile and the distance itself vary with time.

    Parameters
    ----------
    component
        Component the flows are added to.
    plant
        Plant whose region and deliveries set the rates.
    feed
        Feedstock, or process output, transported.
    production
        Production of the plant, in tons/year.
    conversion
        Mass of the feed per mass of fuel.
    """
    delivery = plant.feed_deliveries[feed.name]
    if delivery is None:
        return

    region = plant.region
    transport, distance = delivery
    cost_rate = region.transport_cost[transport.name]

    def metric(time: float) -> float:
        return conversion

    def cost(time: FloatArray) -> FloatArray:
        return cost_rate.get(time) * distance.get(time) * production

    def wtt(emission: str, time: FloatArray) -> FloatArray:
        wtt_rate = region.transport_wtt[(transport.name, emission)]
        return wtt_rate.get(time) * distance.get(time) * production

    add_variable_opex(component, metric, cost)
    add_variable_wtt(component, metric, wtt)


def _calculate_unit_properties(component: Component, plant: Plant, idx: int) -> None:
    """
    Calculate the levelized cost, tied capital and WTT per ton of the plant at a step.

    Parameters
    ----------
    component
        Component holding the flows of the whole process tree.
    plant
        Plant whose expectation receives the properties.
    idx
        Current time-step index.
    """
    expectation = plant.expectation
    commence_idx = component.get_commence_index()

    production = float(expectation.get_production(idx))
    production_flow = build_production_flow(component, production)

    cost_flow = component.get_cost_flow()
    discount_rate = plant.cost_of_capital.get(component.time_initial)
    levelized_cost = calculate_levelized_cost(cost_flow, production_flow, discount_rate)
    expectation.set_levelized_production_cost(idx, levelized_cost)

    # a copy, since the component is reused and refilled for the next step
    tied_capital = component.tied_capital_flow[commence_idx:].copy()
    expectation.set_tied_capital(idx, tied_capital)

    # TODO: recertify the plant every year instead of at its first operating year,
    # which requires reworking the Producer node. Unlike the cost, which converts to a
    # present value, the emissions must be tracked over the lifetime of the plant: a
    # reduction, e.g. in source or transport emissions as other sectors decarbonize,
    # can only be accounted for once it materializes.
    production_commence = production_flow[commence_idx]
    for emission, wtt_flow in component.wtt_flows.items():
        wtt = wtt_flow[commence_idx] / production_commence
        expectation.set_production_wtt(idx, emission, wtt)
