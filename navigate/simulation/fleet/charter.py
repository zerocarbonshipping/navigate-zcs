# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Asset and cargo charter rates, NPVs and freight rate of each vessel."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.economics.flows import (
    Component,
    add_capex_flow,
    add_fixed_opex,
    add_variable_opex,
    build_cargo_flow,
)
from navigate.simulation.economics.metric import calculate_net_present_value

if TYPE_CHECKING:
    from collections.abc import Callable

    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.power_system import PowerSystem
    from navigate.core.nodes.tank import Tank
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray


def calculate_vessel_charter_properties(
    vessel: Vessel, timeline: FloatArray, idx: int
) -> None:
    """
    Calculate the asset charter metrics of a vessel ordered at this time-step.

    The cost flow holds the CAPEX and fixed OPEX of the hull, power system,
    converters and tanks. Technology costs are left out: they enter the cargo
    charter metrics as the fleet-average carried technology charge, and the
    post-processed instantaneous freight rate reuses the asset charter NPV.

    Parameters
    ----------
    vessel
        Vessel whose asset charter metrics are calculated.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    time = timeline[idx]
    component = _initialize_vessel_component(
        vessel=vessel, machinery=None, time_initial=time
    )

    _calculate_base_cost(vessel, component)
    _calculate_power_system_cost(vessel, component)
    _calculate_converter_cost(vessel, component)
    _calculate_tank_cost(vessel, component)
    _calculate_vessel_unit_properties(vessel, component, idx)


def calculate_cargo_charter_properties(
    vessel: Vessel, timeline: FloatArray, idx: int
) -> None:
    """
    Calculate the cargo charter rate and investment freight rate of a vessel.

    The fuel expenses, bunker and policy costs, enter as variable OPEX on top of
    the asset charter NPV already calculated for this time-step.

    Parameters
    ----------
    vessel
        Vessel whose cargo charter metrics are calculated.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    time = timeline[idx]
    component = _initialize_vessel_component(
        vessel=vessel, machinery=None, time_initial=time
    )

    _calculate_fuel_cost(vessel, component, timeline, idx)
    _calculate_cargo_unit_properties(vessel, component, timeline, idx)


def _calculate_vessel_unit_properties(
    vessel: Vessel, component: Component, idx: int
) -> None:
    """
    Store the asset charter NPV, CAPEX NPV, asset charter rate and tied capital.

    The asset charter rate, USD/year, is what a ship operator would pay a ship
    owner: the asset cost levelized over the vessel's operating years.

    Parameters
    ----------
    vessel
        Vessel whose asset charter metrics are stored.
    component
        Root component holding the vessel's asset cost flows.
    idx
        Current time-step index.
    """
    time_initial = component.time_initial
    discount_rate = vessel.cost_of_capital.get(time_initial)

    cost_flow_asset = component.get_cost_flow()
    asset_charter_npv = calculate_net_present_value(cost_flow_asset, discount_rate)

    # levelize over the years the vessel actually operates (construction
    # lead time excluded), consistent with the cost and cargo-mile flows
    age_npv = calculate_net_present_value(component.constant_overlap, discount_rate)
    asset_charter_rate = asset_charter_npv / age_npv

    # summed CAPEX (hull, power system, converters, tanks) discounted to a single
    # reference value used to non-dimensionalize technology and conversion investment
    # NPVs
    capex_npv = calculate_net_present_value(component.capex_flow, discount_rate)

    # the tied-up capital starts once the asset is in operation, as the lead time
    # is not modelled outside the financial calculations
    commence_idx = component.get_commence_index()
    tied_capital = component.tied_capital_flow[commence_idx:]

    vessel.expectation.set_asset_charter_npv(idx, asset_charter_npv)
    vessel.expectation.set_capex_npv(idx, capex_npv)
    vessel.expectation.set_asset_charter_rate(idx, asset_charter_rate)
    vessel.expectation.set_tied_capital(idx, tied_capital)

    vessel.profile.set_asset_charter_rate(idx, asset_charter_rate)


