# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Asset and cargo charter rates, NPVs and freight rate of each vessel."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.economics import (
    Component,
    add_capex,
    add_fixed_opex,
    add_variable_opex,
    build_cargo_flow,
    calculate_net_present_value,
)

if TYPE_CHECKING:
    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.tank import Tank
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray, FloatLike, Index


def calculate_asset_charter(vessel: Vessel, timeline: FloatArray, idx: int) -> None:
    """
    Calculate the asset charter metrics of a vessel ordered at this time-step.

    The asset charter rate, in USD/year, is what a ship operator would pay a ship
    owner: the asset cost levelized over the vessel's operating years. Technology
    costs are left out: they enter the cargo charter metrics as the fleet-average
    carried technology charge, and the post-processed instantaneous freight rate
    reuses the asset charter NPV.

    Parameters
    ----------
    vessel
        Vessel whose asset charter metrics are calculated.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    component = _build_asset_component(vessel, timeline[idx])
    discount_rate = vessel.cost_of_capital.get(component.time_initial)

    capex_flow = component.capex_flow
    cost_flow = component.get_cost_flow()
    operating_flow = component.operating_flow

    # reference for non-dimensionalizing technology and conversion investment NPVs
    capex_npv = calculate_net_present_value(capex_flow, discount_rate)

    # the asset cost levelized over the operating years, lead time excluded
    asset_charter_npv = calculate_net_present_value(cost_flow, discount_rate)
    annuity_factor = calculate_net_present_value(operating_flow, discount_rate)
    asset_charter_rate = asset_charter_npv / annuity_factor

    # the tied-up capital starts once the asset is in operation, as the lead time
    # is not modelled outside the financial calculations
    commence_idx = component.get_commence_index()
    tied_capital = component.tied_capital_flow[commence_idx:]

    expectation = vessel.expectation
    expectation.set_asset_charter_npv(idx, asset_charter_npv)
    expectation.set_capex_npv(idx, capex_npv)
    expectation.set_asset_charter_rate(idx, asset_charter_rate)
    expectation.set_tied_capital(idx, tied_capital)

    vessel.results.asset_charter_rate[idx] = asset_charter_rate


def calculate_cargo_charter(vessel: Vessel, timeline: FloatArray, idx: int) -> None:
    """
    Calculate the cargo charter rate and investment freight rate of a vessel.

    The total cost NPV adds the fuel cost NPV, which covers the bunker and policy
    expenses, and the carried technology charge to the asset charter NPV already
    calculated for this time-step. The cargo charter rate, in USD/year, is what a
    cargo owner would pay a ship operator: the total cost levelized over the
    operating years. The freight rate, in USD/cargo-mile, levelizes it over the
    cargo-miles delivered.

    Parameters
    ----------
    vessel
        Vessel whose cargo charter metrics are calculated.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    component = _build_fuel_component(vessel, timeline, idx)
    discount_rate = vessel.cost_of_capital.get(component.time_initial)

    expectation = vessel.expectation
    asset_charter_npv = expectation.get_asset_charter_npv(idx)
    technology_rate = expectation.get_technology_charter_rate(idx)
    cargo_miles = np.asarray(expectation.get_cargo_miles())

    fuel_cost_flow = component.get_cost_flow()
    operating_flow = component.operating_flow
    cargo_flow = build_cargo_flow(component, cargo_miles, timeline)

    fuel_npv = calculate_net_present_value(fuel_cost_flow, discount_rate)
    cargo_npv = calculate_net_present_value(cargo_flow, discount_rate)

    # present value of one USD/year over the operating years, lead time excluded
    annuity_factor = calculate_net_present_value(operating_flow, discount_rate)

    # the fleet-average carried technology charge is locked at this step like fixed
    # OPEX; the fleet average matches the fuel expenses, which reflect fleet-average
    # technology uptake
    cost_npv = asset_charter_npv + fuel_npv + technology_rate * annuity_factor
    cargo_charter_rate = cost_npv / annuity_factor
    freight_rate = cost_npv / cargo_npv

    expectation.set_fuel_cost_flow(fuel_cost_flow)
    expectation.set_freight_rate(idx, freight_rate)

    vessel.results.cargo_charter_rate[idx] = cargo_charter_rate
    vessel.results.investment_freight_rate[idx] = freight_rate


