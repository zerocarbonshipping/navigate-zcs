# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import FuelTypeID
from navigate.fleet.utils import get_total_power_capacity
from navigate.util import YEAR, get_increment_origin_index, interpolate_tied_capital

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.fuel import Fuel


def calculate_fleet_profile(
    fleet: Fleet, fuels: dict[str, Fuel], timeline: np.ndarray, idx: int
) -> None:
    """
    Calculate the per-step fleet state: the increment-based cost transfers,
    which need the live cohort composition, and the fuel-type demand/supply
    totals on the fleet expectation, which the next step's fuel conversion
    reads. Output-only profile aggregation happens in
    navigate.fleet.post_process after the simulation.

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
    _transfer_increment_expenses(fleet, timeline, idx)
    _transfer_weighted_age(fleet, idx)
    _gather_fuel_type_demand(fleet)
    _gather_fuel_type_supply(fleet, fuels, idx)
    _transfer_fuel_type_demand(fleet, idx)


def _transfer_increment_expenses(fleet: Fleet, timeline: np.ndarray, idx: int) -> None:
    """
    Transfer the running vessel expenses per increment: instantaneous charter
    rate, remaining tied-up capital, and the carried technology charge.

    Parameters
    ----------
    fleet
        Fleet instance.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    """
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
            tied_capital = interpolate_tied_capital(tied_capital_flow, inc.age)

            fleet.profile.add_vessel_expenses(cost * inc.multiplier, idx)
            fleet.profile.add_vessel_tied_capital(tied_capital * inc.multiplier, idx)

            # the carried technology charge is the levelized analogue of the
            # asset charter rate for the cohort's installed technologies
            fleet.profile.add_technology_expenses(
                inc.technology_charter_rate * inc.multiplier, idx
            )


def _transfer_weighted_age(fleet: Fleet, idx: int) -> None:
    """
    Transfer the power-weighted average fleet age per fuel type as separate
    numerator (age * count * power) and denominator (count * power) sums.

    Parameters
    ----------
    fleet
        Fleet instance.
    idx
        Current time-step index.
    """
    for v, vessel in enumerate(fleet.assets):
        power = get_total_power_capacity(vessel)

        age_power_sum = (
            float(sum(inc.age * inc.multiplier for inc in fleet.increments[v])) * power
        )
        count_power_sum = (
            float(sum(inc.multiplier for inc in fleet.increments[v])) * power
        )
        fleet.profile.add_weighted_age(
            vessel.fuel_type, age_power_sum, count_power_sum, idx
        )


def _gather_fuel_type_demand(fleet: Fleet) -> None:
    """
    Gather the fuel type specific demand for the fleet from the latest
    bunkering solution onto the fleet expectation.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    # the reset must come after fleet evolution, which
    # reads the previous step's totals
    fleet.expectation.reset_fuel_type_totals()

    for v, vessel in enumerate(fleet.assets):
        multiplier = fleet.get_multiplier(v)

        if multiplier == 0.0:
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
                pilot_fuel_share = 0.0

            # loop over each main and pilot
            # fuel type and add the demand
            for fuel_type in converter.main_fuel_types:
                fleet.expectation.add_fuel_type_demand(
                    fuel_type, (1.0 - pilot_fuel_share) * fleet_demand
                )

            for fuel_type in converter.pilot_fuel_types:
                fleet.expectation.add_fuel_type_demand(
                    fuel_type, pilot_fuel_share * fleet_demand
                )

        # resetting the previously spend energy
        # values to avoid lingering solutions
        vessel.expectation.reset_spend_energy()


def _gather_fuel_type_supply(fleet: Fleet, fuels: dict[str, Fuel], idx: int) -> None:
    """
    Gather the fuel type specific supply for the fleet from each vessel's
    fair share of the port supplies onto the fleet expectation.

    Parameters
    ----------
    fleet
        Fleet instance.
    fuels
        All fuels in the simulation.
    idx
        Current time-step index.
    """
    for v, vessel in enumerate(fleet.assets):
        multiplier = fleet.get_multiplier(v)

        if multiplier == 0.0:
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
                    fair_share_supply = 0.0

                fleet.expectation.add_fuel_type_supply(fuel_type, fair_share_supply)


def _transfer_fuel_type_demand(fleet: Fleet, idx: int) -> None:
    """
    Transfer the gathered fuel type demand totals to the output profile.

    Parameters
    ----------
    fleet
        Fleet instance.
    idx
        Current time-step index.
    """
    for fuel_type in FuelTypeID:
        fleet.profile.add_fuel_type_demand(
            fuel_type, fleet.expectation.get_fuel_type_demand(fuel_type), idx
        )


def transfer_multipliers_to_profile(fleet: Fleet, idx: int) -> None:
    """
    Transfer the current multiplier state to the profile for output.

    Parameters
    ----------
    fleet
        The fleet instance.
    idx
        Current time-step index.
    """
    for v, vessel in enumerate(fleet.assets):
        fleet.profile.set_existing_vessels(idx, vessel.name, fleet.get_multiplier(v))
