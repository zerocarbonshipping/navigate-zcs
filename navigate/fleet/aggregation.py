# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

import numpy as np

from navigate.core.nodes.vessel import Vessel
from navigate.core.profiles import FleetProfile
from navigate.util import TOLERANCE, YEAR, divide_nonzero, get_increment_origin_index

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.fuel import Fuel

logger = logging.getLogger(__name__)


def calculate_fleet_profile(fleet: Fleet, fuels: dict[str, Fuel], timeline: np.ndarray, idx: int) -> None:
    """
    Calculate the fleet profile for a given time step.

    Parameters
    ----------
    fleet
        Fleet instance.
    fuels
        All fuels in the simulation.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    """

    # transfer boolean to vessel profile
    for v, vessel in enumerate(fleet.assets):
        in_fleet = fleet.get_multiplier(v) > 0.
        vessel.profile.set_in_fleet(idx, in_fleet)

    # transfer emissions and fuel consumer data
    for v, vessel in enumerate(fleet.assets):
        multiplier = fleet.get_multiplier(v)
        fleet.profile.add_fuel_consumer_profile(vessel.profile, multiplier, idx)

    # transfer running vessel expenses
    years = timeline / YEAR
    current_year = years[idx]

    for v, vessel in enumerate(fleet.assets):

        for inc in fleet.increments[v]:

            # find the cost profile corresponding to a vessel entering
            # the fleet at 'age' years ago. Notice here that if the
            # vessel was part of the initial fleet, the cost profile
            # from a vessel at age 0 is used. This is the best available
            # approximation as historical data is unknown
            origin = get_increment_origin_index(years, current_year, inc.age)

            # calculate instantaneous charter rate
            cost = vessel.expectation.get_asset_charter_rate(origin)

            # calculate remaining tied up capital
            tied_capital_flow = vessel.expectation.get_tied_capital(origin)
            time_flow = np.arange(0, tied_capital_flow.size) * YEAR
            tied_capital = np.interp(inc.age * YEAR, time_flow, tied_capital_flow)

            fleet.profile.add_vessel_expenses(cost * inc.multiplier, idx)
            fleet.profile.add_vessel_tied_capital(tied_capital * inc.multiplier, idx)

            # the carried technology charge is the levelized analogue of the
            # asset charter rate for the cohort's installed technologies
            fleet.profile.add_technology_expenses(inc.technology_charter_rate * inc.multiplier, idx)

    # transfer running technology retrofit and fuel conversion expenses
    fleet.profile.add_fuel_conversion_expenses(fleet.fuel_conversion_expenses[idx], idx)

    # transfer power related properties
    for v, vessel in enumerate(fleet.assets):
        vessel_name = vessel.name
        fuel_type = vessel.fuel_type

        # calculate the total installed
        # power on the vessel
        power = sum([c.power_capacity.get() for c in vessel.power_system.get_converters()])

        fleet.profile.add_installed_power(fuel_type, power * fleet.get_multiplier(v), idx)
        fleet.profile.add_newbuild_power(fuel_type, float(power * fleet.profile.get_newbuilds(vessel_name, idx)), idx)
        fleet.profile.add_scrapped_power(fuel_type, float(power * fleet.profile.get_scrap(vessel_name, idx)), idx)

        # weighted average age: accumulate numerator (age * count * power) and denominator (count * power)
        age_power_sum = float(sum(inc.age * inc.multiplier for inc in fleet.increments[v])) * power
        count_power_sum = float(sum(inc.multiplier for inc in fleet.increments[v])) * power
        fleet.profile.add_weighted_age(fuel_type, age_power_sum, count_power_sum, idx)

    # transfer fuel converted power
    vessel_map = {vessel.name: vessel for vessel in fleet.assets}
    fuel_conversions = fleet.profile.get_fuel_conversions(idx=idx)

    for (v_from, v_to), multiplier in fuel_conversions.items():

        if multiplier < TOLERANCE:
            continue

        vessel_from = vessel_map[v_from]
        vessel_to = vessel_map[v_to]

        fuel_type_from = vessel_from.fuel_type
        fuel_type_to = vessel_to.fuel_type

        # calculate the total installed
        # power on the vessels
        power_from = sum([c.power_capacity.get() for c in vessel_from.power_system.get_converters()])
        power_to = sum([c.power_capacity.get() for c in vessel_to.power_system.get_converters()])

        if abs(power_to - power_from) > TOLERANCE:
            logger.warning("{}: Fuel conversion occurred with different installed power {} ({}) to {} ({})."
                           .format(fleet, vessel_from, round(power_from, 1), vessel_to, round(power_to, 1)))

        fleet.profile.add_fuel_converted_power(fuel_type_from, fuel_type_to, float(power_from * multiplier), idx=idx)

    # transfer the fuel type specific demand for the fleet
    for v, vessel in enumerate(fleet.assets):

        multiplier = fleet.get_multiplier(v)

        if multiplier == 0.:
            continue

        # modelling assuming simplified power system
        power_system = vessel.power_system
        converters = power_system.get_converters()

        for converter in converters:

            # extract the spend energy for the
            # given converter from the latest
            # existing bunkering solution
            converter_demand = vessel.expectation.get_spend_energy(converter.name)

            # scale by the number of vessels
            fleet_demand = converter_demand * multiplier

            # extract minimum pilot fuel
            if converter.is_dual_fuel():
                pilot_fuel_share = converter.minimum_pilot_fuel.get()
            else:
                pilot_fuel_share = 0.

            # loop over each main and pilot
            # fuel type and add the demand
            for fuel_type in converter.main_fuel_types:
                fleet.profile.add_fuel_type_demand(fuel_type, (1. - pilot_fuel_share) * fleet_demand, idx)

            for fuel_type in converter.pilot_fuel_types:
                fleet.profile.add_fuel_type_demand(fuel_type, pilot_fuel_share * fleet_demand, idx)

        # resetting the previously spend energy
        # values to avoid lingering solutions
        vessel.expectation.reset_spend_energy()

    # transfer the fuel type specific supply for the fleet
    for v, vessel in enumerate(fleet.assets):

        multiplier = fleet.get_multiplier(v)

        if multiplier == 0.:
            continue

        fair_shares = vessel.expectation.get_fair_share_fuel_existing()

        ports = vessel.route.ports

        for port in ports:

            port_name = port.name

            for fuel_name, fuel in fuels.items():

                if not port.is_bunkering_allowed(fuel_name):
                    continue

                fuel_type = fuel.fuel_type
                supply_mass = port.expectation.get_bunker_supply(fuel_name, idx)
                supply_energy = supply_mass * fuel.lower_heating_value.get()

                key = (port_name, fuel_name)
                if key in fair_shares:

                    if np.isinf(supply_energy):

                        fair_share_supply = np.inf

                    else:

                        fair_share = fair_shares[key]
                        fair_share_supply = supply_energy * fair_share * multiplier

                else:
                    # the fair-share of a certain fuel type
                    # in a port will not have been calculated
                    # if no vessels with that fuel type operate
                    # in the jurisdiction of the port
                    fair_share_supply = 0.

                fleet.profile.add_fuel_type_supply(fuel_type, fair_share_supply, idx)

    # calculate the average speeds of the fleet across all vessel types
    aggregate_speed_profile(fleet.assets, fleet.get_multiplier, fleet.profile, idx)

    # transfer the transport work performed and the counterfactual baseline energy
    transfer_transport_work(fleet, idx)


