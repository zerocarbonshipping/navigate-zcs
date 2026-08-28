# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.nodes.converter import Converter
from navigate.core.nodes.power_system import PowerSystem
from navigate.core.nodes.tank import Tank
from navigate.core.nodes.vessel import Vessel
from navigate.economics.flows import (
    Component,
    add_capex_flow,
    add_fixed_opex,
    add_variable_opex,
    build_cargo_flow,
)
from navigate.economics.metric import calculate_net_present_value


def calculate_vessel_charter_properties(vessel: Vessel,
                                        timeline: np.ndarray,
                                        idx: int) -> None:
    """
    Calculates all properties related to the vessel asset charter at a given time-step.

    The routine builds a unified cost flow for owning the vessel over its lifetime by aggregating base vessel
    CAPEX and fixed OPEX with machinery CAPEX/OPEX for the power system, converters, and tanks. The resulting
    cost flow is then converted into an asset charter NPV and an age-levelized annual charter rate. Technology
    costs are deliberately excluded: they enter the cargo charter metrics as the fleet-average carried
    technology charge, and the post-processed instantaneous freight rate reuses the asset charter NPV.

    Parameters
    ----------
    vessel
        Vessel for which asset charter properties are being calculated.
    timeline
        Simulation timeline in days since the start of simulation.
    idx
        Current time-step index in the simulation timeline.
    """

    time = timeline[idx]

    # initialize the component on
    # which cost flow is stored
    component = _initialize_vessel_component(vessel=vessel,
                                             machinery=None,
                                             time_initial=time)

    # calculate cost of the asset, including
    # base costs and all fixed equipment
    # namely power system tanks, and converters
    _calculate_base_cost(vessel, component)
    _calculate_power_system_cost(vessel, component)
    _calculate_converter_cost(vessel, component)
    _calculate_tank_cost(vessel, component)

    # based on the calculated cost-flow,
    # calculate the charter properties
    _calculate_vessel_unit_properties(vessel, component, idx)


def calculate_cargo_charter_properties(vessel: Vessel,
                                       timeline: np.ndarray,
                                       idx: int) -> None:
    """
    Calculates cargo-owner-facing charter properties at a given time-step.

    The routine adds fuel-related costs (bunkers and policy costs, represented as variable OPEX) into a unified
    cost flow and combines this with the already-computed asset charter NPV to obtain the total yearly cost NPV.
    From this, it derives (i) a cargo charter rate per year and (ii) an investment freight rate per cargo-mile.

    Parameters
    ----------
    vessel
        Vessel for which cargo charter properties are being calculated.
    timeline
        Simulation timeline in days since the start of simulation.
    idx
        Current time-step index in the simulation timeline.
    """

    time = timeline[idx]

    # initialize the component on
    # which cost flow is stored
    component = _initialize_vessel_component(vessel=vessel,
                                             machinery=None,
                                             time_initial=time)

    # calculate the cost related to fuel
    # consumption, including bunker cost
    # and policy costs
    _calculate_fuel_cost(vessel, component, timeline, idx)

    # based on the calculated cost-flows,
    # calculate the metrics used for
    # investment decisions
    _calculate_cargo_unit_properties(vessel, component, timeline, idx)


def _calculate_vessel_unit_properties(vessel: Vessel,
                                      component: Component,
                                      idx: int) -> None:
    """
    Aggregates vessel asset cost flows into owner-facing charter metrics for a given time-step.

    The function converts the aggregated CAPEX/OPEX cost flow into:
    (i) an asset charter NPV and (ii) an age-levelized annual asset charter rate using the vessel lifetime and
    discount rate. The results are stored on the vessel expectation and profile for later use.

    Parameters
    ----------
    vessel
        Vessel for which asset charter metrics are being calculated.
    component
        The root component that holds cost flows accumulated during vessel cost aggregation.
    idx
        Current time-step index in the simulation timeline.
    """

    # extract vessel investment properties
    time_initial = component.time_initial
    discount_rate = vessel.cost_of_capital.get(time_initial)

    # calculate the asset charter rate as a levelized
    # cost per year (the charter rate a ship operator
    # would pay a ship owner). Also, calculate the
    # asset charter NPV for later post-processing.
    cost_flow_asset = component.get_cost_flow()
    asset_charter_npv = calculate_net_present_value(cost_flow_asset, discount_rate)

    # levelize over the years the vessel actually operates (construction
    # lead time excluded), consistent with the cost and cargo-mile flows
    age_npv = calculate_net_present_value(component.constant_overlap, discount_rate)
    asset_charter_rate = asset_charter_npv / age_npv

    # summed CAPEX (hull, power system, converters, tanks) discounted to a single
    # reference value used to non-dimensionalize technology and conversion investment NPVs
    capex_npv = calculate_net_present_value(component.capex_flow, discount_rate)

    # the tied up capital is evaluated only after the
    # asset is in operation since the lead time is not
    # well accounted for at the moment outside the
    # financial calculations
    commence_idx = component.get_commence_index()
    tied_capital = component.tied_capital_flow[commence_idx:]

    vessel.expectation.set_asset_charter_npv(idx, asset_charter_npv)
    vessel.expectation.set_capex_npv(idx, capex_npv)
    vessel.expectation.set_asset_charter_rate(idx, asset_charter_rate)
    vessel.expectation.set_tied_capital(idx, tied_capital)

    vessel.profile.set_asset_charter_rate(idx, asset_charter_rate)


