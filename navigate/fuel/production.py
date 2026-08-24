# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.enum_ import SourceDependencyID
from navigate.core.nodes.emission import Emission
from navigate.core.nodes.feedstock import Feedstock
from navigate.core.nodes.plant import Plant
from navigate.core.nodes.process import Process
from navigate.core.nodes.region import Region
from navigate.core.nodes.source import Source
from navigate.economics.flows import (
    Component,
    add_capex_flow,
    add_fixed_opex,
    add_fixed_wtt,
    add_variable_opex,
    add_variable_wtt,
    build_production_flow,
)
from navigate.economics.metric import calculate_levelized_cost
from navigate.util import YEAR


def calculate_plant_production_expectations(plant: Plant,
                                            emissions: dict[str, Emission],
                                            timeline: np.ndarray,
                                            idx: int) -> None:
    """
    Calculates all properties related to the production of fuels from a given plant. Specifically, the levelized cost
    of fuel, the average emission factor, and the amount of input (feedstock or process output) used.

    The levelized cost is calculated by summing the CAPEX, fixed OPEX, and variable OPEX needed to construct and
    operate the plant over its lifetime. Certain processes (e.g., electrolyzer stacks) may have lifetimes shorter
    than the plant and consequently require replacement at later stages.

    During the replacement, the model accounts for technology developments and thus the CAPEX, OPEX, energy demand,
    etc., may be lower after replacement. Notice, that the conversion factor remains constant over the lifetime
    of the plant. This is necessary to ensure consistent calculations for former and future use of feedstock.

    We assume that the emissions of the first year of production is the value at which the plant will be certified.
    This is a temporary simplification until TODO is implemented (requires reworking Producer node).
    # TODO:
    # Unlike the cost which can be converted to a present value, the emissions must be tracked over the lifetime of the
    # plant. If reductions in emissions happens e.g., due to decarbonization of other sectors via reduction in source or
    # transport emissions, these reductions cannot be accounted for until they materialize. The logic here is that
    # the emissions from the plant will be recertified every year to account for any potential reductions.

    Parameters
    ----------
    plant
        Plant for which fuel production properties are being calculated.
    emissions
        All emissions in the simulation.
    timeline
        Simulation timeline in days since the start of simulation.
    idx
        Current time-step index in the simulation timeline.
    """

    # calculate the production
    # output from the plant
    _calculate_plant_production(plant, timeline, idx)

    # extract the top-level process used
    # in the plant to produce fuel and
    # start the recursive traversal
    process = plant.process

    # track previous dimensions for component reuse
    prev_lead_time = None
    prev_lifetime = None
    component = None

    # TODO: Forward calculation can be removed once fuel market expectation is simplified
    for t, time in enumerate(timeline[idx:], start=idx):

        lead_time = plant.expectation.get_lead_time(t)
        lifetime = plant.expectation.get_lifetime(t)

        if component is not None and lead_time == prev_lead_time and lifetime == prev_lifetime:
            # reuse: zero flows, update time context, recompute overlap
            component.reset_flow(time)
            component.compute_overlap_schedule()
        else:
            # full allocation (first iteration or dimension change)
            component = _initialize_process_component(plant=plant,
                                                      process=process,
                                                      emissions=emissions,
                                                      time_initial=time,
                                                      idx=t)
            prev_lead_time = lead_time
            prev_lifetime = lifetime

        # calculate the cost flow and
        # emissions flow of the plant
        _calculate_recursive_process(component=component,
                                     plant=plant,
                                     process=process,
                                     emissions=emissions,
                                     conversion=1.,
                                     idx=t)

        # calculate the final cost and
        # emissions per ton of fuel
        _calculate_unit_properties(component=component,
                                   plant=plant,
                                   idx=t)

    # transfer the cost that is used at the
    # time of investment for the plant
    plant.profile.set_investment_cost(idx, plant.expectation.get_levelized_production_cost(idx))

    # transfer the WTT that is used at the
    # time of investment for the plant
    for e in emissions:
        plant.profile.set_investment_WTT(idx, e, plant.expectation.get_production_WTT(e, idx))


