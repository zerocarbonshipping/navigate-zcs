# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Levelized production cost, WTT emissions and feed use of each plant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import SourceDependencyID
from navigate.core.node_type import is_feedstock, is_process
from navigate.simulation.economics.flows import (
    Component,
    add_capex_flow,
    add_fixed_opex,
    add_fixed_wtt,
    add_variable_opex,
    add_variable_wtt,
    build_production_flow,
)
from navigate.simulation.economics.metric import calculate_levelized_cost
from navigate.util import YEAR

if TYPE_CHECKING:
    from collections.abc import Callable

    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.process import Process
    from navigate.core.nodes.region import Region
    from navigate.core.nodes.source import Source
    from navigate.core.types_ import ForecastInput
    from navigate.util.types_ import FloatArray


def calculate_plant_production_expectations(
    plant: Plant, emissions: dict[str, Emission], timeline: FloatArray, idx: int
) -> None:
    """
    Calculate all properties related to the production of fuels from a given plant.

    Specifically, the levelized cost of fuel, the average emission factor, and the
    amount of input (feedstock or process output) used.

    The levelized cost is calculated by summing the CAPEX, fixed OPEX, and variable OPEX
    needed to construct and operate the plant over its lifetime. Certain processes
    (e.g., electrolyzer stacks) may have lifetimes shorter than the plant and
    consequently require replacement at later stages.

    During the replacement, the model accounts for technology developments and thus the
    CAPEX, OPEX, energy demand, etc., may be lower after replacement. Notice, that the
    conversion factor remains constant over the lifetime of the plant. This is necessary
    to ensure consistent calculations for former and future use of feedstock.

    We assume that the emissions of the first year of production is the value at which
    the plant will be certified. This is a temporary simplification until TODO is
    implemented (requires reworking Producer node).
    # TODO:
    # Unlike the cost which can be converted to a present value, the emissions must be
    # tracked over the lifetime of the plant. If reductions in emissions happens e.g.,
    # due to decarbonization of other sectors via reduction in source or transport
    # emissions, these reductions cannot be accounted for until they materialize. The
    # logic here is that the emissions from the plant will be recertified every year to
    # account for any potential reductions.

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
    _calculate_plant_production(plant, timeline, idx)

    process = plant.process

    prev_lead_time = None
    prev_lifetime = None
    component = None

    # TODO: Forward calculation can be removed once fuel market expectation is
    # simplified
    for t, time in enumerate(timeline[idx:], start=idx):
        lead_time = plant.expectation.get_lead_time(t)
        lifetime = plant.expectation.get_lifetime(t)

        if (
            component is not None
            and lead_time == prev_lead_time
            and lifetime == prev_lifetime
        ):
            # the flow sizes depend on the lead time and lifetime alone, so an
            # unchanged pair reuses the component instead of reallocating it
            component.reset_flow(time)
        else:
            component = _initialize_process_component(
                plant=plant,
                process=process,
                emissions=emissions,
                time_initial=time,
                idx=t,
            )
            prev_lead_time = lead_time
            prev_lifetime = lifetime

        _calculate_recursive_process(
            component=component,
            plant=plant,
            process=process,
            emissions=emissions,
            conversion=1.0,
            idx=t,
        )
        _calculate_unit_properties(component=component, plant=plant, idx=t)

    plant.profile.set_investment_cost(
        idx, float(plant.expectation.get_levelized_production_cost(idx))
    )

    for e in emissions:
        plant.profile.set_investment_wtt(
            idx, e, float(plant.expectation.get_production_wtt(e, idx))
        )


def _calculate_unit_properties(component: Component, plant: Plant, idx: int) -> None:
    """
    Aggregate cost and emissions flows into unit metrics for the plant at a time-step.

    The function builds a production flow for the current time-step and computes (i) the
    levelized cost of production using the plant's discount rate and (ii) the average
    well-to-tank (WTT) emission factor across all emissions. Emissions are averaged over
    the same production flow to be consistent with the cost aggregation and to mimic
    certification-style accounting over the operating period.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during
        recursive traversal.
    plant
        Plant for which fuel production properties are being calculated.
    idx
        Current time-step index in the simulation timeline.
    """
    production = float(plant.expectation.get_production(idx))
    production_flow = build_production_flow(component=component, production=production)

    cost_flow = component.get_cost_flow()
    discount_rate = plant.cost_of_capital.get(component.time_initial)
    levelized_cost = calculate_levelized_cost(cost_flow, production_flow, discount_rate)
    plant.expectation.set_levelized_production_cost(idx, levelized_cost)

    commence_idx = component.get_commence_index()
    tied_capital = component.tied_capital_flow[commence_idx:]
    plant.expectation.set_tied_capital(idx, tied_capital)

    idx_commence = component.get_commence_index()
    production_commence = production_flow[idx_commence]

    for e, emission_flow in component.wtt_flow.items():
        emission_commence = emission_flow[idx_commence]
        wtt = emission_commence / production_commence
        plant.expectation.set_production_wtt(idx, e, wtt)


def _calculate_plant_production(plant: Plant, timeline: FloatArray, idx: int) -> None:
    """
    Compute future production primitives (lifetime, lead time, size, production).

    Capacity is derived from nameplate size (tons/day) and scaled to tons/year. Actual
    production accounts for uptime.

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

    size = plant.capacity.get(times)
    capacity = size * YEAR

    uptime = plant.uptime.get(times)
    production = capacity * uptime

    plant.expectation.set_lifetime(idx, lifetime)
    plant.expectation.set_lead_time(idx, lead_time)
    plant.expectation.set_size(idx, size)
    plant.expectation.set_production(idx, production)


