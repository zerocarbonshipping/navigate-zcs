# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Estimate each vessel's fair share of the port fuel supply from its energy demand."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import BunkerScopeID, EnergyDemandID, FuelTypeID, RouteTypeID
from navigate.util import divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray, FloatLike


def calculate_fair_share_fuel_supply(
    fleets: dict[str, Fleet],
    fuels: dict[str, Fuel],
    ports: dict[str, Port],
    idx: int,
    scope: BunkerScopeID,
) -> None:
    """
    Calculate fair-share fuel supply from each port for every vessel in the simulation.

    Used as a starting guess for the fair-share of fuel supply during existing
    bunkering.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    fuels
        All fuels in the simulation.
    ports
        All ports in the simulation.
    idx
        Current time-step index.
    scope
        Whether the fair shares are for existing or for expected bunkering.
    """
    fair_share, vessels = _calculate_demand_based_fair_share_fuel_supply(
        fleets, ports, idx, scope
    )

    for v, vessel in vessels.items():
        for port in vessel.route.ports:
            p = port.name

            for f, fuel in fuels.items():
                if f not in vessel.usable_fuels:
                    continue

                fuel_type = fuel.fuel_type

                # existing bunkering evaluates a single time step, where the shares
                # are zero-dimensional arrays
                if scope == BunkerScopeID.EXISTING:
                    vessel.expectation.set_fair_share_fuel_existing(
                        p, f, np.float64(fair_share[(v, p, fuel_type)])
                    )
                else:
                    vessel.expectation.set_fair_share_fuel_expected(
                        idx, p, f, fair_share[(v, p, fuel_type)]
                    )


def _calculate_demand_based_fair_share_fuel_supply(
    fleets: dict[str, Fleet],
    ports: dict[str, Port],
    idx: int,
    scope: BunkerScopeID,
) -> tuple[dict[tuple[str, str, FuelTypeID], FloatArray], dict[str, Vessel]]:
    """
    Calculate the fair-share fuel type supply from each port for every vessel.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    ports
        All ports in the simulation.
    idx
        Current time-step index.
    scope
        Whether the fair shares are for existing or for expected bunkering; expected
        bunkering evaluates the remaining timeline.

    Returns
    -------
    tuple[dict[tuple[str, str, FuelTypeID], FloatArray], dict[str, Vessel]]
        Fair share of the fuel type supply per (vessel, port, fuel type), and every
        vessel in the simulation by name.
    """
    time_index = idx if scope == BunkerScopeID.EXISTING else np.s_[idx:]

    vessels = {
        vessel.name: vessel for fleet in fleets.values() for vessel in fleet.vessels
    }

    multipliers = {
        vessel.name: fleet.expectation.get_existing_multipliers(vessel.name, time_index)
        if scope == BunkerScopeID.EXISTING
        else fleet.expectation.get_expected_multipliers(vessel.name, time_index)
        for fleet in fleets.values()
        for vessel in fleet.vessels
    }

    all_demand: dict[tuple[str, str, FuelTypeID], FloatLike] = {
        (v, p, ft): 0.0 for v in vessels for p in ports for ft in FuelTypeID
    }

    for v, vessel in vessels.items():
        for p, port in ports.items():
            type_demand = _calculate_fuel_type_demand_in_port_jurisdiction(
                port, vessel, time_index
            )

            for ft, demand in type_demand.items():
                all_demand[(v, p, ft)] = demand

    total_demand = {
        (p, ft): sum(all_demand[(v, p, ft)] * multipliers[v] for v in vessels)
        for p in ports
        for ft in FuelTypeID
    }

    fair_share = {}
    for v, vessel in vessels.items():
        for port in vessel.route.ports:
            p = port.name

            for ft in FuelTypeID:
                if ft not in vessel.usable_fuel_types:
                    continue

                share = divide_nonzero(all_demand[(v, p, ft)], total_demand[(p, ft)])
                fair_share[(v, p, ft)] = share

    return fair_share, vessels


