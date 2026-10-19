# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Per-step fleet and vessel output transfers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import FuelTypeID
from navigate.simulation.cohort import find_origin_index
from navigate.simulation.fleet.composition import get_multiplier
from navigate.simulation.fleet.power import get_total_power_capacity
from navigate.util import YEAR, divide_nonzero, interpolate_yearly_flow

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray


def calculate_fleet_profile(fleet: Fleet, timeline: FloatArray, idx: int) -> None:
    """
    Transfer the fleet's expenses, weighted age, fuel-type capacity, counts and uptake.

    The increment-based cost transfers need the live cohort composition. Output-only
    profile aggregation happens in navigate.simulation.fleet.post_process after the
    simulation.

    Parameters
    ----------
    fleet
        Fleet instance.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    _transfer_increment_expenses(fleet, timeline, idx)
    _transfer_weighted_age(fleet, idx)
    _transfer_fuel_type_capacity(fleet, idx)
    _transfer_multipliers(fleet, idx)
    _transfer_technology_uptake(fleet, idx)


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

    for v, vessel in enumerate(fleet.vessels):
        for inc in fleet.increments[v]:
            # the cost profile is that of a vessel entering the fleet 'age' years
            # ago; an increment of the initial fleet uses the profile at the
            # simulation start, as historical cost data is unknown
            origin = find_origin_index(years, current_year, inc.age)
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
    for v, vessel in enumerate(fleet.vessels):
        incs = fleet.increments[v]
        power = get_total_power_capacity(vessel)

        age_power_sum = float(sum(inc.age * inc.multiplier for inc in incs)) * power
        count_power_sum = float(get_multiplier(fleet, v)) * power

        fleet.profile.add_weighted_age(
            vessel.primary_fuel_type, age_power_sum, count_power_sum, idx
        )


def _transfer_fuel_type_capacity(fleet: Fleet, idx: int) -> None:
    """
    Transfer the fleet's fuel-type capacity totals to the output profile.

    Parameters
    ----------
    fleet
        Fleet instance.
    idx
        Current time-step index.
    """
    for fuel_type in FuelTypeID:
        fleet.profile.add_fuel_type_capacity(
            fuel_type, fleet.expectation.get_fuel_type_capacity(fuel_type), idx
        )


def _transfer_multipliers(fleet: Fleet, idx: int) -> None:
    """
    Transfer the current multiplier state to the profile for output.

    Parameters
    ----------
    fleet
        Fleet instance.
    idx
        Current time-step index.
    """
    for v, vessel in enumerate(fleet.vessels):
        fleet.profile.set_existing_vessels(idx, vessel.name, get_multiplier(fleet, v))


def _transfer_technology_uptake(fleet: Fleet, idx: int) -> None:
    """
    Transfer the newbuild and fleet-average technology uptake to the fleet profile.

    Parameters
    ----------
    fleet
        Fleet whose uptake is transferred.
    idx
        Current time-step index.
    """
    for v, vessel in enumerate(fleet.vessels):
        for p, _package in enumerate(fleet.technology_packages[1:], start=1):
            t = fleet.package_to_technology_map[p]
            technology = fleet.technologies[t]

            nb_uptake = np.sum(fleet.newbuild_package_uptake[v][p:])
            fleet.profile.set_newbuild_technology_uptake(
                idx, vessel.name, technology.name, nb_uptake
            )

            weighted_uptake = 0.0
            weight = 0.0
            for inc in fleet.increments[v]:
                inc_uptake = float(np.sum(inc.package_uptake[p:]))
                weighted_uptake += inc_uptake * inc.multiplier
                weight += inc.multiplier

            avg_uptake = float(divide_nonzero(weighted_uptake, weight))
            fleet.profile.set_technology_uptake(
                idx, vessel.name, technology.name, avg_uptake
            )


def calculate_vessel_profile(vessel: Vessel, idx: int) -> None:
    """
    Write the vessel's lifetime and lead time to its profile.

    Parameters
    ----------
    vessel
        Vessel instance.
    idx
        Current time-step index.
    """
    vessel.profile.set_lifetime(idx, vessel.lifetime.get())
    vessel.profile.set_lead_time(idx, vessel.lead_time.get())
