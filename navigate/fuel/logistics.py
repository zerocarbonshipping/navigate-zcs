# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.nodes.emission import Emission
from navigate.core.nodes.plant import Plant
from navigate.core.nodes.port import Port
from navigate.economics.flows import build_operating_flows
from navigate.economics.metric import calculate_levelized_cost


def calculate_plant_logistics_expectations(plants: dict[str, Plant],
                                           ports: dict[str, Port],
                                           emissions: dict[str, Emission],
                                           timeline: np.ndarray, idx: int) -> None:
    """
    Calculate the expected cost and WTT emissions of delivering each plant's fuel to each port.

    The delivery cost and emissions are given by the transport mode and distance assigned per port on the
    plant, combined with the per-distance rates of the plant's region.

    The delivery cost is production-levelized over the same window as the levelized cost of production:
    the plant's construction lead time followed by its operational lifetime, anchored at the evaluation
    time. Since the plant's annual production is constant over the operating window, it cancels from the
    levelization ratio, leaving the per-year operating fraction as the leveling flow.

    Parameters
    ----------
    plants
        All plants in the simulation.
    ports
        All ports in the simulation.
    emissions
        All emissions in the simulation.
    timeline
        Simulation timeline in days since the start of simulation.
    idx
        Current time-step index in the simulation timeline.
    """

    times = timeline[idx:]

    # rate expectations are shared between every plant in the same region
    # using the same transport over the same window: resolve each combination once
    cost_rates = {}
    wtt_rates = {}

    for plant in plants.values():

        region = plant.region
        fuel_name = plant.fuel.name

        # without a transport assignment no delivery cost
        # or emissions accrue: the expectation defaults are zero
        deliveries = [(port_name, plant.fuel_transport[port_name])
                      for port_name, port in ports.items()
                      if port.is_bunkering_allowed(fuel_name) and plant.fuel_transport[port_name] is not None]

        if not deliveries:
            continue

        for t, time in enumerate(times, start=idx):
            # the levelized cost of delivery needs
            # to be calculated per time-step since
            # lifetime, discount rate and the cost-flow
            # may change over time
            lead_time = plant.expectation.get_lead_time(t)
            lifetime = plant.expectation.get_lifetime(t)
            year_flow, overlap = build_operating_flows(time, lead_time, lifetime)
            discount_rate = plant.cost_of_capital.get(time)

            for port_name, transport in deliveries:

                key = (region.name, transport.name, t, lead_time, lifetime)
                if key not in cost_rates:
                    cost_rates[key] = region.transport_cost[transport.name].get(year_flow)

                cost_flow = cost_rates[key] * plant.fuel_distance[port_name].get(year_flow) * overlap
                levelized_cost = calculate_levelized_cost(cost_flow, overlap, discount_rate)
                plant.expectation.set_levelized_delivery_cost(t, port_name, levelized_cost)

        # emissions are undiscounted and thus can
        # be assigned as instantaneous values
        for port_name, transport in deliveries:

            distance = plant.fuel_distance[port_name].get(times)

            for emission_name in emissions:
                key = (region.name, transport.name, emission_name)
                if key not in wtt_rates:
                    wtt_rates[key] = region.transport_wtt[(transport.name, emission_name)].get(times)

                plant.expectation.set_delivery_wtt(idx, port_name, emission_name, wtt_rates[key] * distance)