def _calculate_recursive_process(
    component: Component,
    plant: Plant,
    process: Process,
    emissions: dict[str, Emission],
    conversion: float,
    idx: int,
) -> None:
    """
    Walk the production tree to accumulate process and feedstock costs and emissions.

    Starting from the top-level process, the routine:
    (1) Records the current conversion factor (mass input per mass fuel output).
    (2) Adds process-specific CAPEX/OPEX and WTT emissions.
    (3) Adds energy-related costs and emissions depending on whether the source is
        standalone or connected.
    (4) Adds transport-related costs and emissions for process outputs.
    (5) Iterates over each feedstock/conversion branch:
        - If a leaf feedstock, adds acquisition and transport costs/emissions.
        - If a nested process, continues recursion with the extended conversion.

    The accumulated flows are stored in `component` and later transformed into unit
    metrics.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during
        recursive traversal.
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
    region = plant.region
    source = plant.source
    expectation = plant.expectation
    production = float(expectation.get_production(idx))

    expectation.add_feed_mass(idx, process.name, conversion)

    _calculate_process_cost(
        component, plant, process, region, production, conversion, idx
    )
    _calculate_process_emissions(
        component, process, emissions, region, production, conversion
    )
    _calculate_energy_cost(component, process, region, source, production, conversion)
    _calculate_energy_emissions(
        component, process, emissions, region, source, production, conversion
    )
    _calculate_transport_cost(component, plant, process, region, production, conversion)
    _calculate_transport_emissions(
        component, plant, process, emissions, region, production, conversion
    )

    for feed, feed_conversion in zip(process.feeds, process.conversions, strict=True):
        conversion_feed = conversion * feed_conversion.get(component.time_initial)

        if is_feedstock(feed):
            expectation.add_feed_mass(idx, feed.name, conversion_feed)

            _calculate_feedstock_cost(
                component, feed, region, production, conversion_feed
            )
            _calculate_feedstock_emissions(
                component, feed, emissions, region, production, conversion_feed
            )
            _calculate_transport_cost(
                component, plant, feed, region, production, conversion_feed
            )
            _calculate_transport_emissions(
                component, plant, feed, emissions, region, production, conversion_feed
            )

        elif is_process(feed):
            # a subprocess gets its own component, since its lifetime and
            # replacement cycle differ from those of its parent
            subcomponent = _initialize_process_component(
                plant=plant,
                process=feed,
                emissions=emissions,
                time_initial=component.time_initial,
                idx=idx,
            )
            _calculate_recursive_process(
                subcomponent, plant, feed, emissions, conversion_feed, idx
            )
            component.add_component(subcomponent)


def _initialize_process_component(
    plant: Plant,
    process: Process,
    emissions: dict[str, Emission],
    time_initial: float,
    idx: int,
) -> Component:
    """
    Create and initialize the aggregation `Component` for a plant at a start time.

    The component is prepared with:
    - Flow containers sized to the plant's lead time and lifetime at the current index.
    - Callable hooks linking region- and process-specific lookups used by downstream
      calculators.
    - Emission streams to ensure consistent accumulation during recursion.

    Parameters
    ----------
    plant
        The plant whose timing (lead time, lifetime) governs the flow horizon.
    process
        The top-level process that defines the production branch.
    emissions
        All emissions in the simulation.
    time_initial
        Absolute time at which the plant component is assumed to be constructed or
        commissioned.
    idx
        Current time-step index in the simulation timeline.

    Returns
    -------
    Component
        An initialized component ready to receive cost and emissions flows.
    """
    lead_time = float(plant.expectation.get_lead_time(idx))
    lifetime = float(plant.expectation.get_lifetime(idx))
    component = Component(lead_time, lifetime, time_initial, emissions)
    component.initialize_process_component(plant.region, process.name)

    return component


def _calculate_process_cost(
    component: Component,
    plant: Plant,
    process: Process,
    region: Region,
    production: float,
    conversion: float,
    idx: int,
) -> None:
    """
    Add process capital and fixed operating costs to the component's cost flow.

    CAPEX/OPEX are evaluated via region lookups as functions of time and effective
    scale. Scale combines the plant's size (tons/day) and the cumulative conversion
    factor so that intermediate-process sizing aligns with fuel output requirements.
    Costs are added as fixed flows at construction/operation times.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during
        recursive traversal.
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
    size = float(plant.expectation.get_size(idx))
    capex_rate = region.process_capex[process.name]
    opex_rate = region.process_opex[process.name]

    def capex(time: float) -> float:
        return capex_rate.get(time, size * conversion) * production * conversion

    def opex(time: float) -> float:
        return opex_rate.get(time, size * conversion) * production * conversion

    add_capex_flow(component=component, capex=capex)
    add_fixed_opex(component=component, value=opex)


