# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.enum_ import BunkerScopeID, EnergyDemandTypeID, FuelTypeID, RouteTypeID
from navigate.core.nodes.port import Port
from navigate.core.nodes.vessel import Vessel
from navigate.util import divide_nonzero


def calculate_fair_share_fuel_supply(fleets, fuels, ports, idx, scope):
    """
    Calculates the fair-share of fuel supply from each port for every vessel in the simulation.

    Used as a starting guess for the fair-share of fuel supply during existing bunkering.

    Parameters
    ----------
    fleets : dict[str, Fleet]
        All fleets in the simulation.
    fuels : dict[str, Fuel]
        All fuels in the simulation.
    ports : dict[str, Port]
        All ports in the simulation.
    idx : int
        Current time-step index.
    scope : Enum
        ID of whether this is for expected fuel cost or existing bunkering.
    """

    fair_share, _, _, vessels = _calculate_demand_based_fair_share_fuel_supply(fleets, ports, idx, scope)

    # calculate fair-share for each vessel,
    # port and fuel in tons of fuel
    for v, vessel in vessels.items():

        for port in vessel.route.ports:

            p = port.name

            for f, fuel in fuels.items():

                if f not in vessel.usable_fuels:
                    continue

                fuel_type = fuel.fuel_type

                if scope == BunkerScopeID.EXISTING:
                    vessel.expectation.set_fair_share_fuel_existing(p, f, fair_share[(v, p, fuel_type)])
                else:
                    vessel.expectation.set_fair_share_fuel_expected(idx, p, f, fair_share[(v, p, fuel_type)])


def _calculate_demand_based_fair_share_fuel_supply(fleets, ports, idx, scope):
    """
    Calculates the fair-share of fuel type supply from each port for every vessel in the simulation.

    Parameters
    ----------
    fleets : dict[str, Fleet]
        All fleets in the simulation.
    ports : dict[str, Port]
        All ports in the simulation.
    idx : int
        Current time-step index.
    scope : Enum
        ID of whether this is for expected fuel cost or existing bunkering.


    Returns
    -------
    tuple[dict, dict, dict, dict]
        Fair-share of fuel type supply from each port for every vessel in the simulation.
    """

    if scope == BunkerScopeID.EXISTING:
        _idx = idx
    else:
        _idx = np.s_[idx:]

    vessels = {vessel.name: vessel
               for fleet in fleets.values()
               for vessel in fleet.vessels}

    multipliers = {vessel.name:

                   fleet.expectation.get_existing_multipliers(vessel.name, _idx)
                   if scope == BunkerScopeID.EXISTING
                   else fleet.expectation.get_expected_multipliers(vessel.name, _idx)

                   for fleet in fleets.values()
                   for vessel in fleet.vessels}

    all_demand = {(v, p, ft): 0. for v in vessels for p in ports for ft in FuelTypeID}

    # calculate the individual maximum demand of
    # every vessel in every port for every fuel type
    for v, vessel in vessels.items():
        for p, port in ports.items():

            type_demand = _calculate_fuel_type_demand_in_port_jurisdiction(port, vessel, _idx)

            for ft, demand in type_demand.items():
                all_demand[(v, p, ft)] = demand

    # calculate total demand for
    # each port and fuel type
    total_demand = {(p, ft): 0. for p in ports for ft in FuelTypeID}
    for p in ports:
        for ft in FuelTypeID:
            total_demand[(p, ft)] = sum(all_demand[(v, p, ft)] * multipliers[v] for v in vessels)

    # calculate fair-share for each vessel,
    # port and fuel in tons of fuel
    fair_share = {}
    for v, vessel in vessels.items():

        for port in vessel.route.ports:

            p = port.name

            for ft in FuelTypeID:

                if ft not in vessel.usable_fuel_types:
                    continue

                share = divide_nonzero(all_demand[(v, p, ft)], total_demand[(p, ft)])
                fair_share[(v, p, ft)] = share

    return fair_share, all_demand, multipliers, vessels