def _calculate_unit_properties(component: Component, plant: Plant, idx: int) -> None:
    """
    Aggregates time-dependent cost and emissions flows into unit metrics for the plant at a given time-step.

    The function builds a production flow for the current time-step and computes (i) the levelized cost of
    production using the plant's discount rate and (ii) the average well-to-tank (WTT) emission factor across
    all emissions. Emissions are averaged over the same production flow to be consistent with the cost
    aggregation and to mimic certification-style accounting over the operating period.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during recursive traversal.
    plant
        Plant for which fuel production properties are being calculated.
    idx
        Current time-step index in the simulation timeline.
    """

    # calculate the production flow of the plant
    production = plant.expectation.get_production(idx)
    production_flow = build_production_flow(component=component, production=production)

    # calculate the levelized cost
    cost_flow = component.get_cost_flow()
    discount_rate = plant.cost_of_capital.get(component.time_initial)
    levelized_cost = calculate_levelized_cost(cost_flow, production_flow, discount_rate)
    plant.expectation.set_levelized_production_cost(idx, levelized_cost)

    # assign the tied up capital
    commence_idx = component.get_commence_index()
    tied_capital = component.tied_capital_flow[commence_idx:]
    plant.expectation.set_tied_capital(idx, tied_capital)

    # calculate the emission factor
    emissions_flow = component.wtt_flow

    # index in the emissions flow vector
    # where the plant production commences
    idx_commence = component.get_commence_index()
    production_commence = production_flow[idx_commence]

    for e, emission_flow in emissions_flow.items():

        emission_commence = emission_flow[idx_commence]
        wtt = emission_commence / production_commence
        plant.expectation.set_production_WTT(idx, e, wtt)


def _calculate_plant_production(plant: Plant, timeline: np.ndarray, idx: int) -> None:
    """
    Computes plant-level production primitives (lifetime, lead time, capacity, production) over future times.

    Capacity is derived from nameplate size (tons/day) and scaled to tons/year. Actual production accounts for
    uptime.

    Parameters
    ----------
    plant
        Plant for which production primitives are being calculated.
    timeline
        Simulation timeline in days since the start of simulation.
    idx
        Current time-step index in the simulation timeline.
    """

    times = timeline[idx:]

    lifetime = plant.lifetime.get(times)
    lead_time = plant.lead_time.get(times)

    # convert production capacity
    # from tons/day to tons/year
    size = plant.capacity.get(times)
    capacity = size * YEAR

    # scale the production capacity
    # with the uptake to get the actual
    # delivered production per year
    uptime = plant.uptime.get(times)
    production = capacity * uptime

    plant.expectation.set_lifetime(idx, lifetime)
    plant.expectation.set_lead_time(idx, lead_time)
    plant.expectation.set_size(idx, size)
    plant.expectation.set_capacity(idx, capacity)
    plant.expectation.set_production(idx, production)