def calculate_fuel_and_policy_expenses(vessel: Vessel, idx: Index) -> FloatLike:
    """
    Calculate a vessel's expected fuel expenses plus its policy expenses.

    The policy expenses are the remedial and the flexibility expenses.

    Parameters
    ----------
    vessel
        Vessel whose expected expenses are summed.
    idx
        Time-step index or slice of the expenses.

    Returns
    -------
    FloatLike
        Fuel plus policy (remedial and flexibility) expenses, in USD/year.
    """
    expectation = vessel.expectation

    fuel = expectation.get_fuel_expenses(idx)
    remedial = expectation.get_remedial_expenses(idx)
    flexibility = expectation.get_flexibility_expenses(idx)

    return fuel + remedial + flexibility


def _build_asset_component(vessel: Vessel, time_initial: float) -> Component:
    """
    Build the component holding a vessel's asset cost flow.

    The cost flow holds the CAPEX and fixed OPEX of the vessel, its converters and
    its tanks.

    Parameters
    ----------
    vessel
        Vessel whose asset cost flow is built.
    time_initial
        Time at which the vessel is ordered, in days.

    Returns
    -------
    Component
        Component holding the asset cost flow.
    """
    component = _initialize_vessel_component(vessel, time_initial)

    add_capex(component, vessel.capex.get)
    add_fixed_opex(component, vessel.opex.get)

    for converter in vessel.get_converters():
        capacity = converter.power_capacity.get()
        _add_machinery_cost(vessel, component, converter, capacity)

    for tank in vessel.tanks:
        size = tank.size.get()
        _add_machinery_cost(vessel, component, tank, size)

    return component


def _initialize_vessel_component(vessel: Vessel, time_initial: float) -> Component:
    """
    Create the cost-flow component spanning a vessel's lead time and lifetime.

    Parameters
    ----------
    vessel
        Vessel whose lead time and lifetime set the flow horizon.
    time_initial
        Time at which the vessel is ordered, in days.

    Returns
    -------
    Component
        Component ready to receive cost flows.
    """
    lead_time = vessel.lead_time.get()
    lifetime = vessel.lifetime.get()

    return Component(lead_time, lifetime, time_initial)


def _add_machinery_cost(
    vessel: Vessel,
    component: Component,
    machinery: Converter | Tank,
    scale: float,
) -> None:
    """
    Add a machinery item's CAPEX and fixed OPEX, scaled by its capacity.

    A subcomponent carries the machinery's own lifetime and replacements.

    Parameters
    ----------
    vessel
        Vessel owning the machinery.
    component
        Root component accumulating the vessel's cost flows.
    machinery
        Converter or tank whose costs are added.
    scale
        Capacity the costs are scaled by: the power capacity of a converter, the
        size of a tank.
    """
    subcomponent = _initialize_vessel_component(vessel, component.time_initial)
    subcomponent.attach_machinery_cycle(machinery)

    def capex(time: float) -> float:
        return machinery.capex.get(time) * scale

    def opex(time: float) -> float:
        return machinery.opex.get(time) * scale

    add_capex(subcomponent, capex)
    add_fixed_opex(subcomponent, opex)
    component.add_component(subcomponent)


def _build_fuel_component(vessel: Vessel, timeline: FloatArray, idx: int) -> Component:
    """
    Build the component holding a vessel's expected fuel cost flow.

    The fuel and policy expenses over the remaining timeline are interpolated onto
    the component's year grid; the unit metric makes the variable OPEX equal that
    series.

    Parameters
    ----------
    vessel
        Vessel providing the expected fuel and policy expenses.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.

    Returns
    -------
    Component
        Component holding the fuel cost flow.
    """
    component = _initialize_vessel_component(vessel, timeline[idx])

    forward = np.s_[idx:]
    expenses = calculate_fuel_and_policy_expenses(vessel, forward)
    times = timeline[forward]

    def metric(time: float) -> float:
        return 1.0

    def price(time: FloatArray) -> FloatArray:
        return np.interp(time, times, expenses)

    add_variable_opex(component, metric, price)

    return component
