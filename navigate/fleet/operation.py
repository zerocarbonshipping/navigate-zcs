# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Operational profile calculations for vessels on round-trip and regional routes.

The round-trip route models discrete voyages with fixed per-leg distances and port
durations, so annual totals follow directly from voyages per year. The regional route
has no discrete voyages: it supplies an exogenous annual reference pattern (time at sea,
sea-condition distribution, reference speeds, and port calls per year) describing
operations absent speed management. From that pattern two scalars are derived,
days_per_call (the port-side constraint of turnaround, congestion and waiting) and
miles_between_calls (the trading-pattern geometry), which let speed management change
speeds while port and sea time respond endogenously: higher speed raises sea miles per
year, hence port calls per year, hence port time per year, which crowds out sea time and
limits the throughput gain. This reproduces the round-trip feedback (port time as a
binding activity constraint) within the aggregate regional representation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import EnergyDemandTypeID, EnergyDemandTypePortID, RouteTypeID
from navigate.core.wrap import to_numpy
from navigate.fleet.power import calculate_technical_speed_limits
from navigate.util import DAY_TO_HOURS, HOUR_TO_DAYS, MWD_TO_GJ, YEAR, divide_nonzero

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.route import Route
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.types_ import ForecastInput
    from navigate.util.types_ import FloatArray, FloatLike


@dataclass
class Operations:
    """
    Annualized operational profile of one vessel at given speeds.

    Parameters
    ----------
    distribution
        Share of the sea time on each leg, fraction.
    speeds
        Speed on each leg, knots.
    capacity_utilizations
        Capacity utilization on each leg, fraction.
    distances
        Distance sailed on each leg, nautical miles/year.
    times_sea
        Time at sea on each leg, days/year.
    times_port
        Time in each port, days/year.
    time_at_sea
        Share of the year spent at sea, fraction.
    voyages
        Voyages per year; one for a regional route.
    miles
        Distance sailed, nautical miles/year.
    cargo_miles
        Cargo-miles delivered, cargo-miles/year.
    cargo_miles_leg
        Cargo-miles delivered on each leg, cargo-miles/year.
    cargo_miles_leg_nominal
        Cargo-miles on each leg at full capacity utilization, cargo-miles/year.
    energy_sea
        Energy demand at sea per energy demand type, one value per leg, GJ/year.
    energy_port
        Energy demand in port per energy demand type, one value per port, GJ/year.
    """

    # operations
    distribution: FloatArray = field(default_factory=lambda: np.empty(0))
    speeds: FloatArray = field(default_factory=lambda: np.empty(0))
    capacity_utilizations: FloatArray = field(default_factory=lambda: np.empty(0))
    distances: FloatArray = field(default_factory=lambda: np.empty(0))

    # voyage
    times_sea: FloatArray = field(default_factory=lambda: np.empty(0))
    times_port: FloatArray = field(default_factory=lambda: np.empty(0))
    time_at_sea: float = 0.0
    voyages: float = 0.0

    # cargo
    miles: float = 0.0
    cargo_miles: float = 0.0
    cargo_miles_leg: FloatArray = field(default_factory=lambda: np.empty(0))
    cargo_miles_leg_nominal: FloatArray = field(default_factory=lambda: np.empty(0))

    # energy
    energy_sea: dict[EnergyDemandTypeID, FloatArray] = field(default_factory=dict)
    energy_port: dict[EnergyDemandTypeID, FloatArray] = field(default_factory=dict)


def update_operational_profile(
    vessel: Vessel, allow_speed_management: bool, idx: int
) -> None:
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
        speeds = np.array(
            [float(speed) for speed in vessel.expectation.get_speeds(idx - 1)]
        )

    else:
        speeds = to_numpy(vessel.route.speeds)

        # the route's reference speed may exceed the propulsion converter's power
        # capacity or fall below its minimum load
        speeds_min, speeds_max = calculate_technical_speed_limits(vessel)
        speeds = np.clip(speeds, speeds_min, speeds_max)

    operations = calculate_operational_profile(vessel, speeds)
    transfer_operational_profile(vessel, operations, idx)


def calculate_operational_profile(vessel: Vessel, speeds: FloatArray) -> Operations:
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
        Speed on each leg, knots.

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