def _calculate_recursive_process(component: Component,
                                 plant: Plant,
                                 process: Process,
                                 emissions: dict[str, Emission],
                                 conversion: float,
                                 idx: int) -> None:
    """
    Recursively traverses the production tree to accumulate costs and emissions for processes and feedstocks.

    Starting from the top-level process, the routine:
    (1) Records the current conversion factor (mass input per mass fuel output).
    (2) Adds process-specific CAPEX/OPEX and WTT emissions.
    (3) Adds energy-related costs and emissions depending on whether the source is standalone or connected.
    (4) Adds transport-related costs and emissions for process outputs.
    (5) Iterates over each feedstock/conversion branch:
        • If a leaf feedstock, adds acquisition and transport costs/emissions.
        • If a nested process, continues recursion with the extended conversion.

    The accumulated flows are stored in `component` and later transformed into unit metrics.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during recursive traversal.
    plant
        The plant providing region, source, and expectation context.
    process
        The current process node being evaluated.
    emissions
        Mapping of emission names to `Emission` metadata used to initialize flows.
    conversion
        Cumulative mass conversion factor up to this node (input per unit fuel output).
    idx
        Current time-step index in the simulation timeline.
    """

    # pre-resolve shared lookups once for all cost/emission functions
    region = plant.region
    source = plant.source
    expectation = plant.expectation
    production = expectation.get_production(idx)

    # save the conversion factor for later use
    expectation.add_feed_mass(idx, process.get_name(), conversion)

    # calculate cost and emissions related
    # to the production process
    _calculate_process_cost(component, plant, process, region, production, conversion, idx)
    _calculate_process_emissions(component, process, emissions, region, production, conversion)

    # calculate cost and emissions related to the
    # energy source used to power the process
    _calculate_energy_cost(component, process, region, source, production, conversion, idx)
    _calculate_energy_emissions(component, process, emissions, region, source, production, conversion, idx)

    # calculate the cost and emissions related
    # to transporting output from the process
    _calculate_transport_cost(component, plant, process, region, production, conversion)
    _calculate_transport_emissions(component, plant, process, emissions, region, production, conversion)

    # loop over the feedstocks used in the process
    for (feed, feed_conversion) in zip(process.feeds, process.conversions):

        # extend the recursive conversion factor
        conversion_feed = conversion * feed_conversion.get(component.time_initial)

        if feed.is_feedstock():
            # if the feed is of type feedstock and not
            # a process, then the end of the recursive
            # tree is met in this direction

            # save the conversion factor for later use
            expectation.add_feed_mass(idx, feed.get_name(), conversion_feed)

            # calculate the cost and emissions related
            # to acquiring feedstock for the process
            _calculate_feedstock_cost(component, feed, region, production, conversion_feed)
            _calculate_feedstock_emissions(component, feed, emissions, region, production, conversion_feed)

            # calculate the cost and emissions related
            # to transporting feedstock for the process
            _calculate_transport_cost(component, plant, feed, region, production, conversion_feed)
            _calculate_transport_emissions(component, plant, feed, emissions, region, production, conversion_feed)

        elif feed.is_process():
            # if the feed is of type process,
            # continue traversing the recursive
            # process tree

            # initialize a component for the subprocess
            # to account for unique lifetime/replacement
            subcomponent = _initialize_process_component(plant=plant,
                                                         process=feed,
                                                         emissions=emissions,
                                                         time_initial=component.time_initial,
                                                         idx=idx)

            # calculate the cost and emissions related to the
            # subprocess and add them to the overall plant
            _calculate_recursive_process(subcomponent, plant, feed, emissions, conversion_feed, idx)
            component.add_component(subcomponent)


def _initialize_process_component(plant: Plant,
                                  process: Process,
                                  emissions: dict[str, Emission],
                                  time_initial: float,
                                  idx: int) -> Component:
    """
    Creates and initializes the aggregation `Component` for a given plant at a specific start time.

    The component is prepared with:
    • Flow containers sized to the plant's lead time and lifetime at the current index.
    • Callable hooks linking region- and process-specific lookups used by downstream calculators.
    • Emission streams to ensure consistent accumulation during recursion.

    Parameters
    ----------
    plant
        The plant whose timing (lead time, lifetime) governs the flow horizon.
    process
        The top-level process that defines the production branch.
    emissions
        All emissions in the simulation.
    time_initial
        Absolute time at which the plant component is assumed to be constructed or commissioned.
    idx
        Current time-step index in the simulation timeline.

    Returns
    -------
    Component
        An initialized component ready to receive cost and emissions flows.
    """

    component = Component()

    # initialize containers
    lead_time = plant.expectation.get_lead_time(idx)
    lifetime = plant.expectation.get_lifetime(idx)
    component.initialize_flow(lead_time, lifetime, time_initial, emissions)

    # initialize callables
    region = plant.region
    p = process.get_name()
    component.initialize_process_component(region, p)

    return component