def transfer_transport_work(fleet: Fleet, idx: int) -> None:
    """
    Transfer the transport work performed and the counterfactual baseline
    energy: what the year-0 raw energy intensity would require to perform
    the transport work actually performed at this time step. A fleet with
    no vessels at the first time step has no year-0 intensity to measure
    against: its baseline stays 0 for the whole simulation, its intensity
    savings read 0, and it contributes no baseline to aggregate savings.

    Parameters
    ----------
    fleet
        Fleet instance.
    idx
        Current time-step index.
    """

    cargo_miles = fleet.get_cargo_miles(idx)
    fleet.profile.set_cargo_miles(idx, cargo_miles)

    growth = divide_nonzero(cargo_miles, fleet.profile.get_cargo_miles(idx=0), default=1.)
    baseline = fleet.profile.get_raw_energy(idx=0) * growth
    fleet.profile.set_baseline_energy(idx, baseline)


def aggregate_speed_profile(assets: list[Vessel],
                            get_multiplier: Callable[[int], float],
                            profile: FleetProfile,
                            idx: int) -> None:
    """
    Aggregate vessel-level speed profiles into fleet-level weighted averages.

    Parameters
    ----------
    assets
        List of vessels in the fleet.
    get_multiplier
        Callable returning the multiplier for vessel index v.
    profile
        Fleet profile to write aggregated results to.
    idx
        Current time-step index.
    """

    reference_speed = 0.
    minimum_speed = 0.
    maximum_speed = 0.
    actual_speed = 0.
    optimal_speed = 0.
    lowest_speed = 0.
    highest_speed = 0.
    reference_multiplier = 0.
    other_multiplier = 0.

    for v, vessel in enumerate(assets):

        vessel_profile = vessel.profile
        multiplier = get_multiplier(v)

        reference = vessel_profile.get_reference_speed(idx)
        minimum = vessel_profile.get_minimum_speed(idx)
        maximum = vessel_profile.get_maximum_speed(idx)
        actual = vessel_profile.get_actual_speed(idx)
        optimal = vessel_profile.get_optimal_speed(idx)
        lowest = vessel_profile.get_lowest_speed(idx)
        highest = vessel_profile.get_highest_speed(idx)

        reference_speed += multiplier * reference if not (np.isnan(reference)) else 0.

        if not (np.isnan(minimum) or np.isnan(maximum) or np.isnan(actual)):

            minimum_speed += multiplier * minimum
            maximum_speed += multiplier * maximum
            actual_speed += multiplier * actual
            optimal_speed += multiplier * optimal
            lowest_speed += multiplier * lowest
            highest_speed += multiplier * highest
            other_multiplier += multiplier

        reference_multiplier += multiplier

    profile.set_reference_speed(idx, reference_speed / reference_multiplier)

    if other_multiplier > 0.:
        profile.set_minimum_speed(idx, minimum_speed / other_multiplier)
        profile.set_maximum_speed(idx, maximum_speed / other_multiplier)
        profile.set_actual_speed(idx, actual_speed / other_multiplier)
        profile.set_optimal_speed(idx, optimal_speed / other_multiplier)
        profile.set_lowest_speed(idx, lowest_speed / other_multiplier)
        profile.set_highest_speed(idx, highest_speed / other_multiplier)