def _calculate_cargo_unit_properties(vessel: Vessel,
                                     component: Component,
                                     timeline: np.ndarray,
                                     idx: int) -> None:
    """
    Aggregates fuel-related cost flows into operator- and cargo-owner-facing unit metrics for a given time-step.

    Fuel costs are converted to NPV and combined with the vessel asset charter NPV and the fleet-average carried
    technology charge (a constant yearly cost over the operating years, matching the fleet-average uptake the
    fuel expenses reflect) to obtain a total cost NPV. The routine then computes:
    (i) a cargo charter rate per year by dividing total cost NPV by the NPV of an age flow, and
    (ii) a freight rate per cargo-mile by dividing total cost NPV by the NPV of a cargo-mile delivery flow.

    Parameters
    ----------
    vessel
        Vessel for which cargo charter metrics are being calculated.
    component
        The root component that holds fuel cost flows accumulated during the current time-step.
    timeline
        Simulation timeline in days since the start of simulation.
    idx
        Current time-step index in the simulation timeline.
    """

    # extract vessel investment properties
    time_initial = component.time_initial
    discount_rate = vessel.cost_of_capital.get(time_initial)

    # extract the charter rate of the
    # asset excluding fuel expenses
    asset_charter_npv = vessel.expectation.get_asset_charter_npv(idx)

    # calculate the NPV of the fuel cost
    # flow and add it to the vessel charter
    # npv to get the total NPV of a vessel
    # over a year
    cost_flow = component.get_cost_flow()
    fuel_npv = calculate_net_present_value(cost_flow, discount_rate)

    # levelize over the years the vessel actually operates (construction
    # lead time excluded), consistent with the asset charter rate
    age_npv = calculate_net_present_value(component.constant_overlap, discount_rate)

    # add the fleet-average carried technology charge as a constant yearly
    # cost over the operating years (locked at the current time-step, like
    # fixed OPEX); the fleet average matches the fuel expenses, which
    # reflect fleet-average technology uptake
    technology_rate = vessel.expectation.get_technology_charter_rate(idx)
    cost_npv = asset_charter_npv + fuel_npv + technology_rate * age_npv

    # calculate the cargo charter rate (the charter
    # rate a cargo owner would pay a ship operator
    # per year)
    cargo_charter_rate = cost_npv / age_npv

    # calculate the cargo-delivery flow of the vessel
    cargo_miles = vessel.expectation.get_cargo_miles()

    cargo_flow = build_cargo_flow(component=component,
                                  cargo=cargo_miles,
                                  timeline=timeline)

    cargo_npv = calculate_net_present_value(cargo_flow, discount_rate)

    # calculate the freight rate (the rate a cargo
    # owner would pay a ship operator per cargo-mile)
    freight_rate = cost_npv / cargo_npv

    vessel.expectation.set_fuel_cost_flow(cost_flow)
    vessel.expectation.set_freight_rate(idx, freight_rate)

    vessel.profile.set_cargo_charter_rate(idx, cargo_charter_rate)
    vessel.profile.set_investment_freight_rate(idx, freight_rate)


def _initialize_vessel_component(vessel: Vessel,
                                 machinery: Converter | PowerSystem | Tank | None,
                                 time_initial: float) -> Component:
    """
    Creates and initializes the aggregation `Component` for a given vessel at a specific start time.

    The component is prepared with:
    • Flow containers sized to the vessel lifetime (lead time assumed zero).
    • Callable hooks linking machinery-specific lifetime/replacement lookups when a machinery object is provided.

    Parameters
    ----------
    vessel
        The vessel whose timing (lifetime) governs the flow horizon.
    machinery
        _Machinery for which lifetime/replacement hooks should be initialized (optional).
    time_initial
        Absolute time at which the vessel component is assumed to be constructed or commissioned.

    Returns
    -------
    Component
        An initialized component ready to receive cost flows.
    """

    component = Component()

    # initialize containers
    lead_time = vessel.lead_time.get()
    lifetime = vessel.lifetime.get()
    component.initialize_flow(lead_time, lifetime, time_initial)

    # initialize callables
    if machinery is not None:
        component.initialize_machinery_component(machinery)

    return component


