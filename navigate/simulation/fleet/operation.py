# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Operational profile calculations for vessels on round-trip and regional routes.

The round-trip route models discrete voyages with fixed per-leg distances and port
durations, so annual totals follow directly from voyages per year. The regional route
has no discrete voyages: it supplies an exogenous annual reference pattern (time at sea,
sea-condition distribution, reference speeds, and port calls per year) describing
operations absent speed management. That pattern yields one scalar, the port days per
sea mile: the port time per call (turnaround, congestion and waiting) over the sea miles
between calls (the trading-pattern geometry). With it, speed management can change
speeds while port and sea time respond endogenously: higher speed raises sea miles per
year, hence port calls per year, hence port time per year, which crowds out sea time and
limits the throughput gain. This reproduces the round-trip feedback (port time as a
binding activity constraint) within the aggregate regional representation. The number
of port calls cancels from the scalar and only splits the port time between the ports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import EnergyDemandID, RouteTypeID
from navigate.core.wrap import to_numpy
from navigate.simulation.fleet.power import calculate_technical_speed_limits
from navigate.util import DAY_TO_HOURS, HOUR_TO_DAYS, MWD_TO_GJ, YEAR, divide_nonzero

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.route import Route
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.types_ import ForecastInput
    from navigate.util.types_ import FloatArray, FloatLike