def _calculate_fuel_type_demand_in_port_jurisdiction(
    port: Port, vessel: Vessel, idx: int | slice
) -> dict[FuelTypeID, FloatLike]:
    """
    Calculate a vessel's potential energy demand per fuel type in port's jurisdiction.

    Parameters
    ----------
    port
        Port for which energy calculation is made.
    vessel
        Vessel operating in the jurisdiction of the port.
    idx
        Time-step index, or the slice of the remaining timeline.

    Returns
    -------
    dict[FuelTypeID, FloatLike]
        Potential energy demand per fuel type.
    """
    raw_energy = _calculate_operational_demand_in_port_jurisdiction(vessel, port, idx)

    fuel_type_demand: dict[FuelTypeID, FloatLike] = dict.fromkeys(FuelTypeID, 0.0)

    for energy_id in EnergyDemandID:
        converter = vessel.power_system.get_converter_by_energy_type(energy_id)
        energy = raw_energy[energy_id]

        main_fuel_types = converter.main_fuel_types
        pilot_fuel_types = converter.pilot_fuel_types

        # a dual-fuel converter burns all but its minimum pilot fuel share as main
        # fuel at most, and up to all of its energy as pilot fuel; a mono-fuel
        # converter burns main fuel only
        if converter.is_dual_fuel():
            maximum_main_fuel = 1.0 - converter.minimum_pilot_fuel.get()
            maximum_pilot_fuel = 1.0
        else:
            maximum_main_fuel = 1.0
            maximum_pilot_fuel = 0.0

        for main_fuel_type in main_fuel_types:
            fuel_type_demand[main_fuel_type] += energy * maximum_main_fuel

        for pilot_fuel_type in pilot_fuel_types:
            fuel_type_demand[pilot_fuel_type] += energy * maximum_pilot_fuel

    return fuel_type_demand


def _calculate_operational_demand_in_port_jurisdiction(
    vessel: Vessel, port: Port, idx: int | slice
) -> dict[EnergyDemandID, FloatArray]:
    """
    Calculate operational energy demand for a vessel within a port's jurisdiction.

    Parameters
    ----------
    vessel
        Vessel operating in the jurisdiction of the port.
    port
        Port for which energy calculation is made.
    idx
        Time-step index, or the slice of the remaining timeline.

    Returns
    -------
    dict[EnergyDemandID, FloatArray]
        Operational energy used within the port jurisdiction.
    """
    expectation = vessel.expectation

    operational_demand_sea = expectation.get_operational_energy_sea(idx=idx)
    operational_demand_port = expectation.get_operational_energy_port(idx=idx)

    return _calculate_energy_in_port_jurisdiction(
        vessel, port, operational_demand_sea, operational_demand_port
    )


def _calculate_energy_in_port_jurisdiction(
    vessel: Vessel,
    port: Port,
    energy_sea: dict[EnergyDemandID, list[FloatLike]],
    energy_port: dict[EnergyDemandID, list[FloatLike]],
) -> dict[EnergyDemandID, FloatArray]:
    """
    Calculate the energy demand or spend for a vessel within a port's jurisdiction.

    Parameters
    ----------
    vessel
        Vessel operating under the jurisdiction of the regulation.
    port
        Port for which energy calculation is made.
    energy_sea
        Energy per leg at sea (either demand or spend).
    energy_port
        Energy per port (either demand or spend).

    Returns
    -------
    dict[EnergyDemandID, FloatArray]
        Energy used within the port jurisdiction.
    """
    route = vessel.route
    route_type = route.route_type
    ports = route.ports

    timeline_shape = np.shape(energy_sea[EnergyDemandID.PROPULSION][0])
    energy = {energy_id: np.zeros(timeline_shape) for energy_id in EnergyDemandID}

    if port not in ports:
        return energy

    # a voyage between two ports counts half to the jurisdiction of each
    jurisdiction_fraction = 0.5

    if route_type == RouteTypeID.REGIONAL_TRIP:
        port_idx = ports.index(port)
        port_name = port.name

        voyage_distribution = route.get_voyage_distribution()

        for energy_id in EnergyDemandID:
            total_energy_sea = np.add.reduce(np.asarray(energy_sea[energy_id]))

            for (p_from, p_to), fraction in voyage_distribution.items():
                if (p_from == p_to) and p_from == port_name:
                    energy[energy_id] += total_energy_sea * fraction

                elif (p_from == port_name) or (p_to == port_name):
                    energy[energy_id] += (
                        jurisdiction_fraction * total_energy_sea * fraction
                    )

            if energy_id != EnergyDemandID.PROPULSION:
                energy[energy_id] += energy_port[energy_id][port_idx]

    else:
        n_legs = route.get_number_of_legs()

        for energy_id in EnergyDemandID:
            for p, route_port in enumerate(ports):
                if route_port == port and energy_id != EnergyDemandID.PROPULSION:
                    energy[energy_id] += energy_port[energy_id][p]

            for leg in range(n_legs):
                port_from = ports[leg]
                # the last leg returns to the first port
                port_to = ports[(leg + 1) % n_legs]

                if (port_from == port) or (port_to == port):
                    energy[energy_id] += (
                        jurisdiction_fraction * energy_sea[energy_id][leg]
                    )

    return energy