def _calculate_base_cost(vessel: Vessel, component: Component) -> None:
    """
    Adds base vessel capital and fixed operating costs to the component's cost flow.

    CAPEX and fixed OPEX are retrieved from the vessel and added as fixed/locked flows over the vessel horizon.

    Parameters
    ----------
    vessel
        Vessel providing base CAPEX and OPEX definitions.
    component
        The root component that accumulates vessel cost flows.
    """

    capex = lambda time: vessel.capex.get(time)
    opex = lambda time: vessel.opex.get(time)

    add_capex_flow(component=component, capex=capex)
    add_fixed_opex(component=component, value=opex)


def _calculate_power_system_cost(vessel: Vessel, component: Component) -> None:
    """
    Adds power-system capital and fixed operating costs to the vessel component.

    A dedicated subcomponent is initialized for the power system to account for any distinct machinery lifetime and
    replacement behavior. The subcomponent cost flow is then added to the parent vessel component.

    Parameters
    ----------
    vessel
        Vessel providing access to the power system.
    component
        The root component that accumulates vessel cost flows.
    """

    power_system = vessel.power_system
    subcomponent = _initialize_vessel_component(vessel=vessel,
                                                machinery=power_system,
                                                time_initial=component.time_initial)

    capex = lambda time: power_system.capex.get(time)
    opex = lambda time: power_system.opex.get(time)

    add_capex_flow(component=subcomponent, capex=capex)
    add_fixed_opex(component=subcomponent, value=opex)
    component.add_component(subcomponent)


def _calculate_converter_cost(vessel: Vessel, component: Component) -> None:
    """
    Adds converter capital and fixed operating costs to the vessel component.

    For each converter in the vessel power system, a dedicated subcomponent is initialized to respect the converter's
    lifetime/replacement behavior. CAPEX and OPEX are scaled by converter power capacity and aggregated into the parent.

    Parameters
    ----------
    vessel
        Vessel providing access to converters in the power system.
    component
        The root component that accumulates vessel cost flows.
    """

    for converter in vessel.power_system.get_converters():
        subcomponent = _initialize_vessel_component(vessel=vessel,
                                                    machinery=converter,
                                                    time_initial=component.time_initial)

        power = converter.power_capacity.get()
        capex = lambda time: converter.capex.get(time) * power
        opex = lambda time: converter.opex.get(time) * power

        add_capex_flow(component=subcomponent, capex=capex)
        add_fixed_opex(component=subcomponent, value=opex)
        component.add_component(subcomponent)


def _calculate_tank_cost(vessel: Vessel, component: Component) -> None:
    """
    Adds tank capital and fixed operating costs to the vessel component.

    For each tank installed on the vessel, a dedicated subcomponent is initialized to respect the tank's
    lifetime/replacement behavior. CAPEX and OPEX are scaled by tank size and aggregated into the parent.

    Parameters
    ----------
    vessel
        Vessel providing access to installed tanks.
    component
        The root component that accumulates vessel cost flows.
    """

    for tank in vessel.tanks:
        subcomponent = _initialize_vessel_component(vessel=vessel,
                                                    machinery=tank,
                                                    time_initial=component.time_initial)

        size = tank.size.get()
        capex = lambda time: tank.capex.get(time) * size
        opex = lambda time: tank.opex.get(time) * size

        add_capex_flow(component=subcomponent, capex=capex)
        add_fixed_opex(component=subcomponent, value=opex)
        component.add_component(subcomponent)


def _calculate_fuel_cost(vessel: Vessel,
                         component: Component,
                         timeline: np.ndarray,
                         idx: int) -> None:
    """
    Adds fuel-related costs as variable OPEX into the component's cost flow for a given time-step.

    Fuel expenses are taken from the vessel expectation as an annual time series defined over the remaining simulation
    timeline and interpolated onto the component year grid. A unit metric is used so that the variable OPEX equals the
    interpolated expense series.

    Parameters
    ----------
    vessel
        Vessel providing fuel expense expectations.
    component
        The root component that accumulates fuel cost flows for the current time-step.
    timeline
        Simulation timeline in days since the start of simulation.
    idx
        Current time-step index in the simulation timeline.
    """

    _idx = np.s_[idx:]
    expenses = vessel.expectation.get_total_fuel_expenses(_idx)

    metric = lambda time: 1.
    cost = lambda time: np.interp(time, timeline[idx:], expenses)

    add_variable_opex(component=component, metric=metric, cost=cost)
