# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Estimate each vessel's potential fuel-type demand at the ports of its route."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import EnergyDemandID, FuelTypeID

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.route import Route
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatLike


def calculate_potential_fuel_type_demand(fleets: dict[str, Fleet], idx: int) -> None:
    """
    Calculate every vessel's potential fuel-type demand at the ports of its route.

    The demand at a port is the most of each fuel type the vessel could burn at and
    around it, from each stop there and half of each leg per end there, by which the
    bunkering shares the port's fuel supply among the vessels calling there. It
    covers the remaining timeline: the existing bunkering reads the current
    time-step, the expected bunkering all of it.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.
    """
    remaining = np.s_[idx:]

    for fleet in fleets.values():
        for vessel in fleet.vessels:
            expectation = vessel.expectation

            energy_sea_leg = expectation.get_operational_energy_sea_leg(remaining)
            energy_port = expectation.get_operational_energy_port(remaining)

            demand = _calculate_vessel_demand(vessel, energy_sea_leg, energy_port)
            expectation.set_potential_fuel_type_demand(idx, demand)


def _calculate_vessel_demand(
    vessel: Vessel,
    energy_sea_leg: Mapping[EnergyDemandID, Sequence[FloatLike]],
    energy_port: Mapping[EnergyDemandID, Sequence[FloatLike]],
) -> dict[tuple[str, FuelTypeID], FloatLike]:
    """
    Calculate a vessel's potential demand per fuel type at each port of its route.

    Parameters
    ----------
    vessel
        Vessel whose demand is calculated.
    energy_sea_leg
        Operational energy at sea per energy demand type and leg, in the order of
        `Route.get_legs`, in GJ/year.
    energy_port
        Operational energy in port per energy demand type and stop, in GJ/year.

    Returns
    -------
    dict[tuple[str, FuelTypeID], FloatLike]
        Potential demand per (port name, fuel type), in GJ/year.
    """
    route = vessel.route
    demand: dict[tuple[str, FuelTypeID], FloatLike] = {}

    for port in dict.fromkeys(route.ports):
        energy = _calculate_energy_at_port(route, port, energy_sea_leg, energy_port)
        fuel_type_demand = _calculate_fuel_type_demand(vessel, energy)

        for fuel_type, value in fuel_type_demand.items():
            demand[(port.name, fuel_type)] = value

    return demand


def _calculate_energy_at_port(
    route: Route,
    port: Port,
    energy_sea_leg: Mapping[EnergyDemandID, Sequence[FloatLike]],
    energy_port: Mapping[EnergyDemandID, Sequence[FloatLike]],
) -> dict[EnergyDemandID, FloatLike]:
    """
    Calculate the energy a vessel spends at and around a port of its route.

    A stop at the port counts wholly, and a leg counts half for each of its ends at
    the port.

    Parameters
    ----------
    route
        Route of the vessel.
    port
        Port of the route.
    energy_sea_leg
        Energy at sea per energy demand type and leg, in GJ/year.
    energy_port
        Energy in port per energy demand type and stop, in GJ/year.

    Returns
    -------
    dict[EnergyDemandID, FloatLike]
        Energy at the port per energy demand type, in GJ/year.
    """
    ports = route.ports
    legs = route.get_legs()
    leg_weights = [_calculate_leg_weight(ports[i], ports[e], port) for i, e in legs]

    energy: dict[EnergyDemandID, FloatLike] = dict.fromkeys(EnergyDemandID, 0.0)

    for energy_id, energy_stops in energy_port.items():
        for stop_port, energy_stop in zip(ports, energy_stops, strict=True):
            if stop_port == port:
                energy[energy_id] += energy_stop

    for energy_id, energy_legs in energy_sea_leg.items():
        for weight, energy_leg in zip(leg_weights, energy_legs, strict=True):
            energy[energy_id] += weight * energy_leg

    return energy


def _calculate_leg_weight(origin: Port, destination: Port, port: Port) -> float:
    """Calculate the weight of a leg at a port, half for each of its ends there."""
    ends_at_port = (origin == port) + (destination == port)
    return 0.5 * ends_at_port


def _calculate_fuel_type_demand(
    vessel: Vessel, energies: Mapping[EnergyDemandID, FloatLike]
) -> dict[FuelTypeID, FloatLike]:
    """
    Calculate the most of each fuel type the converters can burn for the given energy.

    Parameters
    ----------
    vessel
        Vessel whose converters burn the fuel.
    energies
        Energy per energy demand type, in GJ/year.

    Returns
    -------
    dict[FuelTypeID, FloatLike]
        Potential demand per fuel type, in GJ/year.
    """
    fuel_type_demand: dict[FuelTypeID, FloatLike] = dict.fromkeys(FuelTypeID, 0.0)

    for energy_id in EnergyDemandID:
        converter = vessel.power_system.get_converter_by_energy_type(energy_id)
        energy = energies[energy_id]

        # a dual-fuel converter burns all but its minimum pilot fuel share as main
        # fuel at most, and up to all of its energy as pilot fuel; a mono-fuel
        # converter burns main fuel only
        if converter.is_dual_fuel():
            maximum_main_fuel = 1.0 - converter.minimum_pilot_fuel.get()
            maximum_pilot_fuel = 1.0
        else:
            maximum_main_fuel = 1.0
            maximum_pilot_fuel = 0.0

        for main_fuel_type in converter.main_fuel_types:
            fuel_type_demand[main_fuel_type] += energy * maximum_main_fuel

        for pilot_fuel_type in converter.pilot_fuel_types:
            fuel_type_demand[pilot_fuel_type] += energy * maximum_pilot_fuel

    return fuel_type_demand
