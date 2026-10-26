# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Operational profile of a vessel: its reference trip sailed at given speeds for a year.

The reference trip (`_trip.py`) gives each leg's miles, each stop's port days and the
sailing conditions on each leg. At given speeds the sea days of one voyage follow from
the leg miles, the port days stay fixed, and the voyages per year are the year over
one voyage's days. Every annual time, distance, cargo-mile and energy is a voyage's
value times the voyages per year, per condition and summed per leg, or per stop.

A TRAMP's voyage is its reference year, so it fixes the port days per sea mile: the port
time per call (turnaround, congestion and waiting) over the sea miles between calls (the
trading-pattern geometry). The number of calls cancels from it, so the port calls only
split the port time between the ports. The ratio lets speed management change speeds
while port and sea time respond endogenously: higher speed raises sea miles per year,
hence port calls per year, hence port time per year, which crowds out sea time and
limits the throughput gain. A LINER's discrete voyages respond the same way, port time
being a binding activity constraint on both.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import EnergyDemandID
from navigate.core.wrap import to_floats
from navigate.simulation.fleet._trip import derive_reference_trip, sum_per_leg
from navigate.simulation.fleet.power import calculate_technical_speed_limits
from navigate.util import (
    HOUR_TO_DAYS,
    YEAR,
    divide_nonzero,
    power_to_energy,
    sum_per_key,
)

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.fleet._trip import ReferenceTrip
    from navigate.util.types_ import FloatArray


@dataclass(init=False)
class Operations:
    """
    Annualized operational profile of one vessel at given speeds.

    Attributes
    ----------
    speeds
        Speed in each condition, in knots.
    distribution
        Share of the sea time spent in each condition.
    distances
        Distance sailed in each condition, in nautical miles/year.
    times_sea
        Time at sea in each condition, in days/year.
    times_port
        Time at each stop, in days/year.
    voyages
        Voyages of the reference trip per year.
    cargo_miles
        Cargo-miles delivered, in cargo-miles/year.
    cargo_miles_leg
        Cargo-miles delivered on each leg, in cargo-miles/year.
    cargo_miles_leg_nominal
        Cargo-miles on each leg at full capacity utilization, in cargo-miles/year.
    energy_sea
        Energy demand at sea per energy demand type and condition, in GJ/year.
    energy_port
        Energy demand in port per energy demand type and stop, in GJ/year.
    """

    # operating point
    speeds: FloatArray

    # trip
    distribution: FloatArray
    distances: FloatArray
    times_sea: FloatArray
    times_port: FloatArray
    voyages: float

    # cargo
    cargo_miles: float
    cargo_miles_leg: FloatArray
    cargo_miles_leg_nominal: FloatArray

    # energy
    energy_sea: dict[EnergyDemandID, FloatArray]
    energy_port: dict[EnergyDemandID, FloatArray]


def update_operations(vessel: Vessel, allow_speed_management: bool, idx: int) -> None:
    """
    Update a vessel's operational profile at its current speeds.

    Parameters
    ----------
    vessel
        Vessel whose operational profile is updated.
    allow_speed_management
        Whether the fleet the vessel belongs to allows speed management.
    idx
        Current time-step index.
    """
    trip = derive_reference_trip(vessel.route)

    if idx > 0 and allow_speed_management:
        # under speed management, the previous time-step's speed is the best proxy
        speeds = np.array(vessel.expectation.get_speeds_condition(idx - 1), dtype=float)

    else:
        speeds_min, speeds_max = calculate_technical_speed_limits(vessel, trip)

        # the route's reference speed may exceed the propulsion converter's power
        # capacity or fall below its minimum load
        speeds = np.clip(trip.speeds, speeds_min, speeds_max)

    operations = calculate_operations(vessel, trip, speeds)
    transfer_operations(vessel, trip, operations, idx)


def calculate_operations(
    vessel: Vessel, trip: ReferenceTrip, speeds: FloatArray
) -> Operations:
    """
    Evaluate a vessel's operational profile at given speeds.

    Parameters
    ----------
    vessel
        Vessel whose operational profile is evaluated.
    trip
        Reference trip of the vessel's route.
    speeds
        Speed in each condition, in knots.

    Returns
    -------
    Operations
        Operational profile evaluated at the given speeds.
    """
    operations = Operations()
    operations.speeds = speeds

    _calculate_trip(operations, trip)
    _calculate_cargo_miles(operations, vessel, trip)

    _calculate_energy_sea(operations, vessel, trip)
    _calculate_energy_port(operations, vessel)

    return operations


