# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.general_nodes.bunker_logistics import BunkerLogistics
from navigate.core.nodes.emission import Emission
from navigate.core.nodes.plant import Plant
from navigate.core.nodes.port import Port
from navigate.economics.metric import calculate_age_levelized_cost


def calculate_plant_logistics_expectations(plants: dict[str, Plant],
                                           ports: dict[str, Port],
                                           emissions: dict[str, Emission],
                                           bunker_logistics: BunkerLogistics,
                                           timeline: np.ndarray, idx: int) -> None:
    """


    Parameters
    ----------
    plants
        All plants in the simulation.
    ports
        All ports in the simulation.
    emissions
        All emissions in the simulation.
    bunker_logistics
        General node containing distance between regions and ports and cost of fuel transport.
    timeline
        Simulation timeline in days since the start of simulation.
    idx
        Current time-step index in the simulation timeline.
    """

    _idx = np.s_[idx:]
    times = timeline[_idx]

    # assemble the fuel logistic
    # cost and emission maps
    cost, WTT = _assemble_fuel_logistic_maps(bunker_logistics, times)

    for plant in plants.values():

        region = plant.region
        fuel = plant.fuel

        region_name = region.name
        fuel_name = fuel.name

        for port_name, port in ports.items():

            if not port.is_bunkering_allowed(fuel_name):
                continue

            key = (region_name, port_name, fuel_name)

            for t, time in enumerate(times, start=idx):
                # the levelized cost of delivery needs
                # to be calculated per time-step since
                # lifetime, discount rate and the cost-flow
                # may change over time
                lifetime = plant.expectation.get_lifetime(t)
                discount_rate = plant.cost_of_capital.get(time)
                levelized_cost = calculate_age_levelized_cost(cost[key], lifetime, discount_rate)
                plant.expectation.set_levelized_delivery_cost(t, port_name, levelized_cost)

            # emissions are undiscounted and thus can
            # be assigned as instantaneous values
            for emission_name in emissions:
                key = (region_name, port_name, fuel_name, emission_name)
                plant.expectation.set_delivery_WTT(idx, port_name, emission_name, WTT[key])


def _assemble_fuel_logistic_maps(bunker_logistics: BunkerLogistics,
                                 times: np.ndarray) -> tuple[dict[tuple[str], np.ndarray]]:
    """

    Parameters
    ----------
    bunker_logistics : BunkerLogistics
        General node containing distance between regions and ports and cost of fuel transport.
    times
        Simulation times from the current index onward (typically `timeline[idx:]`).

    Returns
    -------
        A map of the cost of transporting fuel and emissions from transporting fuel respectively.
    """

    distances = bunker_logistics.distances
    transport_costs = bunker_logistics.transport_costs
    transport_WTTs = bunker_logistics.transport_WTT

    # assemble the transport cost map
    cost_map = {}
    for fuel_name, transport_cost in transport_costs.items():

        # calculate the transport
        # unit cost expectation
        cost = transport_cost.get(times)

        for (region_name, port_name), distance in distances.items():

            # calculate the total cost of transport
            # per ton of fuel delivered
            cost_map[(region_name, port_name, fuel_name)] = cost * distance.get()

    # assemble the emissions map
    wtt_map = {}
    for (fuel_name, emission_name), transport_WTT in transport_WTTs.items():

        # calculate the transport
        # unit emission expectation
        wtt = transport_WTT.get(times)

        for (region_name, port_name), distance in distances.items():

            # calculate the total emission of
            # transport per ton of fuel delivered
            wtt_map[(region_name, port_name, fuel_name, emission_name)] = wtt * distance.get()

    return cost_map, wtt_map