def _calculate_process_cost(component: Component,
                            plant: Plant,
                            process: Process,
                            region: Region,
                            production: float,
                            conversion: float,
                            idx: int) -> None:
    """
    Adds process-specific capital and fixed operating costs to the component's cost flow.

    CAPEX/OPEX are evaluated via region lookups as functions of time and effective scale. Scale combines the
    plant's size (tons/day) and the cumulative conversion factor so that intermediate-process sizing aligns with
    fuel output requirements. Costs are added as fixed flows at construction/operation times.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during recursive traversal.
    plant
        The plant providing size expectations.
    process
        The process whose CAPEX/OPEX intensities are applied.
    region
        Pre-resolved region for this plant.
    production
        Pre-resolved production value for this timestep.
    conversion
        Cumulative mass conversion factor applied to scale the process equipment.
    idx
        Current time-step index in the simulation timeline.
    """

    size = plant.expectation.get_size(idx)
    p = process.get_name()

    capex_obj = region.get_process_CAPEX(p)
    opex_obj = region.get_process_OPEX(p)
    capex = lambda time, _c=capex_obj: _c.get(time, size * conversion) * production * conversion
    opex = lambda time, _o=opex_obj: _o.get(time, size * conversion) * production * conversion

    add_capex_flow(component=component, capex=capex)
    add_fixed_opex(component=component, value=opex)


def _calculate_process_emissions(component: Component,
                                 process: Process,
                                 emissions: dict[str, Emission],
                                 region: Region,
                                 production: float,
                                 conversion: float) -> None:
    """
    Adds process-related WTT emissions as fixed flows over the operating horizon.

    Emission factors are retrieved per species for the given process and multiplied by production and the
    current conversion factor. These are recorded as fixed WTT flows (constant with respect to consumption
    volume within the step) for later aggregation into average emission factors.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during recursive traversal.
    process
        The process whose emissions' factors are applied.
    emissions
        All emissions in the simulation.
    region
        Pre-resolved region for this plant.
    production
        Pre-resolved production value for this timestep.
    conversion
        Cumulative mass conversion factor reflecting upstream inputs per unit fuel.
    """

    p = process.get_name()

    wtt_callables = {}
    for e in emissions:
        wtt_obj = region.get_process_WTT(p, e)
        wtt_callables[e] = lambda time, _w=wtt_obj: _w.get(time) * production * conversion

    add_fixed_wtt(component=component, wtt_callables=wtt_callables)


def _calculate_energy_cost(component: Component,
                           process: Process,
                           region: Region,
                           source: Source,
                           production: float,
                           conversion: float,
                           idx: int) -> None:
    """
    Adds energy-related costs for powering the process, handling standalone vs. connected sources.

    For standalone sources, CAPEX and fixed OPEX are proportional to the process energy demand at construction
    and operation times. For connected sources, energy demand is fixed at construction but unit energy price is
    allowed to vary over time; costs are therefore added as variable OPEX with a time-varying price metric.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during recursive traversal.
    process
        The process whose energy demand profile is used.
    region
        Pre-resolved region for this plant.
    source
        Pre-resolved energy source for this plant.
    production
        Pre-resolved production value for this timestep.
    conversion
        Cumulative mass conversion factor used to scale energy demand to fuel output.
    idx
        Current time-step index in the simulation timeline.
    """

    s = source.get_name()
    p = process.get_name()

    energy_obj = region.get_process_energy(p)
    energy = lambda time, _e=energy_obj: _e.get(time) * production * conversion

    if source.get_dependency() == SourceDependencyID.STANDALONE:
        # if the energy source is standalone
        # the costs are defined, at the time
        # of construction. While the energy
        # demand may change with replacement
        # of the technology, the energy cost
        # is fixed at the time of investment
        # when the standalone source is built

        time_invest = component.time_initial
        capex_val = region.get_source_CAPEX(s).get(time_invest)
        opex_val = region.get_source_OPEX(s).get(time_invest)
        capex = lambda time: capex_val * energy(time)
        opex = lambda time: opex_val * energy(time)

        add_capex_flow(component=component, capex=capex)
        add_fixed_opex(component=component, value=opex)

    elif source.get_dependency() == SourceDependencyID.CONNECTED:
        # if the energy source is connected the
        # energy consumption is defined at the
        # time of construction but the energy
        # cost is variable over time

        opex_obj = region.get_source_OPEX(s)
        opex = lambda time, _o=opex_obj: _o.get(time)
        add_variable_opex(component=component, metric=energy, cost=opex)


