# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The fleet and vessel results written at each time step."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import FuelTypeID
from navigate.simulation.cohort import find_origin_index
from navigate.simulation.fleet._composition import get_multiplier
from navigate.simulation.fleet._package import get_technologies_by_capex
from navigate.simulation.fleet.power import get_total_power_capacity
from navigate.util import YEAR, divide_nonzero, interpolate_yearly_flow

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray


def record_fleet_results(fleet: Fleet, timeline: FloatArray, idx: int) -> None:
    """
    Transfer the fleet's expenses, weighted age, fuel-type capacity, counts and uptake.

    The increment-based cost transfers need the live cohort composition. Output-only
    results aggregation happens in navigate.simulation.fleet.post_process after the
    simulation.

    Parameters
    ----------
    fleet
        Fleet instance.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    _transfer_increment_expenses(fleet, timeline, idx)
    _transfer_weighted_age(fleet, idx)
    _transfer_fuel_type_capacity(fleet, idx)
    _transfer_existing_vessels(fleet, idx)
    _transfer_technology_uptake(fleet, idx)


def _transfer_increment_expenses(fleet: Fleet, timeline: FloatArray, idx: int) -> None:
    """
    Transfer the running vessel expenses per increment.

    Includes the instantaneous charter rate, remaining tied-up capital, and
    the carried technology charge. The technology charge is the levelized
    analogue of the asset charter rate for the cohort's installed technologies.

    Parameters
    ----------
    fleet
        Fleet instance.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    results = fleet.results
    years = timeline / YEAR
    current_year = years[idx]

    for vessel, increments in zip(fleet.vessels, fleet.increments, strict=True):
        expectation = vessel.expectation

        for increment in increments:
            age = increment.age
            multiplier = increment.multiplier

            # the increment bears the costs of a vessel that entered the fleet
            # 'age' years ago
            origin = find_origin_index(years, current_year, age)
            tied_capital_flow = expectation.get_tied_capital(origin)

            asset_charter_rate = expectation.get_asset_charter_rate(origin)
            tied_capital = interpolate_yearly_flow(tied_capital_flow, age)
            technology_charter_rate = increment.technology_charter_rate

            results.vessel_expenses[idx] += asset_charter_rate * multiplier
            results.vessel_tied_capital[idx] += tied_capital * multiplier
            results.technology_expenses[idx] += technology_charter_rate * multiplier


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
    results = fleet.results

    for v, vessel in enumerate(fleet.vessels):
        increments = fleet.increments[v]
        fuel_type = vessel.primary_fuel_type
        power = get_total_power_capacity(vessel)

        cohort_ages = [increment.age * increment.multiplier for increment in increments]
        numerator = sum(cohort_ages) * power
        denominator = get_multiplier(fleet, v) * power

        results.weighted_age_numerator[fuel_type][idx] += numerator
        results.weighted_age_denominator[fuel_type][idx] += denominator


def _transfer_fuel_type_capacity(fleet: Fleet, idx: int) -> None:
    """
    Transfer the fleet's fuel-type capacity totals to the output results.

    Parameters
    ----------
    fleet
        Fleet instance.
    idx
        Current time-step index.
    """
    for fuel_type in FuelTypeID:
        capacity = fleet.expectation.get_fuel_type_capacity(fuel_type)
        fleet.results.fuel_type_capacity[fuel_type][idx] += capacity


def _transfer_existing_vessels(fleet: Fleet, idx: int) -> None:
    """
    Transfer the number of vessels of each type to the results.

    Parameters
    ----------
    fleet
        Fleet instance.
    idx
        Current time-step index.
    """
    for v, vessel in enumerate(fleet.vessels):
        fleet.results.existing_vessels[vessel.name][idx] = get_multiplier(fleet, v)


def _transfer_technology_uptake(fleet: Fleet, idx: int) -> None:
    """
    Transfer the newbuild and fleet-average technology uptake to the fleet results.

    Parameters
    ----------
    fleet
        Fleet whose uptake is transferred.
    idx
        Current time-step index.
    """
    results = fleet.results
    technologies = get_technologies_by_capex(fleet.technology_packages)

    for v, vessel in enumerate(fleet.vessels):
        increments = fleet.increments[v]
        newbuild_package_uptake = fleet.newbuild_package_uptake[v]
        multipliers_total = get_multiplier(fleet, v)

        for i, technology in enumerate(technologies):
            # package i + 1 is the first to hold technology i, as the packages are
            # cumulative, so the technology's uptake is that of every package from it
            key = (vessel.name, technology.name)
            adopting = np.s_[i + 1 :]
            newbuild_uptake = np.sum(newbuild_package_uptake[adopting])

            total = 0.0
            for increment in increments:
                adopting_share = float(np.sum(increment.package_uptake[adopting]))
                total += increment.multiplier * adopting_share

            average = float(divide_nonzero(total, multipliers_total))

            results.newbuild_technology_uptake[key][idx] = newbuild_uptake
            results.technology_uptake[key][idx] = average


def record_vessel_results(vessel: Vessel, idx: int) -> None:
    """
    Write the vessel's lifetime and lead time to its results.

    Parameters
    ----------
    vessel
        Vessel instance.
    idx
        Current time-step index.
    """
    vessel.results.lifetime[idx] = vessel.lifetime.get()
    vessel.results.lead_time[idx] = vessel.lead_time.get()
