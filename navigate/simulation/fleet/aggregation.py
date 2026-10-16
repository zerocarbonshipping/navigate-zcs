# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Per-step fleet cost transfers and fuel-type demand and supply totals."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import FuelTypeID
from navigate.simulation.fleet.power import get_total_power_capacity
from navigate.util import YEAR, get_increment_origin_index, interpolate_yearly_flow

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray


def calculate_fleet_profile(
    fleet: Fleet, fuels: dict[str, Fuel], timeline: FloatArray, idx: int
) -> None:
    """
    Calculate the per-step fleet state: cost transfers and fuel-type totals.

    The increment-based cost transfers need the live cohort composition. The
    fuel-type demand/supply totals go on the fleet expectation, which the
    next step's fuel conversion reads. Output-only profile aggregation
    happens in navigate.simulation.fleet.post_process after the simulation.

    Parameters
    ----------
    fleet
        Fleet instance.
    fuels
        All fuels in the simulation.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    _transfer_increment_expenses(fleet, timeline, idx)
    _transfer_weighted_age(fleet, idx)
    _gather_fuel_type_demand(fleet)
    _gather_fuel_type_supply(fleet, fuels, idx)
    _transfer_fuel_type_demand(fleet, idx)


def _transfer_increment_expenses(fleet: Fleet, timeline: FloatArray, idx: int) -> None:
    """
    Transfer the running vessel expenses per increment.

    Includes the instantaneous charter rate, remaining tied-up capital, and
    the carried technology charge.

    Parameters
    ----------
    fleet
        Fleet instance.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    years = timeline / YEAR
    current_year = years[idx]

    for v, vessel in enumerate(fleet.assets):
        for inc in fleet.increments[v]:
            # the cost profile is that of a vessel entering the fleet 'age' years
            # ago; an increment of the initial fleet uses the profile at the
            # simulation start, as historical cost data is unknown
            origin = get_increment_origin_index(years, current_year, inc.age)
            cost = vessel.expectation.get_asset_charter_rate(origin)
            tied_capital_flow = vessel.expectation.get_tied_capital(origin)
            tied_capital = interpolate_yearly_flow(tied_capital_flow, inc.age)

            fleet.profile.add_vessel_expenses(cost * inc.multiplier, idx)
            fleet.profile.add_vessel_tied_capital(tied_capital * inc.multiplier, idx)

            # the carried technology charge is the levelized analogue of the
            # asset charter rate for the cohort's installed technologies
            fleet.profile.add_technology_expenses(
                inc.technology_charter_rate * inc.multiplier, idx
            )


def _transfer_weighted_age(fleet: Fleet, idx: int) -> None:
    """
    Transfer the power-weighted average fleet age per fuel type.

    Stored as separate numerator (age * count * power) and denominator
    (count * power) sums.

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
            vessel.primary_fuel_type, age_power_sum, count_power_sum, idx
        )


def _gather_fuel_type_demand(fleet: Fleet) -> None:
    """
    Gather the fleet's fuel-type demand onto the fleet expectation.

    The demand is sourced from the latest bunkering solution.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    # the reset must come after fleet evolution, which reads the previous step's
    # totals
    fleet.expectation.reset_fuel_type_totals()

    for v, vessel in enumerate(fleet.assets):
        multiplier = fleet.get_multiplier(v)

        if multiplier == 0.0:
            continue

        power_system = vessel.power_system
        converters = power_system.get_converters()

        for converter in converters:
            converter_demand = vessel.expectation.get_spend_energy(converter.name)
            fleet_demand = converter_demand * multiplier

            if converter.is_dual_fuel():
                pilot_fuel_share = converter.minimum_pilot_fuel.get()
            else:
                pilot_fuel_share = 0.0

            for fuel_type in converter.main_fuel_types:
                fleet.expectation.add_fuel_type_demand(
                    fuel_type, (1.0 - pilot_fuel_share) * fleet_demand
                )

            for fuel_type in converter.pilot_fuel_types:
                fleet.expectation.add_fuel_type_demand(
                    fuel_type, pilot_fuel_share * fleet_demand
                )

        # clear the spend energy so no later step reads this solution's values
        vessel.expectation.reset_spend_energy()


def _gather_fuel_type_supply(fleet: Fleet, fuels: dict[str, Fuel], idx: int) -> None:
    """
    Gather the fleet's fuel-type supply onto the fleet expectation.

    Each vessel's supply is its allocation of the port supplies in the latest
    existing bunkering; an infinite port supply counts in full.

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

        # the allocation is per port, so a port the route calls more than once
        # counts once
        for port in dict.fromkeys(vessel.route.ports):
            for fuel_name, fuel in fuels.items():
                if not port.is_bunkering_allowed(fuel_name):
                    continue

                supply_mass = _get_supply_mass(vessel, port, fuel_name, idx)
                supply = supply_mass * fuel.lower_heating_value.get() * multiplier
                fleet.expectation.add_fuel_type_supply(fuel.fuel_type, supply)


def _get_supply_mass(vessel: Vessel, port: Port, fuel_name: str, idx: int) -> float:
    """
    Return the mass of a port's fuel supply that counts for one vessel.

    A finite supply counts as the existing bunkering's allocation to the vessel. The
    bunkering allocates no infinite supply, which counts in full instead: a fuel
    type no active vessel can use yet still has supply to convert to.

    Parameters
    ----------
    vessel
        Vessel holding the allocation.
    port
        Port supplying the fuel.
    fuel_name
        Name of the fuel.
    idx
        Current time-step index.

    Returns
    -------
    float
        Fuel mass counting for one vessel, in tons.
    """
    supply = float(port.expectation.get_bunker_supply(fuel_name, idx))
    if not np.isfinite(supply):
        return supply

    return vessel.expectation.get_allocation_fuel_existing(port.name, fuel_name)


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
        Fleet instance.
    idx
        Current time-step index.
    """
    for v, vessel in enumerate(fleet.assets):
        fleet.profile.set_existing_vessels(idx, vessel.name, fleet.get_multiplier(v))