def _calculate_energy_emissions(component: Component,
                                process: Process,
                                emissions: dict[str, Emission],
                                region: Region,
                                source: Source,
                                production: float,
                                conversion: float,
                                idx: int) -> None:
    """
    Adds energy-related WTT emissions for the process, respecting source dependency.

    For standalone sources, emissions are treated as fixed flows tied to the energy consumed at construction
    and operation times. For connected sources, emissions intensities may vary over time; emissions are therefore
    added as variable WTT flows using the energy demand as the metric.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during recursive traversal.
    process
        The process whose energy demand drives emissions.
    emissions
        All emissions in the simulation.
    region
        Pre-resolved region for this plant.
    source
        Pre-resolved energy source for this plant.
    production
        Pre-resolved production value for this timestep.
    conversion
        Cumulative mass conversion factor used to scale energy demand.
    idx
        Current time-step index in the simulation timeline.
    """

    s = source.get_name()
    p = process.get_name()

    energy_obj = region.get_process_energy(p)
    energy = lambda time, _e=energy_obj: _e.get(time) * production * conversion

    if source.get_dependency() == SourceDependencyID.STANDALONE:
        # if the energy source is standalone
        # the emissions are are defined, at
        # the time of construction. While
        # the energy demand may change with
        # replacement of the technology, the
        # energy emissions is fixed at the
        # time of investment when the standalone
        # source is built

        time_invest = component.time_initial
        wtt_callables = {}
        for e in emissions:
            wtt_val = region.get_source_WTT(s, e).get(time_invest)
            wtt_callables[e] = lambda time, _wv=wtt_val: _wv * energy(time)

        add_fixed_wtt(component=component, wtt_callables=wtt_callables)

    elif source.get_dependency() == SourceDependencyID.CONNECTED:
        # if the energy source is connected the
        # energy consumption is defined at the
        # time of construction but the energy
        # emissions are variable over time

        wtt_callables = {}
        for e in emissions:
            wtt_obj = region.get_source_WTT(s, e)
            wtt_callables[e] = lambda time, _w=wtt_obj: _w.get(time)

        add_variable_wtt(component=component, metric=energy, wtt_callables=wtt_callables)


def _calculate_feedstock_cost(component: Component,
                              feedstock: Feedstock,
                              region: Region,
                              production: float,
                              conversion: float) -> None:
    """
    Adds variable OPEX for acquiring feedstock (or intermediate process output) consumed by the process.

    The unit feedstock price is looked up per time and multiplied by annual production. A dummy metric equal to
    the conversion factor is used to express that total cost scales with input mass per unit fuel, enabling
    consistent treatment alongside other variable costs.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during recursive traversal.
    feedstock
        A `Feedstock` used as an input to the current process.
    region
        Pre-resolved region for this plant.
    production
        Pre-resolved production value for this timestep.
    conversion
        Cumulative mass conversion factor representing required input per unit fuel.
    """
    f = feedstock.get_name()

    cost_obj = region.get_feedstock_cost(f)
    metric = lambda time: conversion
    cost = lambda time, _c=cost_obj: _c.get(time) * production

    add_variable_opex(component=component, metric=metric, cost=cost)