@dataclass(init=False)
class Operations:
    """
    Annualized operational profile of one vessel at given speeds.

    Attributes
    ----------
    distribution
        Share of the sea time spent on each leg.
    speeds
        Speed on each leg, in knots.
    utilizations
        Cargo capacity utilization on each leg.
    distances
        Distance sailed on each leg, in nautical miles/year.
    times_sea
        Time at sea on each leg, in days/year.
    times_port
        Time in each port, in days/year.
    voyages
        Voyages per year; one for a regional route.
    cargo_miles
        Cargo-miles delivered, in cargo-miles/year.
    cargo_miles_leg
        Cargo-miles delivered on each leg, in cargo-miles/year.
    cargo_miles_leg_nominal
        Cargo-miles on each leg at full capacity utilization, in cargo-miles/year.
    energy_sea
        Energy demand at sea per energy demand type, one value per leg, in GJ/year.
    energy_port
        Energy demand in port per energy demand type, one value per port, in GJ/year.
    """

    # operations
    distribution: FloatArray
    speeds: FloatArray
    utilizations: FloatArray
    distances: FloatArray

    # voyage
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
        Vessel for which the operational profile is updated.
    allow_speed_management
        Whether the fleet the vessel belongs to allows speed management.
    idx
        Current time-step index.
    """
    if idx > 0 and allow_speed_management:
        # under speed management, the previous time-step's speed is the best proxy
        speeds = np.array(vessel.expectation.get_speeds(idx - 1), dtype=float)

    else:
        speeds = to_numpy(vessel.route.speeds)

        # the route's reference speed may exceed the propulsion converter's power
        # capacity or fall below its minimum load
        speeds_min, speeds_max = calculate_technical_speed_limits(vessel)
        speeds = np.clip(speeds, speeds_min, speeds_max)

    operations = calculate_operations(vessel, speeds)
    transfer_operations(vessel, operations, idx)


def calculate_operations(vessel: Vessel, speeds: FloatArray) -> Operations:
    """
    Evaluate a vessel's operational profile at given speeds.

    A round trip scales one voyage to the voyages per year; a regional route splits
    the year between sea and port from its reference pattern, as the module
    docstring describes.

    Parameters
    ----------
    vessel
        Vessel whose operational profile is evaluated.
    speeds
        Speed on each leg, in knots.

    Returns
    -------
    Operations
        Operational profile evaluated at the given speeds.
    """
    operations = Operations()
    operations.speeds = speeds

    _calculate_trip(operations, vessel)
    _calculate_cargo_miles(operations, vessel)

    _calculate_energy_sea(operations, vessel)
    _calculate_energy_port(operations, vessel)

    return operations


def transfer_operations(vessel: Vessel, operations: Operations, idx: int) -> None:
    """
    Store an evaluated operational profile on the vessel's expectation and profile.

    Parameters
    ----------
    vessel
        Vessel whose results are stored.
    operations
        Evaluated annualized operational profile.
    idx
        Current time-step index.
    """
    expectation = vessel.expectation
    profile = vessel.profile

    expectation.set_voyages(idx, operations.voyages)
    expectation.set_speeds(idx, operations.speeds)
    expectation.set_time_sea(idx, operations.times_sea)
    expectation.set_time_port(idx, operations.times_port)

    expectation.set_cargo_miles(idx, operations.cargo_miles)
    expectation.set_cargo_miles_per_leg(idx, operations.cargo_miles_leg)
    expectation.set_cargo_miles_per_leg_nominal(idx, operations.cargo_miles_leg_nominal)

    expectation.set_raw_energy_sea(idx, operations.energy_sea)
    expectation.set_raw_energy_port(idx, operations.energy_port)

    profile.set_cargo_miles(idx, operations.cargo_miles)
    profile.set_raw_energy_sea(idx, _sum_each(operations.energy_sea))
    profile.set_raw_energy_port(idx, _sum_each(operations.energy_port))

    # the reference speed is recalculated from the route, as speed management may have
    # moved the operated speeds away from it
    reference_speeds = to_numpy(vessel.route.speeds)
    reference_speed = np.average(reference_speeds, weights=operations.distribution)
    profile.set_reference_speed(idx, reference_speed)


def transfer_operational_savings(fleet: Fleet) -> None:
    """
    Transfer the fleet-level operational saving fractions to each vessel's expectation.

    Parameters
    ----------
    fleet
        Fleet whose saving fractions are transferred.
    """
    saving_sea = _evaluate_each(fleet.operational_saving_sea)
    saving_port = _evaluate_each(fleet.operational_saving_port)

    for vessel in fleet.assets:
        vessel.expectation.set_operational_saving_fraction_sea(saving_sea)
        vessel.expectation.set_operational_saving_fraction_port(saving_port)


def convert_to_regional_steps(
    vessel: Vessel, energy_sea: Mapping[EnergyDemandID, Sequence[FloatLike]]
) -> dict[EnergyDemandID, list[FloatLike]]:
    """
    Redistribute the sea energy demand onto regional steps by the voyage distribution.

    Parameters
    ----------
    vessel
        Vessel whose route defines the regional legs and voyage distribution.
    energy_sea
        Energy demand at sea per energy demand type, one value per leg, in GJ/year.

    Returns
    -------
    dict[EnergyDemandID, list[FloatLike]]
        Energy demand at sea redistributed across regional legs; a fresh copy of the
        input, per leg, if the route is not a regional trip.
    """
    route = vessel.route

    if route.route_type != RouteTypeID.REGIONAL_TRIP:
        return {demand: list(energy) for demand, energy in energy_sea.items()}

    fractions = route.get_voyage_distribution(to_array=True)
    return {
        demand: [sum(energy) * fraction for fraction in fractions]
        for demand, energy in energy_sea.items()
    }


def _calculate_trip(operations: Operations, vessel: Vessel) -> None:
    """
    Calculate the annual sea and port times and distances of the vessel's route.

    Parameters
    ----------
    operations
        Operational profile to populate.
    vessel
        Vessel whose route is evaluated.
    """
    route = vessel.route
    operations.utilizations = to_numpy(route.utilizations)

    if route.route_type == RouteTypeID.ROUND_TRIP:
        _calculate_round_trip(operations, route)

    elif route.time_at_sea is not None:
        time_at_sea = route.time_at_sea.get()
        _calculate_regional_trip(operations, route, time_at_sea)


def _calculate_round_trip(operations: Operations, route: Route) -> None:
    """
    Calculate the annualized operational profile of a round-trip route.

    One voyage's sea and port times are scaled by the voyages per year that fit its
    duration.

    Parameters
    ----------
    operations
        Operational profile to populate.
    route
        Round-trip route.
    """
    speeds = operations.speeds
    distances = to_numpy(route.distances)
    times_port = to_numpy(route.port_durations)

    times_sea = divide_nonzero(distances, speeds) * HOUR_TO_DAYS
    total_time_sea = np.sum(times_sea)
    distribution = divide_nonzero(times_sea, total_time_sea)

    total_time_port = np.sum(times_port)
    voyage_duration = total_time_sea + total_time_port
    voyages = YEAR / voyage_duration

    operations.distribution = distribution
    operations.distances = distances * voyages
    operations.times_sea = times_sea * voyages
    operations.times_port = times_port * voyages
    operations.voyages = voyages


def _calculate_regional_trip(
    operations: Operations, route: Route, time_at_sea: float
) -> None:
    """
    Calculate the annualized operational profile of a regional-trip route.

    The sea and port times fill the year and their split responds to speed, as the
    module docstring describes.

    Parameters
    ----------
    operations
        Operational profile to populate.
    route
        Route supplying the reference operational pattern.
    time_at_sea
        Reference share of the year spent at sea.
    """
    speeds = operations.speeds
    distribution = to_numpy(route.condition_distribution)
    port_calls = to_numpy(route.port_calls)

    port_days_per_mile = _calculate_port_days_per_mile(route, time_at_sea)
    speed_mean = np.average(speeds, weights=distribution)

    # the sea and port days fill the year:
    # YEAR = sea_days + port_days = sea_days * (1 + port_days_per_sea_day)
    port_days_per_sea_day = port_days_per_mile * speed_mean * DAY_TO_HOURS
    total_time_sea = YEAR / (1.0 + port_days_per_sea_day)

    times_sea = total_time_sea * distribution
    distances = speeds * times_sea * DAY_TO_HOURS
    miles = np.sum(distances)

    distribution_port = divide_nonzero(port_calls, np.sum(port_calls))
    times_port = miles * port_days_per_mile * distribution_port

    operations.distribution = distribution
    operations.distances = distances
    operations.times_sea = times_sea
    operations.times_port = times_port
    operations.voyages = 1.0


def _calculate_port_days_per_mile(route: Route, time_at_sea: float) -> float:
    """
    Derive the port days per sea mile of a regional route's reference pattern.

    It equals the port days per call over the sea miles between calls, so the number
    of calls cancels; the module docstring describes how it anchors the sea and port
    split.

    Parameters
    ----------
    route
        Route supplying the reference operational pattern.
    time_at_sea
        Reference share of the year spent at sea.

    Returns
    -------
    float
        Port days per sea mile, in days/nautical mile.
    """
    distribution = to_numpy(route.condition_distribution)
    speeds = to_numpy(route.speeds)

    total_time_sea = time_at_sea * YEAR
    total_time_port = (1.0 - time_at_sea) * YEAR

    times_sea = total_time_sea * distribution
    miles = np.sum(speeds * times_sea * DAY_TO_HOURS)

    return total_time_port / miles


def _calculate_cargo_miles(operations: Operations, vessel: Vessel) -> None:
    """
    Calculate the annual cargo-miles from the distances and utilizations.

    Parameters
    ----------
    operations
        Operational profile holding the annual distances and utilizations.
    vessel
        Vessel providing the nominal cargo capacity.
    """
    capacity = vessel.nominal_capacity.get()
    distances = operations.distances
    utilizations = operations.utilizations

    cargo_miles_leg_nominal = capacity * distances
    cargo_miles_leg = cargo_miles_leg_nominal * utilizations

    operations.cargo_miles = np.sum(cargo_miles_leg)
    operations.cargo_miles_leg = cargo_miles_leg
    operations.cargo_miles_leg_nominal = cargo_miles_leg_nominal


def _calculate_energy_sea(operations: Operations, vessel: Vessel) -> None:
    """
    Calculate the annual energy demand at sea: propulsion, electrical and heat.

    Parameters
    ----------
    operations
        Operational profile holding the speeds, utilizations and annual sea times.
    vessel
        Vessel providing the loads at sea.
    """
    speeds = operations.speeds
    utilizations = operations.utilizations
    times_sea = operations.times_sea

    load_propulsion = vessel.propulsion_load.get(speeds, utilizations)
    load_electrical = vessel.electrical_load_at_sea.get(speeds, utilizations)
    load_heat = vessel.heat_load_at_sea.get(speeds, utilizations)

    operations.energy_sea = {
        EnergyDemandID.PROPULSION: _load_to_energy(load_propulsion, times_sea),
        EnergyDemandID.ELECTRICAL: _load_to_energy(load_electrical, times_sea),
        EnergyDemandID.HEAT: _load_to_energy(load_heat, times_sea),
    }


def _calculate_energy_port(operations: Operations, vessel: Vessel) -> None:
    """
    Calculate the annual energy demand in port of the electrical and heat loads.

    Parameters
    ----------
    operations
        Operational profile holding the annual time in each port.
    vessel
        Vessel providing the loads in port.
    """
    times_port = operations.times_port

    load_electrical = vessel.electrical_load_in_port.get()
    load_heat = vessel.heat_load_in_port.get()

    operations.energy_port = {
        EnergyDemandID.ELECTRICAL: _load_to_energy(load_electrical, times_port),
        EnergyDemandID.HEAT: _load_to_energy(load_heat, times_port),
    }


def _load_to_energy(load: FloatLike, time: FloatArray) -> FloatArray:
    """
    Calculate the energy required to operate at a given load for a given duration.

    Parameters
    ----------
    load
        Load level of the engine, in MW.
    time
        Time spent at the load level, in days.

    Returns
    -------
    FloatArray
        Energy required at the load level over the time, in GJ.
    """
    return load * time * MWD_TO_GJ


def _sum_each[T](arrays: Mapping[T, FloatArray]) -> dict[T, float]:
    """
    Sum each array of a mapping, keeping its keys.

    Parameters
    ----------
    arrays
        Arrays to sum, by key.

    Returns
    -------
    dict[T, float]
        Sum of each array, by key.
    """
    return {key: np.sum(array) for key, array in arrays.items()}


def _evaluate_each[T](calculators: Mapping[T, ForecastInput]) -> dict[T, float]:
    """
    Evaluate each calculator of a mapping, keeping its keys.

    Parameters
    ----------
    calculators
        Calculators to evaluate, by key.

    Returns
    -------
    dict[T, float]
        Value of each calculator, by key.
    """
    return {key: calculator.get() for key, calculator in calculators.items()}