def transfer_operational_profile(
    vessel: Vessel, operations: Operations, idx: int
) -> None:
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
    vessel.expectation.set_voyages(idx, operations.voyages)
    vessel.expectation.set_speeds(idx, operations.speeds)
    vessel.expectation.set_time_sea(idx, operations.times_sea)
    vessel.expectation.set_time_port(idx, operations.times_port)
    vessel.expectation.set_cargo_miles(idx, operations.cargo_miles)
    vessel.expectation.set_cargo_miles_per_leg(idx, operations.cargo_miles_leg)
    vessel.expectation.set_cargo_miles_per_leg_nominal(
        idx, operations.cargo_miles_leg_nominal
    )
    vessel.expectation.set_raw_energy_sea(idx, operations.energy_sea)
    vessel.expectation.set_raw_energy_port(idx, operations.energy_port)

    total_energy_sea = {
        energy_id: np.sum(energy) for energy_id, energy in operations.energy_sea.items()
    }
    total_energy_port = {
        energy_id: np.sum(energy)
        for energy_id, energy in operations.energy_port.items()
    }

    vessel.profile.set_cargo_miles(idx, operations.cargo_miles)
    vessel.profile.set_raw_energy_sea(idx, total_energy_sea)
    vessel.profile.set_raw_energy_port(idx, total_energy_port)

    # the reference speed is recalculated from the route, as speed management may have
    # moved the operated speeds away from it
    reference_speeds = to_numpy(vessel.route.speeds)
    reference_speed = np.average(reference_speeds, weights=operations.distribution)
    vessel.profile.set_reference_speed(idx, reference_speed)


def convert_to_regional_steps(
    vessel: Vessel,
    energy_sea: Mapping[EnergyDemandTypeID, Sequence[FloatLike]],
) -> dict[EnergyDemandTypeID, list[FloatLike]]:
    """
    Redistribute the sea energy demand onto regional steps by the voyage distribution.

    Parameters
    ----------
    vessel
        Vessel whose route defines the regional legs and voyage distribution.
    energy_sea
        Energy demand at sea per energy demand type, one value per leg, GJ/year.

    Returns
    -------
    dict[EnergyDemandTypeID, list[FloatLike]]
        Energy demand at sea redistributed across regional legs; a fresh copy of the
        input, per leg, if the route is not a regional trip.
    """
    route = vessel.route

    if route.route_type != RouteTypeID.REGIONAL_TRIP:
        return {demand_type: list(energy) for demand_type, energy in energy_sea.items()}

    n_leg = route.get_number_of_regional_legs()
    out_sea: dict[EnergyDemandTypeID, list[FloatLike]] = {
        demand_type: [0.0 for _ in range(n_leg)] for demand_type in energy_sea
    }
    sailing_fractions = route.get_voyage_distribution(to_array=True)

    for energy_id, energy in energy_sea.items():
        total_energy = sum(energy)

        for leg in range(n_leg):
            out_sea[energy_id][leg] = total_energy * sailing_fractions[leg]

    return out_sea


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
    route_type = route.route_type
    operations.capacity_utilizations = to_numpy(route.capacity_utilizations)

    if route_type == RouteTypeID.ROUND_TRIP:
        _calculate_round_trip(operations, route)
    elif route.time_at_sea is not None:
        # a regional trip always has a time at sea, as its requirements check
        # enforces
        _calculate_regional_trip(operations, route, route.time_at_sea)


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
    times_sea = divide_nonzero(distances, speeds) * HOUR_TO_DAYS
    times_port = to_numpy(route.port_durations)

    total_time_sea = np.sum(times_sea)
    distribution = divide_nonzero(times_sea, total_time_sea)
    time_at_sea = total_time_sea / YEAR

    total_time_port = np.sum(times_port)
    voyage_duration = total_time_sea + total_time_port
    voyages = YEAR / voyage_duration

    operations.distribution = distribution
    operations.distances = distances * voyages
    operations.times_sea = times_sea * voyages
    operations.times_port = times_port * voyages
    operations.time_at_sea = time_at_sea * voyages
    operations.voyages = voyages