def _calculate_process_emissions(
    component: Component,
    process: Process,
    emissions: dict[str, Emission],
    region: Region,
    production: float,
    conversion: float,
) -> None:
    """
    Add process-related WTT emissions as fixed flows over the operating horizon.

    Emission factors are retrieved per species for the given process and multiplied by
    production and the current conversion factor. These are recorded as fixed WTT flows
    (constant with respect to consumption volume within the step) for later aggregation
    into average emission factors.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during
        recursive traversal.
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

    def wtt(rate: ForecastInput) -> Callable[[float], float]:
        return lambda time: rate.get(time) * production * conversion

    wtt_callables = {e: wtt(region.process_wtt[(process.name, e)]) for e in emissions}
    add_fixed_wtt(component=component, wtt_callables=wtt_callables)


def _calculate_energy_cost(
    component: Component,
    process: Process,
    region: Region,
    source: Source,
    production: float,
    conversion: float,
) -> None:
    """
    Add energy costs for powering the process (standalone vs. connected sources).

    For standalone sources, CAPEX and fixed OPEX are proportional to the process energy
    demand at construction and operation times. For connected sources, energy demand is
    fixed at construction but unit energy price is allowed to vary over time; costs are
    therefore added as variable OPEX with a time-varying price metric.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during
        recursive traversal.
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
    """
    energy_rate = region.process_energy[process.name]

    def energy(time: float) -> float:
        return energy_rate.get(time) * production * conversion

    if source.dependency == SourceDependencyID.STANDALONE:
        # a standalone source is built with the plant, so its unit cost is locked
        # at the time of investment even as a replaced process changes the energy
        # demand
        time_invest = component.time_initial
        capex_rate = region.source_capex[source.name].get(time_invest)
        opex_rate = region.source_opex[source.name].get(time_invest)

        def capex(time: float) -> float:
            return capex_rate * energy(time)

        def opex(time: float) -> float:
            return opex_rate * energy(time)

        add_capex_flow(component=component, capex=capex)
        add_fixed_opex(component=component, value=opex)

    elif source.dependency == SourceDependencyID.CONNECTED:
        # a connected source is bought at the prevailing price, so only the energy
        # demand is locked at construction
        add_variable_opex(
            component=component, metric=energy, cost=region.source_opex[source.name].get
        )


def _calculate_energy_emissions(
    component: Component,
    process: Process,
    emissions: dict[str, Emission],
    region: Region,
    source: Source,
    production: float,
    conversion: float,
) -> None:
    """
    Add energy-related WTT emissions for the process, respecting source dependency.

    For standalone sources, emissions are treated as fixed flows tied to the energy
    consumed at construction and operation times. For connected sources, emissions
    intensities may vary over time; emissions are therefore added as variable WTT flows
    using the energy demand as the metric.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during
        recursive traversal.
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
    """
    energy_rate = region.process_energy[process.name]

    def energy(time: float) -> float:
        return energy_rate.get(time) * production * conversion

    if source.dependency == SourceDependencyID.STANDALONE:
        # a standalone source is built with the plant, so its emission factor is
        # locked at the time of investment even as a replaced process changes the
        # energy demand
        time_invest = component.time_initial

        def fixed_wtt(rate: float) -> Callable[[float], float]:
            return lambda time: rate * energy(time)

        fixed_wtt_callables = {
            e: fixed_wtt(region.source_wtt[(source.name, e)].get(time_invest))
            for e in emissions
        }
        add_fixed_wtt(component=component, wtt_callables=fixed_wtt_callables)

    elif source.dependency == SourceDependencyID.CONNECTED:
        # a connected source emits at the prevailing factor, so only the energy
        # demand is locked at construction
        variable_wtt_callables: dict[str, Callable[[FloatArray], FloatArray]] = {
            e: region.source_wtt[(source.name, e)].get for e in emissions
        }
        add_variable_wtt(
            component=component, metric=energy, wtt_callables=variable_wtt_callables
        )


def _calculate_feedstock_cost(
    component: Component,
    feedstock: Feedstock,
    region: Region,
    production: float,
    conversion: float,
) -> None:
    """
    Add variable OPEX for feedstock (or intermediate output) consumed by the process.

    The unit feedstock price is looked up per time and multiplied by annual production.
    A dummy metric equal to the conversion factor is used to express that total cost
    scales with input mass per unit fuel, enabling consistent treatment alongside other
    variable costs.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during
        recursive traversal.
    feedstock
        A `Feedstock` used as an input to the current process.
    region
        Pre-resolved region for this plant.
    production
        Pre-resolved production value for this timestep.
    conversion
        Cumulative mass conversion factor representing required input per unit fuel.
    """
    cost_rate = region.feedstock_cost[feedstock.name]

    def metric(time: float) -> float:
        return conversion

    def cost(time: FloatArray) -> FloatArray:
        return cost_rate.get(time) * production

    add_variable_opex(component=component, metric=metric, cost=cost)


def _calculate_feedstock_emissions(
    component: Component,
    feedstock: Feedstock,
    emissions: dict[str, Emission],
    region: Region,
    production: float,
    conversion: float,
) -> None:
    """
    Add variable WTT emissions associated with acquiring and using a feedstock.

    Emission factors are retrieved per emission for the feedstock and multiplied by
    annual production. A dummy metric equal to the conversion factor scales emissions to
    the input mass required per unit fuel.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during
        recursive traversal.
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

    def metric(time: float) -> float:
        return conversion

    def wtt(rate: ForecastInput) -> Callable[[FloatArray], FloatArray]:
        return lambda time: rate.get(time) * production

    wtt_callables = {
        e: wtt(region.feedstock_wtt[(feedstock.name, e)]) for e in emissions
    }
    add_variable_wtt(component=component, metric=metric, wtt_callables=wtt_callables)