def transfer_operations(
    vessel: Vessel, trip: ReferenceTrip, operations: Operations, idx: int
) -> None:
    """
    Store a vessel's evaluated operations on its expectation and results.

    Parameters
    ----------
    vessel
        Vessel whose results are stored.
    trip
        Reference trip the operations were evaluated on.
    operations
        Evaluated annualized operational profile.
    idx
        Current time-step index.
    """
    expectation = vessel.expectation
    results = vessel.results

    expectation.set_speeds_condition(idx, operations.speeds)
    expectation.set_time_sea_condition(idx, operations.times_sea)
    expectation.set_time_port(idx, operations.times_port)
    expectation.set_voyages(idx, operations.voyages)

    expectation.set_cargo_miles(idx, operations.cargo_miles)
    expectation.set_cargo_miles_leg(idx, operations.cargo_miles_leg)
    expectation.set_cargo_miles_leg_nominal(idx, operations.cargo_miles_leg_nominal)

    expectation.set_raw_energy_sea_condition(idx, operations.energy_sea)
    expectation.set_raw_energy_port(idx, operations.energy_port)

    energy_sea = sum_per_key(operations.energy_sea)
    energy_port = sum_per_key(operations.energy_port)

    # the reference speed is weighted by the operated sea time, as speed management
    # may have moved the operated speeds away from the reference speeds
    speed_reference = np.average(trip.speeds, weights=operations.distribution)

    results.cargo_miles[idx] = operations.cargo_miles
    results.reference_speed[idx] = speed_reference

    for key, value in energy_sea.items():
        results.raw_energy_sea[key][idx] = value

    for key, value in energy_port.items():
        results.raw_energy_port[key][idx] = value


def transfer_operational_savings(fleet: Fleet) -> None:
    """
    Transfer the fleet-level operational saving fractions to each vessel's expectation.

    Parameters
    ----------
    fleet
        Fleet whose saving fractions are transferred.
    """
    saving_sea = to_floats(fleet.operational_saving_sea)
    saving_port = to_floats(fleet.operational_saving_port)

    for vessel in fleet.vessels:
        vessel.expectation.set_operational_saving_fraction_sea(saving_sea)
        vessel.expectation.set_operational_saving_fraction_port(saving_port)


def _calculate_trip(operations: Operations, trip: ReferenceTrip) -> None:
    """
    Calculate the voyages per year and the annual sea and port times and distances.

    Parameters
    ----------
    operations
        Operational profile holding the speeds; populated with the trip.
    trip
        Reference trip of the route.
    """
    speeds = operations.speeds
    legs = trip.condition_legs.legs
    shares = trip.shares

    speeds_weighted = shares * speeds
    speeds_leg = sum_per_leg(trip.condition_legs, speeds_weighted)
    mile_shares = divide_nonzero(speeds_weighted, speeds_leg[legs])

    days_leg = divide_nonzero(trip.leg_miles, speeds_leg) * HOUR_TO_DAYS
    days_condition = days_leg[legs] * shares

    days_sea = np.sum(days_leg)
    days_port = np.sum(trip.port_days)
    voyages = YEAR / (days_sea + days_port)

    operations.distribution = divide_nonzero(days_condition, days_sea)
    operations.distances = trip.leg_miles[legs] * mile_shares * voyages
    operations.times_sea = days_condition * voyages
    operations.times_port = trip.port_days * voyages
    operations.voyages = voyages


def _calculate_cargo_miles(
    operations: Operations, vessel: Vessel, trip: ReferenceTrip
) -> None:
    """
    Calculate the annual cargo-miles on each leg from the distances and utilizations.

    Parameters
    ----------
    operations
        Operational profile holding the annual distances.
    vessel
        Vessel providing the nominal cargo capacity.
    trip
        Reference trip holding the utilizations.
    """
    condition_legs = trip.condition_legs
    capacity = vessel.nominal_capacity.get()

    nominal = capacity * operations.distances
    utilized = nominal * trip.utilizations

    operations.cargo_miles_leg = sum_per_leg(condition_legs, utilized)
    operations.cargo_miles_leg_nominal = sum_per_leg(condition_legs, nominal)
    operations.cargo_miles = np.sum(operations.cargo_miles_leg)


def _calculate_energy_sea(
    operations: Operations, vessel: Vessel, trip: ReferenceTrip
) -> None:
    """
    Calculate the annual energy demand at sea: propulsion, electrical and heat.

    Parameters
    ----------
    operations
        Operational profile holding the speeds and annual sea times.
    vessel
        Vessel providing the loads at sea.
    trip
        Reference trip holding the utilizations.
    """
    speeds = operations.speeds
    utilizations = trip.utilizations
    times_sea = operations.times_sea

    load_propulsion = vessel.propulsion_load.get(speeds, utilizations)
    load_electrical = vessel.electrical_load_at_sea.get(speeds, utilizations)
    load_heat = vessel.heat_load_at_sea.get(speeds, utilizations)

    operations.energy_sea = {
        EnergyDemandID.PROPULSION: power_to_energy(load_propulsion, times_sea),
        EnergyDemandID.ELECTRICAL: power_to_energy(load_electrical, times_sea),
        EnergyDemandID.HEAT: power_to_energy(load_heat, times_sea),
    }


def _calculate_energy_port(operations: Operations, vessel: Vessel) -> None:
    """
    Calculate the annual energy demand in port: electrical and heat.

    Parameters
    ----------
    operations
        Operational profile holding the annual time at each stop.
    vessel
        Vessel providing the loads in port.
    """
    times_port = operations.times_port

    load_electrical = vessel.electrical_load_in_port.get()
    load_heat = vessel.heat_load_in_port.get()

    operations.energy_port = {
        EnergyDemandID.ELECTRICAL: power_to_energy(load_electrical, times_port),
        EnergyDemandID.HEAT: power_to_energy(load_heat, times_port),
    }
