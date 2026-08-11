# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Operational profile calculations for vessels on round-trip and regional routes.

The round-trip route models discrete voyages with fixed per-leg distances and port durations,
so annual totals follow directly from voyages per year. The regional route has no discrete
voyages: it supplies an exogenous annual reference pattern (time at sea, sea-condition
distribution, reference speeds, and port calls per year) describing operations absent speed
management. From that pattern two scalars are derived, days_per_call (the port-side constraint
of turnaround, congestion and waiting) and miles_between_calls (the trading-pattern geometry),
which let speed management change speeds while port and sea time respond endogenously: higher
speed raises sea miles per year, hence port calls per year, hence port time per year, which
crowds out sea time and limits the throughput gain. This reproduces the round-trip feedback
(port time as a binding activity constraint) within the aggregate regional representation.
"""

from dataclasses import dataclass, field

import numpy as np

from navigate.core.enum_ import EnergyDemandTypeID, RouteTypeID
from navigate.core.misc import YEAR
from navigate.core.unit import DAY_TO_HOURS, HOUR_TO_DAYS, MWD_TO_GJ
from navigate.route.route import Route
from navigate.util import divide_nonzero, to_numpy
from navigate.vessel import Vessel
from navigate.vessel.power import calculate_technical_speed_limits


@dataclass
class Operations:

    # operations
    distribution: np.ndarray = field(default_factory=lambda: np.empty(0))
    speeds: np.ndarray = field(default_factory=lambda: np.empty(0))
    capacity_utilizations: np.ndarray = field(default_factory=lambda: np.empty(0))
    distances: np.ndarray = field(default_factory=lambda: np.empty(0))

    # voyage
    times_sea: np.ndarray = field(default_factory=lambda: np.empty(0))
    times_port: np.ndarray = field(default_factory=lambda: np.empty(0))
    time_at_sea: float = 0.
    voyages: float = 0.

    # cargo
    miles: float = 0.
    cargo_miles: float = 0.
    cargo_miles_leg: np.ndarray = field(default_factory=lambda: np.empty(0))
    cargo_miles_leg_nominal: np.ndarray = field(default_factory=lambda: np.empty(0))

    # energy
    energy_sea: dict[EnergyDemandTypeID, list[float | np.ndarray]] = field(default_factory=dict)
    energy_port: dict[EnergyDemandTypeID, list[float | np.ndarray]] = field(default_factory=dict)


def update_operational_profile(vessel: Vessel, allow_speed_management: bool, idx: int) -> None:
    """
    Update the operational profile of a vessel based on its current speeds and route.

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
        # if the fleet allows speed management, the best proxy for the vessel's speed
        # is the speed at the previous time-step
        speeds = to_numpy(vessel.expectation.get_speeds(idx - 1))

    else:
        # if the fleet does not allow speed management, use the reference speed from the route
        speeds = to_numpy(vessel.route.speeds)

        # the reference speed may exceed the propulsion converter's maximum power capacity
        # or fall below the minimum load required; if so, truncate it to the limits
        speeds_min, speeds_max = calculate_technical_speed_limits(vessel)
        speeds = np.clip(speeds, speeds_min, speeds_max)

    operations = calculate_operational_profile(vessel, speeds)
    transfer_operational_profile(vessel, operations, idx)


