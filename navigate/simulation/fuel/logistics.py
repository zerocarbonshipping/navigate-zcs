# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Levelized cost and WTT emissions of delivering each plant's fuel to each port."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.economics import (
    build_operating_flows,
    calculate_levelized_cost,
)

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.transport import Transport
    from navigate.core.types_ import ForecastInput
    from navigate.util.types_ import FloatArray


def calculate_plant_logistics_expectations(
    plants: dict[str, Plant],
    ports: dict[str, Port],
    emissions: dict[str, Emission],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate the cost and WTT emissions of delivering each plant's fuel to each port.

    The delivery cost and emissions are given by the transport mode and distance
    assigned per port on the plant, combined with the per-distance rates of the plant's
    region. The cost is levelized over the plant's lead time and lifetime; the emissions
    are instantaneous.

    Parameters
    ----------
    plants
        All plants in the simulation.
    ports
        All ports in the simulation.
    emissions
        All emissions in the simulation.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    # rate expectations are shared between every plant in the same region using the
    # same transport over the same window: resolve each combination once
    cost_rates: dict[tuple[str, str, int, float, float], FloatArray] = {}
    wtt_rates: dict[tuple[str, str, str], FloatArray] = {}

    for plant in plants.values():
        deliveries = _find_deliveries(plant, ports)

        # without a transport assignment no delivery cost or emissions accrue: the
        # expectation defaults are zero
        if not deliveries:
            continue

        _calculate_delivery_cost(plant, deliveries, cost_rates, timeline, idx)
        _calculate_delivery_wtt(plant, deliveries, emissions, wtt_rates, timeline, idx)


def _find_deliveries(
    plant: Plant, ports: dict[str, Port]
) -> dict[str, tuple[Transport, ForecastInput]]:
    """
    Find the transport and distance assigned to the plant for each port it supplies.

    Parameters
    ----------
    plant
        Plant delivering its fuel.
    ports
        All ports in the simulation.

    Returns
    -------
    dict[str, tuple[Transport, ForecastInput]]
        Transport and distance per port name, for the ports that allow bunkering of
        the plant's fuel and have a transport assigned.
    """
    deliveries = {}

    for port_name, port in ports.items():
        if not port.bunkering_allowed[plant.fuel.name]:
            continue

        delivery = plant.fuel_deliveries[port_name]
        if delivery is not None:
            deliveries[port_name] = delivery

    return deliveries


def _calculate_delivery_cost(
    plant: Plant,
    deliveries: dict[str, tuple[Transport, ForecastInput]],
    cost_rates: dict[tuple[str, str, int, float, float], FloatArray],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate the levelized cost of delivering the plant's fuel to each port.

    The delivery cost is production-levelized over the same window as the levelized
    cost of production: the plant's construction lead time followed by its operational
    lifetime, anchored at the evaluation time. Since the plant's annual production is
    constant over the operating window, it cancels from the levelization ratio, leaving
    the per-year operating fraction as the leveling flow.

    Parameters
    ----------
    plant
        Plant delivering its fuel.
    deliveries
        Transport and distance per port name.
    cost_rates
        Transport cost rates already resolved, filled in as new combinations occur.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    region = plant.region
    expectation = plant.expectation

    # the lifetime, discount rate and cost flow may change over time, so the
    # levelized cost of delivery is calculated per time step
    for t, time in enumerate(timeline[idx:], start=idx):
        # Python floats, as they key the cost rates and the flow sizing rounds them
        lead_time = float(expectation.get_lead_time(t))
        lifetime = float(expectation.get_lifetime(t))

        year_starts, operating_flow = build_operating_flows(lead_time, lifetime, time)
        discount_rate = plant.cost_of_capital.get(time)

        for port_name, (transport, distance) in deliveries.items():
            key = (region.name, transport.name, t, lead_time, lifetime)
            if key not in cost_rates:
                rate = region.transport_costs[transport.name]
                cost_rates[key] = rate.get(year_starts)

            cost_flow = cost_rates[key] * distance.get(year_starts) * operating_flow
            cost = calculate_levelized_cost(cost_flow, operating_flow, discount_rate)
            expectation.set_levelized_delivery_cost(t, port_name, cost)


def _calculate_delivery_wtt(
    plant: Plant,
    deliveries: dict[str, tuple[Transport, ForecastInput]],
    emissions: dict[str, Emission],
    wtt_rates: dict[tuple[str, str, str], FloatArray],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate the WTT emissions of delivering the plant's fuel to each port.

    Emissions are undiscounted and thus can be assigned as instantaneous values.

    Parameters
    ----------
    plant
        Plant delivering its fuel.
    deliveries
        Transport and distance per port name.
    emissions
        All emissions in the simulation.
    wtt_rates
        Transport WTT rates already resolved, filled in as new combinations occur.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    region = plant.region
    expectation = plant.expectation
    times = timeline[idx:]

    for port_name, (transport, distance) in deliveries.items():
        distances = distance.get(times)

        for emission_name in emissions:
            key = (region.name, transport.name, emission_name)
            if key not in wtt_rates:
                rate = region.transport_wtt[(transport.name, emission_name)]
                wtt_rates[key] = rate.get(times)

            delivery_wtt = wtt_rates[key] * distances
            expectation.set_delivery_wtt(idx, port_name, emission_name, delivery_wtt)
