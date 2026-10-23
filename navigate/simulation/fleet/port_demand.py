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
    around it. Each stop there counts wholly, and each leg half for each of its ends
    there. The bunkering shares the port's fuel supply among the vessels calling
    there by this demand. The demand covers the remaining timeline: the existing
    bunkering reads the current time-step, the expected bunkering all of it.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.
    """
    forward = np.s_[idx:]

    for fleet in fleets.values():
        for vessel in fleet.vessels:
            expectation = vessel.expectation

            energy_sea_leg = expectation.get_operational_energy_sea_leg(forward)
            energy_port = expectation.get_operational_energy_port(forward)

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
        energies = _calculate_energy_at_port(route, port, energy_sea_leg, energy_port)
        fuel_type_demand = _calculate_fuel_type_demand(vessel, energies)

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

    A stop weighs 1 at the port and 0 elsewhere. A leg weighs the mean of its two
    stops' weights, so it counts half for each of its ends at the port.

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
    stops = route.ports
    legs = route.get_legs()

    stop_weights = [float(stop == port) for stop in stops]
    leg_weights = [(stop_weights[i] + stop_weights[j]) / 2.0 for i, j in legs]

    energies: dict[EnergyDemandID, FloatLike] = dict.fromkeys(EnergyDemandID, 0.0)

    for energy_id, energy_stops in energy_port.items():
        for weight, energy_stop in zip(stop_weights, energy_stops, strict=True):
            energies[energy_id] += weight * energy_stop

    for energy_id, energy_legs in energy_sea_leg.items():
        for weight, energy_leg in zip(leg_weights, energy_legs, strict=True):
            energies[energy_id] += weight * energy_leg

    return energies


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
    demand: dict[FuelTypeID, FloatLike] = dict.fromkeys(FuelTypeID, 0.0)

    for energy_id, energy in energies.items():
        converter = vessel.get_converter(energy_id)

        # a dual-fuel converter burns all but its minimum pilot share as main fuel at
        # most, and any converter up to all of its energy as pilot fuel
        if converter.is_dual_fuel():
            main_share = 1.0 - converter.minimum_pilot_fuel.get()
        else:
            main_share = 1.0

        for fuel_type in converter.main_fuel_types:
            demand[fuel_type] += main_share * energy

        for fuel_type in converter.pilot_fuel_types:
            demand[fuel_type] += energy

    return demand