def calculate_operational_profile(vessel: Vessel, speeds: np.ndarray) -> Operations:
    """
    Evaluate the operational profile for a vessel at given speeds.

    The calculation is route-type specific:
      - ROUND_TRIP: derives voyages/year from voyage duration and scales to annual totals.
      - REGIONAL: uses a reference operational pattern and applies endogenous sea/port split.

    Parameters
    ----------
    vessel
        Vessel for which the operational profile is evaluated.
    speeds
        Speeds per leg (knots).

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


def transfer_operational_profile(vessel: Vessel,
                                 operations: Operations,
                                 idx: int) -> None:
    """
    Transfer an evaluated Operations profile into vessel expectation and vessel profile.

    Parameters
    ----------
    vessel
        Vessel for which results are stored.
    operations
        Operations object containing evaluated annualized results.
    idx
        Simulation index at which the results are stored.
    """

    # convert leg-based energy to regional-energy at sea
    regional_energy_sea = convert_to_regional_steps(vessel, operations.energy_sea)

    # transfer expectations
    vessel.expectation.set_voyages(idx, operations.voyages)
    vessel.expectation.set_distances(idx, operations.distances)
    vessel.expectation.set_speeds(idx, operations.speeds)
    vessel.expectation.set_time_sea(idx, operations.times_sea)
    vessel.expectation.set_time_port(idx, operations.times_port)
    vessel.expectation.set_cargo_miles(idx, operations.cargo_miles)
    vessel.expectation.set_cargo_miles_per_leg(idx, operations.cargo_miles_leg)
    vessel.expectation.set_cargo_miles_per_leg_nominal(idx, operations.cargo_miles_leg_nominal)
    vessel.expectation.set_raw_energy_sea(idx, operations.energy_sea)
    vessel.expectation.set_raw_energy_port(idx, operations.energy_port)
    vessel.expectation.set_regional_raw_energy_sea(idx, regional_energy_sea)

    # calculate the total energy across legs for transfer to output
    total_energy_sea = {energy_id: np.sum(energy) for energy_id, energy in operations.energy_sea.items()}
    total_energy_port = {energy_id: np.sum(energy) for energy_id, energy in operations.energy_port.items()}

    # transfer results to vessel profile
    vessel.profile.set_time_at_sea(idx, operations.time_at_sea)
    vessel.profile.set_voyages(idx, operations.voyages)
    vessel.profile.set_miles(idx, operations.miles)
    vessel.profile.set_cargo_miles(idx, operations.cargo_miles)
    vessel.profile.set_time_sea(idx, np.sum(operations.times_sea))
    vessel.profile.set_time_port(idx, np.sum(operations.times_port))
    vessel.profile.set_raw_energy_sea(idx, total_energy_sea)
    vessel.profile.set_raw_energy_port(idx, total_energy_port)

    # the reference speed must be calculated specifically in case speed management is activated
    reference_speeds = to_numpy(vessel.route.speeds)
    reference_speed = np.average(reference_speeds, weights=operations.distribution)
    vessel.profile.set_reference_speed(idx, reference_speed)


def convert_to_regional_steps(vessel: Vessel,
                              energy_sea: dict[EnergyDemandTypeID, list[float | np.ndarray] | np.ndarray],
                              ) -> dict[EnergyDemandTypeID, list[float | np.ndarray]]:
    """
    Redistribute energy demand at sea into regional steps based on the voyage distribution.

    Parameters
    ----------
    vessel
        Vessel whose route defines the regional legs and voyage distribution.
    energy_sea
        Energy demand at sea per energy demand type, one value per leg.

    Returns
    -------
    Energy demand at sea redistributed across regional legs; the input unchanged if the
    route is not a regional trip.
    """

    route = vessel.route

    if route.route_type != RouteTypeID.REGIONAL_TRIP:
        return energy_sea

    n_leg = route.get_number_of_regional_legs()
    out_sea = {demand_type: [0. for _ in range(n_leg)] for demand_type in energy_sea.keys()}
    sailing_fractions = route.get_voyage_distribution(to_array=True)

    for energy_id, energy in energy_sea.items():
        total_energy = sum(energy)

        for leg in range(n_leg):
            out_sea[energy_id][leg] = total_energy * sailing_fractions[leg]

    return out_sea


def _calculate_trip(operations: Operations, vessel: Vessel) -> None:
    """
    Compute annual sea/port time and annual distances for a route, storing results in Operations.

    The implementation depends on route type (round-trip vs regional).

    Parameters
    ----------
    operations
        Operations container to be populated.
    vessel
        Vessel providing the route definition with sailing/port parameters.
    """

    route = vessel.route
    route_type = route.route_type
    operations.capacity_utilizations = to_numpy(route.capacity_utilizations)

    if route_type == RouteTypeID.ROUND_TRIP:
        _calculate_round_trip(operations, route)
    else:
        _calculate_regional_trip(operations, route)


def _calculate_round_trip(operations: Operations, route: Route) -> None:
    """
    Compute annualized operational profile for a round-trip route.

    Per-voyage sea times are derived from distances and per-leg speeds, port times are taken
    from port durations, and voyages/year is computed from total voyage duration. All
    quantities are scaled to annual totals.

    Parameters
    ----------
    operations
        Operations container to be populated.
    route
        Round-trip route definition.
    """

    speeds = operations.speeds

    distances = to_numpy(route.distances)
    times_sea = divide_nonzero(distances, speeds) * HOUR_TO_DAYS
    times_port = to_numpy(route.port_durations)

    total_time_sea = np.sum(times_sea)
    distribution = divide_nonzero(times_sea, total_time_sea)
    time_at_sea = total_time_sea / YEAR

    # calculate voyages per year in order to rescale durations and distances to
    # the times and distances covered in a year
    total_time_port = np.sum(times_port)
    voyage_duration = total_time_sea + total_time_port
    voyages = YEAR / voyage_duration

    operations.distribution = distribution
    operations.distances = distances * voyages
    operations.times_sea = times_sea * voyages
    operations.times_port = times_port * voyages
    operations.time_at_sea = time_at_sea * voyages
    operations.voyages = voyages


def _calculate_regional_trip(operations: Operations, route: Route) -> None:
    """
    Calculate the annualized operational profile for a regional-trip route.

    Enforces a 365-day annual time budget while letting the sea/port split respond endogenously
    to speed; see the module docstring for the feedback mechanism.

    Parameters
    ----------
    operations
        Operations on which operational profile results are stored.
    route
        Route supplying the reference operational parameters.
    """

    days_per_call, miles_between_calls = _calculate_regional_reference(route)

    speeds = operations.speeds
    distribution_sea = to_numpy(route.condition_distribution)
    speed_mean = np.average(speeds, weights=distribution_sea)
    miles_per_day = speed_mean * DAY_TO_HOURS

    # calculate the total time at sea as a function of the port time budget defined by
    # the reference pattern: YEAR = sea_days + port_days = sea_days * (1 + port_days_per_sea_day)
    port_days_per_sea_day = days_per_call / miles_between_calls * miles_per_day
    total_time_sea = YEAR / (1. + port_days_per_sea_day)
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
    operations.voyages = 1.


def _calculate_regional_reference(route: Route) -> tuple[float, float]:
    """
    Derive reference (absent speed management) scalars for a regional-trip route.

    Returns the port-days per call and sea-miles between calls implied by the route's exogenous
    reference pattern; see the module docstring for how these anchor the endogenous sea/port split.

    Parameters
    ----------
    route
        Route supplying the reference operational parameters.

    Returns
    -------
    days_per_call
        Port days per call implied by reference time at sea and total port calls.
    miles_between_calls
        Sea miles between calls implied by reference speeds, sea distribution and sea time.
    """

    distribution = to_numpy(route.condition_distribution)
    speeds = to_numpy(route.speeds)

    time_at_sea = route.time_at_sea.get()
    total_time_sea = time_at_sea * YEAR
    total_time_port = (1. - time_at_sea) * YEAR

    port_calls = to_numpy(route.port_calls)
    total_calls = np.sum(port_calls)
    days_per_call = divide_nonzero(total_time_port, total_calls)

    times_sea = total_time_sea * distribution
    distances = speeds * times_sea * DAY_TO_HOURS
    miles = np.sum(distances)
    miles_between_calls = divide_nonzero(miles, total_calls)

    return days_per_call, miles_between_calls


def _calculate_cargo_miles(operations: Operations, vessel: Vessel) -> None:
    """
    Compute annual miles and cargo-miles from annual distances and capacity utilization.

    Parameters
    ----------
    operations
        Operations container with annual distances and capacity utilizations.
    vessel
        Vessel providing the nominal cargo capacity used for cargo-mile calculation.
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
    Compute annual energy demand at sea for propulsion, electrical, and heat loads.

    Parameters
    ----------
    operations
        Operations container with speeds, capacity utilization, and annual sea times.
    vessel
        Vessel providing load models at sea.
    """

    speeds = operations.speeds
    capacity_utilizations = operations.capacity_utilizations
    times_sea = operations.times_sea

    load_propulsion = vessel.propulsion_load.get(speeds, capacity_utilizations)
    load_electrical = vessel.electrical_load_at_sea.get(speeds, capacity_utilizations)
    load_heat = vessel.heat_load_at_sea.get(speeds, capacity_utilizations)

    operations.energy_sea[EnergyDemandTypeID.PROPULSION] = _load_to_energy(load_propulsion, times_sea)
    operations.energy_sea[EnergyDemandTypeID.ELECTRICAL] = _load_to_energy(load_electrical, times_sea)
    operations.energy_sea[EnergyDemandTypeID.HEAT] = _load_to_energy(load_heat, times_sea)


def _calculate_energy_port(operations: Operations, vessel: Vessel) -> None:
    """
    Compute annual energy demand in port for electrical and heat loads.

    Parameters
    ----------
    operations
        Operations container with annual port times by port.
    vessel
        Vessel providing port load models.
    """

    times_port = operations.times_port

    load_electrical = vessel.electrical_load_in_port.get()
    load_heat = vessel.heat_load_in_port.get()

    operations.energy_port[EnergyDemandTypeID.ELECTRICAL] = _load_to_energy(load_electrical, times_port)
    operations.energy_port[EnergyDemandTypeID.HEAT] = _load_to_energy(load_heat, times_port)


def _load_to_energy(load: float | np.ndarray, time: np.ndarray) -> np.ndarray:
    """
    Calculate the energy required to operate at a given load for a given duration.

    Parameters
    ----------
    load
        Load level of the engine, MW.
    time
        Time spent at a given load level, days.

    Returns
    -------
    np.ndarray
        Energy required to operate at the given load level for the given duration.
    """

    return load * time * MWD_TO_GJ