def _calculate_feedstock_emissions(component: Component,
                                   feedstock: Feedstock,
                                   emissions: dict[str, Emission],
                                   region: Region,
                                   production: float,
                                   conversion: float) -> None:
    """
    Adds variable WTT emissions associated with acquiring and using a feedstock.

    Emission factors are retrieved per emission for the feedstock and multiplied by annual production.
    A dummy metric equal to the conversion factor scales emissions to the input mass required per unit fuel.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during recursive traversal.
    feedstock
        The feedstock whose emission factors are applied.
    emissions
        All emissions in the simulation.
    region
        Pre-resolved region for this plant.
    production
        Pre-resolved production value for this timestep.
    conversion
        Cumulative mass conversion factor representing input mass per unit fuel.
    """
    f = feedstock.get_name()

    metric = lambda time: conversion

    wtt_callables = {}
    for e in emissions:
        wtt_obj = region.get_feedstock_WTT(f, e)
        wtt_callables[e] = lambda time, _w=wtt_obj: _w.get(time) * production

    add_variable_wtt(component=component, metric=metric, wtt_callables=wtt_callables)


def _calculate_transport_cost(component: Component,
                              plant: Plant,
                              feed: Process | Feedstock,
                              region: Region,
                              production: float,
                              conversion: float) -> None:
    """
    Adds variable OPEX for transporting feedstocks or process outputs, if a transport mode is configured.

    Transport cost is computed from distance, regional transport unit cost, and annual production. If no
    transport is configured for the given input/output, the routine exits without modifying the component.
    Costs scale with the conversion factor through a dummy metric to reflect mass moved per unit fuel.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during recursive traversal.
    plant
        The plant providing transport assignments and distance profiles.
    feed
        A process (output from another process) or a feedstock being transported to the current process.
    region
        Pre-resolved region for this plant.
    production
        Pre-resolved production value for this timestep.
    conversion
        Cumulative mass conversion factor representing transported mass per unit fuel.
    """
    f = feed.get_name()
    transport = plant.get_feed_transport(f)

    # if transport is undefined then no
    # transport costs can be assigned
    if transport is None:
        return

    t = transport.get_name()

    dist_obj = plant.get_feed_distance(f)
    cost_obj = region.get_transport_cost(t)
    metric = lambda time: conversion
    distance = lambda time, _d=dist_obj: _d.get(time) * production
    cost = lambda time, _c=cost_obj: _c.get(time) * distance(time)

    add_variable_opex(component=component, metric=metric, cost=cost)


def _calculate_transport_emissions(component: Component,
                                   plant: Plant,
                                   feed: Process | Feedstock,
                                   emissions: dict[str, Emission],
                                   region: Region,
                                   production: float,
                                   conversion: float) -> None:
    """
    Adds variable WTT emissions from transport activities, if a transport mode is configured.

    Emissions are determined by regional transport emission factors per distance, multiplied by the
    distance traveled and annual production. When no transport assignment exists for the given input/output,
    the routine performs no updates. A dummy metric equal to the conversion factor ensures scaling with
    transported mass per unit fuel.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during recursive traversal.
    plant
        The plant providing transport assignments and distance profiles.
    feed
        A process (output from another process) or a feedstock being transported to the current process.
    emissions
        All emissions in the simulation.
    region
        Pre-resolved region for this plant.
    production
        Pre-resolved production value for this timestep.
    conversion
        Cumulative mass conversion factor representing transported mass per unit fuel.
    """
    f = feed.get_name()

    transport = plant.get_feed_transport(f)

    # if transport is undefined then no
    # transport costs can be assigned
    if transport is None:
        return

    t = transport.get_name()

    dist_obj = plant.get_feed_distance(f)
    metric = lambda time: conversion
    distance = lambda time, _d=dist_obj: _d.get(time)

    wtt_callables = {}
    for e in emissions:
        wtt_obj = region.get_transport_WTT(t, e)
        wtt_callables[e] = lambda time, _w=wtt_obj: _w.get(time) * distance(time) * production

    add_variable_wtt(component=component, metric=metric, wtt_callables=wtt_callables)