def _calculate_cargo_unit_properties(
    vessel: Vessel, component: Component, timeline: FloatArray, idx: int
) -> None:
    """
    Store the cargo charter rate and investment freight rate of a vessel.

    The total cost NPV adds the fuel cost NPV and the carried technology charge
    to the asset charter NPV. The cargo charter rate, USD/year, is what a cargo
    owner would pay a ship operator: the total cost levelized over the operating
    years. The freight rate, USD/cargo-mile, levelizes it over the cargo-miles
    delivered.

    Parameters
    ----------
    vessel
        Vessel whose cargo charter metrics are stored.
    component
        Root component holding the vessel's fuel cost flows for this time-step.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    time_initial = component.time_initial
    discount_rate = vessel.cost_of_capital.get(time_initial)

    asset_charter_npv = vessel.expectation.get_asset_charter_npv(idx)

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
    cargo_charter_rate = cost_npv / age_npv

    cargo_miles = np.asarray(vessel.expectation.get_cargo_miles())

    cargo_flow = build_cargo_flow(
        component=component, cargo=cargo_miles, timeline=timeline
    )

    cargo_npv = calculate_net_present_value(cargo_flow, discount_rate)
    freight_rate = cost_npv / cargo_npv

    vessel.expectation.set_fuel_cost_flow(cost_flow)
    vessel.expectation.set_freight_rate(idx, freight_rate)

    vessel.profile.set_cargo_charter_rate(idx, cargo_charter_rate)
    vessel.profile.set_investment_freight_rate(idx, freight_rate)


def _initialize_vessel_component(
    vessel: Vessel,
    machinery: Converter | PowerSystem | Tank | None,
    time_initial: float,
) -> Component:
    """
    Create the cost-flow component spanning a vessel's lead time and lifetime.

    Parameters
    ----------
    vessel
        Vessel whose lead time and lifetime set the flow horizon.
    machinery
        Machinery whose lifetime and replacement govern the component, or None for
        the vessel itself.
    time_initial
        Time at which the vessel is ordered, days.

    Returns
    -------
    Component
        Component ready to receive cost flows.
    """
    lead_time = vessel.lead_time.get()
    lifetime = vessel.lifetime.get()
    component = Component(lead_time, lifetime, time_initial)

    if machinery is not None:
        component.initialize_machinery_component(machinery)

    return component


def _calculate_base_cost(vessel: Vessel, component: Component) -> None:
    """
    Add the hull CAPEX and fixed OPEX to the component.

    Parameters
    ----------
    vessel
        Vessel providing the CAPEX and OPEX.
    component
        Root component accumulating the vessel's cost flows.
    """
    add_capex_flow(component=component, capex=vessel.capex.get)
    add_fixed_opex(component=component, value=vessel.opex.get)


def _calculate_power_system_cost(vessel: Vessel, component: Component) -> None:
    """
    Add the power-system CAPEX and fixed OPEX to the component.

    A subcomponent carries the power system's own lifetime and replacements.

    Parameters
    ----------
    vessel
        Vessel owning the power system.
    component
        Root component accumulating the vessel's cost flows.
    """
    power_system = vessel.power_system
    subcomponent = _initialize_vessel_component(
        vessel=vessel, machinery=power_system, time_initial=component.time_initial
    )

    add_capex_flow(component=subcomponent, capex=power_system.capex.get)
    add_fixed_opex(component=subcomponent, value=power_system.opex.get)
    component.add_component(subcomponent)


def _scaled_cost_callables(
    machinery: Converter | Tank, scale: float
) -> tuple[Callable[[float], float], Callable[[float], float]]:
    """
    Return (capex, opex) callables for the machinery, scaled by its capacity.

    Binding machinery and scale as function parameters keeps each callable tied
    to its own machinery when created inside a loop.
    """

    def capex(time: float) -> float:
        return machinery.capex.get(time) * scale

    def opex(time: float) -> float:
        return machinery.opex.get(time) * scale

    return capex, opex


def _calculate_converter_cost(vessel: Vessel, component: Component) -> None:
    """
    Add each converter's CAPEX and fixed OPEX, scaled by its power capacity.

    A subcomponent per converter carries its own lifetime and replacements.

    Parameters
    ----------
    vessel
        Vessel owning the converters.
    component
        Root component accumulating the vessel's cost flows.
    """
    for converter in vessel.power_system.get_converters():
        subcomponent = _initialize_vessel_component(
            vessel=vessel, machinery=converter, time_initial=component.time_initial
        )

        capex, opex = _scaled_cost_callables(converter, converter.power_capacity.get())

        add_capex_flow(component=subcomponent, capex=capex)
        add_fixed_opex(component=subcomponent, value=opex)
        component.add_component(subcomponent)


def _calculate_tank_cost(vessel: Vessel, component: Component) -> None:
    """
    Add each tank's CAPEX and fixed OPEX, scaled by its size.

    A subcomponent per tank carries its own lifetime and replacements.

    Parameters
    ----------
    vessel
        Vessel owning the tanks.
    component
        Root component accumulating the vessel's cost flows.
    """
    for tank in vessel.tanks:
        subcomponent = _initialize_vessel_component(
            vessel=vessel, machinery=tank, time_initial=component.time_initial
        )

        capex, opex = _scaled_cost_callables(tank, tank.size.get())

        add_capex_flow(component=subcomponent, capex=capex)
        add_fixed_opex(component=subcomponent, value=opex)
        component.add_component(subcomponent)


def _calculate_fuel_cost(
    vessel: Vessel, component: Component, timeline: FloatArray, idx: int
) -> None:
    """
    Add the expected fuel expenses to the component as variable OPEX.

    The expenses over the remaining timeline are interpolated onto the
    component's year grid; the unit metric makes the variable OPEX equal that
    series.

    Parameters
    ----------
    vessel
        Vessel providing the expected fuel expenses.
    component
        Root component accumulating the fuel cost flows for this time-step.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    _idx = np.s_[idx:]
    expenses = vessel.expectation.get_total_fuel_expenses(_idx)

    def metric(time: float) -> float:
        return 1.0

    def cost(time: FloatArray) -> FloatArray:
        return np.interp(time, timeline[idx:], expenses)

    add_variable_opex(component=component, metric=metric, cost=cost)