def _calculate_transport_cost(
    component: Component,
    plant: Plant,
    feed: Process | Feedstock,
    region: Region,
    production: float,
    conversion: float,
) -> None:
    """
    Add variable OPEX for transporting feedstocks or process outputs, if configured.

    Transport cost is computed from distance, regional transport unit cost, and annual
    production. If no transport is configured for the given input/output, the routine
    exits without modifying the component. Costs scale with the conversion factor
    through a dummy metric to reflect mass moved per unit fuel.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during
        recursive traversal.
    plant
        The plant providing transport assignments and distance profiles.
    feed
        A process (output from another process) or a feedstock being transported to the
        current process.
    region
        Pre-resolved region for this plant.
    production
        Pre-resolved production value for this timestep.
    conversion
        Cumulative mass conversion factor representing transported mass per unit fuel.
    """
    delivery = plant.feed_deliveries[feed.name]
    if delivery is None:
        return

    transport, distance = delivery
    cost_rate = region.transport_cost[transport.name]

    def metric(time: float) -> float:
        return conversion

    def cost(time: FloatArray) -> FloatArray:
        return cost_rate.get(time) * (distance.get(time) * production)

    add_variable_opex(component=component, metric=metric, cost=cost)


def _calculate_transport_emissions(
    component: Component,
    plant: Plant,
    feed: Process | Feedstock,
    emissions: dict[str, Emission],
    region: Region,
    production: float,
    conversion: float,
) -> None:
    """
    Add variable WTT emissions from transport, if a transport mode is configured.

    Emissions are determined by regional transport emission factors per distance,
    multiplied by the distance traveled and annual production. When no transport
    assignment exists for the given input/output, the routine performs no updates. A
    dummy metric equal to the conversion factor ensures scaling with transported mass
    per unit fuel.

    Parameters
    ----------
    component
        The root component that holds cost and emissions flows accumulated during
        recursive traversal.
    plant
        The plant providing transport assignments and distance profiles.
    feed
        A process (output from another process) or a feedstock being transported to the
        current process.
    emissions
        All emissions in the simulation.
    region
        Pre-resolved region for this plant.
    production
        Pre-resolved production value for this timestep.
    conversion
        Cumulative mass conversion factor representing transported mass per unit fuel.
    """
    delivery = plant.feed_deliveries[feed.name]
    if delivery is None:
        return

    transport, distance = delivery

    def metric(time: float) -> float:
        return conversion

    def wtt(rate: ForecastInput) -> Callable[[FloatArray], FloatArray]:
        return lambda time: rate.get(time) * distance.get(time) * production

    wtt_callables = {
        e: wtt(region.transport_wtt[(transport.name, e)]) for e in emissions
    }
    add_variable_wtt(component=component, metric=metric, wtt_callables=wtt_callables)