def _calculate_regional_trip(
    operations: Operations, route: Route, reference_time_at_sea: ForecastInput
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
    reference_time_at_sea
        Reference share of the year spent at sea, fraction.
    """
    days_per_call, miles_between_calls = _calculate_regional_reference(
        route, reference_time_at_sea
    )

    speeds = operations.speeds
    distribution_sea = to_numpy(route.condition_distribution)
    speed_mean = np.average(speeds, weights=distribution_sea)
    miles_per_day = speed_mean * DAY_TO_HOURS

    # the reference pattern fixes the port days per sea day, and
    # YEAR = sea_days + port_days = sea_days * (1 + port_days_per_sea_day)
    port_days_per_sea_day = days_per_call / miles_between_calls * miles_per_day
    total_time_sea = YEAR / (1.0 + port_days_per_sea_day)
    time_at_sea = total_time_sea / YEAR

    times_sea = total_time_sea * distribution_sea
    distances = speeds * times_sea * DAY_TO_HOURS

    miles = np.sum(distances)
    calls_annual = divide_nonzero(miles, miles_between_calls)

    port_calls = to_numpy(route.port_calls)
    total_calls = np.sum(port_calls)
    distribution_port = divide_nonzero(port_calls, total_calls)
    times_port = calls_annual * days_per_call * distribution_port

    operations.distribution = distribution_sea
    operations.distances = distances
    operations.times_sea = times_sea
    operations.times_port = times_port
    operations.time_at_sea = time_at_sea
    operations.voyages = 1.0


def _calculate_regional_reference(
    route: Route, reference_time_at_sea: ForecastInput
) -> tuple[float, float]:
    """
    Derive the port days per call and sea miles between calls of a regional route.

    Both follow from the route's reference pattern, absent speed management; the
    module docstring describes how they anchor the sea and port split.

    Parameters
    ----------
    route
        Route supplying the reference operational pattern.
    reference_time_at_sea
        Reference share of the year spent at sea, fraction.

    Returns
    -------
    float
        Port days per call.
    float
        Sea miles between calls, nautical miles.
    """
    distribution = to_numpy(route.condition_distribution)
    speeds = to_numpy(route.speeds)

    time_at_sea = reference_time_at_sea.get()
    total_time_sea = time_at_sea * YEAR
    total_time_port = (1.0 - time_at_sea) * YEAR

    port_calls = to_numpy(route.port_calls)
    total_calls = np.sum(port_calls)
    # numpy scalars keep numpy division in the caller, which divides by
    # miles_between_calls: a route without port calls gives nan there, not a
    # ZeroDivisionError
    days_per_call = np.float64(divide_nonzero(total_time_port, total_calls))

    times_sea = total_time_sea * distribution
    distances = speeds * times_sea * DAY_TO_HOURS
    miles = np.sum(distances)
    miles_between_calls = np.float64(divide_nonzero(miles, total_calls))

    return days_per_call, miles_between_calls


def _calculate_cargo_miles(operations: Operations, vessel: Vessel) -> None:
    """
    Calculate the annual miles and cargo-miles from the distances and utilizations.

    Parameters
    ----------
    operations
        Operational profile holding the annual distances and capacity utilizations.
    vessel
        Vessel providing the nominal cargo capacity.
    """
    capacity = vessel.nominal_capacity.get()
    distances = operations.distances
    capacity_utilizations = operations.capacity_utilizations

    cargo_miles_leg_nominal = capacity * distances
    cargo_miles_leg = cargo_miles_leg_nominal * capacity_utilizations

    operations.miles = np.sum(distances)
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
    capacity_utilizations = operations.capacity_utilizations
    times_sea = operations.times_sea

    load_propulsion = vessel.propulsion_load.get(speeds, capacity_utilizations)
    load_electrical = vessel.electrical_load_at_sea.get(speeds, capacity_utilizations)
    load_heat = vessel.heat_load_at_sea.get(speeds, capacity_utilizations)

    operations.energy_sea[EnergyDemandTypeID.PROPULSION] = _load_to_energy(
        load_propulsion, times_sea
    )
    operations.energy_sea[EnergyDemandTypeID.ELECTRICAL] = _load_to_energy(
        load_electrical, times_sea
    )
    operations.energy_sea[EnergyDemandTypeID.HEAT] = _load_to_energy(
        load_heat, times_sea
    )


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

    operations.energy_port[EnergyDemandTypeID.ELECTRICAL] = _load_to_energy(
        load_electrical, times_port
    )
    operations.energy_port[EnergyDemandTypeID.HEAT] = _load_to_energy(
        load_heat, times_port
    )


def _load_to_energy(load: FloatLike, time: FloatArray) -> FloatArray:
    """
    Calculate the energy required to operate at a given load for a given duration.

    Parameters
    ----------
    load
        Load level of the engine, MW.
    time
        Time spent at the load level, days.

    Returns
    -------
    FloatArray
        Energy required at the load level over the time, GJ.
    """
    return load * time * MWD_TO_GJ


def transfer_operational_saving_to_vessels(fleet: Fleet) -> None:
    """
    Transfer the fleet-level operational saving fractions to each vessel's expectation.

    Parameters
    ----------
    fleet
        Fleet whose saving fractions are transferred.
    """
    saving_sea = {d: fleet.operational_saving_sea[d].get() for d in EnergyDemandTypeID}
    saving_port = {
        d: fleet.operational_saving_port[d].get() for d in EnergyDemandTypePortID
    }
    for vessel in fleet.assets:
        vessel.expectation.set_operational_saving_fraction_sea(saving_sea)
        vessel.expectation.set_operational_saving_fraction_port(saving_port)