def _calculate_fuel_type_demand_in_port_jurisdiction(port, vessel, idx):
    """
    Calculates the potential energy demand per fuel type of a given vessel within the jurisdiction of a given port.

    Parameters
    ----------
    port : Port
        Port for which energy calculation is made.
    vessel : Vessel
        Vessel operating in the jurisdiction of the port.
    idx : int
        Current time-step index.

    Returns
    -------
    dict[str, np.ndarray]
        Potential energy demand per fuel type.
    """

    # calculate the total operational demand
    # that must be satisfied within
    # the jurisdiction of the port
    # for each demand type
    raw_energy = _calculate_operational_demand_in_port_jurisdiction(vessel, port, idx)

    # pre-allocate output container
    fuel_type_demand = {fuel_type: 0. for fuel_type in FuelTypeID}

    # loop over converters and energy for propulsion,
    # electrical, and heat respectively and add the
    # potential demand corresponding to each fuel type
    for energy_id in EnergyDemandTypeID:

        converter = vessel.power_system.get_converter_by_energy_type(energy_id)
        energy = raw_energy[energy_id]

        main_fuel_types = converter.main_fuel_types
        pilot_fuel_types = converter.pilot_fuel_types

        if converter.is_dual_fuel():

            # a dual-fuel vessel can use at most
            # '100% - minimum pilot fuel' as it's
            # main fuel, but can use up to 100%
            # pilot fuel
            maximum_main_fuel = 1. - converter.minimum_pilot_fuel.get()
            maximum_pilot_fuel = 1.

        else:

            # a mono-fuel vessel can only use main fuel
            maximum_main_fuel = 1.
            maximum_pilot_fuel = 0.

        for main_fuel_type in main_fuel_types:
            fuel_type_demand[main_fuel_type] += energy * maximum_main_fuel

        for pilot_fuel_type in pilot_fuel_types:
            fuel_type_demand[pilot_fuel_type] += energy * maximum_pilot_fuel

    return fuel_type_demand


def _calculate_operational_demand_in_port_jurisdiction(vessel: Vessel, port: Port,
                                                       idx: int) -> dict[EnergyDemandTypeID, np.ndarray]:
    """
    Calculates the operational energy demand for a vessel within the jurisdiction of a port.

    Parameters
    ----------
    vessel
        Vessel operating in the jurisdiction of the port.
    port
        Port for which energy calculation is made.
    idx
        Current time-step index.

    Returns
    -------
    Operational energy used within the port jurisdiction.
    """

    expectation = vessel.expectation

    operational_demand_sea = expectation.get_operational_energy_sea(idx=idx)
    operational_demand_port = expectation.get_operational_energy_port(idx=idx)

    return _calculate_energy_in_port_jurisdiction(vessel, port, operational_demand_sea, operational_demand_port)


def _calculate_energy_in_port_jurisdiction(vessel: Vessel,
                                           port: Port,
                                           energy_sea: dict[EnergyDemandTypeID, list[np.ndarray]],
                                           energy_port: dict[EnergyDemandTypeID, list[np.ndarray]],
                                           ) -> dict[EnergyDemandTypeID, np.ndarray]:
    """
    Calculates the energy demand or spend for a vessel within the jurisdiction of a port.

    Parameters
    ----------
    port
        Port for which energy calculation is made.
    vessel
        Vessel operating under the jurisdiction of the regulation.
    energy_sea
        Energy per leg at sea (either demand or spend).
    energy_port
        Energy per port (either demand or spend).

    Returns
    -------
    Energy used within the port jurisdiction.
    """

    # scale the demand by the fraction of time
    # spent in the jurisdiction of the port
    route = vessel.route
    route_type = route.route_type
    ports = route.ports

    # pre-allocate
    timeline_shape = energy_sea[EnergyDemandTypeID.PROPULSION][0].shape
    energy = {energy_id: np.zeros(timeline_shape) for energy_id in EnergyDemandTypeID}

    if port not in ports:
        return energy

    # inter region travel (assume jurisdiction is split 50/50 for fairness)
    jurisdiction_fraction = 0.5

    if route_type == RouteTypeID.REGIONAL_TRIP:

        port_idx = ports.index(port)
        port_name = port.name

        voyage_distribution = route.get_voyage_distribution()

        # sum energy at sea
        for energy_id in EnergyDemandTypeID:

            total_energy_sea = np.add.reduce(energy_sea[energy_id])

            for (p_from, p_to), fraction in voyage_distribution.items():

                # intra region travel
                if (p_from == p_to) and p_from == port_name:

                    energy[energy_id] += total_energy_sea * fraction

                elif (p_from == port_name) or (p_to == port_name):

                    energy[energy_id] += jurisdiction_fraction * total_energy_sea * fraction

            # add energy in port
            if energy_id != EnergyDemandTypeID.PROPULSION:
                energy[energy_id] += energy_port[energy_id][port_idx]

    else:

        ports = route.ports
        n_legs = route.get_number_of_legs()

        # sum energy at sea
        for energy_id in EnergyDemandTypeID:

            for p, route_port in enumerate(ports):
                if route_port == port and energy_id != EnergyDemandTypeID.PROPULSION:
                    energy[energy_id] += energy_port[energy_id][p]

            for leg in range(n_legs):

                # initial and end port
                port_from = ports[leg]
                port_to = ports[(leg + 1) % n_legs]  # periodical boundary condition wrapping around to the first port

                if (port_from == port) or (port_to == port):
                    energy[energy_id] += jurisdiction_fraction * energy_sea[energy_id][leg]

    return energy
