# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The results of the vessel, fleet and global profiles, from what was written.

The time steps write energy, fuel, emissions and expenses to the vessel profiles, and
post-processing sums them into the fleet and global profiles. Once a profile holds
its final values, the energies, CO2-equivalents, totals, intensities and savings are
computed from them and written to it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import EnergyDemandID, FuelTypeID
from navigate.util import divide_nonzero, sum_values

if TYPE_CHECKING:
    from navigate.core.profiles import FleetProfile, GlobalProfile, VesselProfile
    from navigate.util.types_ import FloatArray, FloatLike

type _ConsumerProfile = VesselProfile | FleetProfile | GlobalProfile
type _AggregateProfile = FleetProfile | GlobalProfile


def complete_vessel_profile(profile: VesselProfile) -> None:
    """
    Write the results of a vessel profile that combine its written ones.

    Parameters
    ----------
    profile
        Vessel profile, written for the whole run.
    """
    _complete_energy(profile)
    profile.baseline_energy = _baseline_energy(profile.raw_energy, profile.cargo_miles)
    _complete_fuel_consumer(profile)

    initial_energy = profile.raw_energy[0]
    profile.speed_energy_saving = 1.0 - divide_nonzero(
        profile.raw_energy, initial_energy, default=1.0
    )
    profile.operational_energy_saving = 1.0 - divide_nonzero(
        profile.operational_energy, initial_energy, default=1.0
    )
    profile.technology_energy_saving = profile.technology_energy_intensity_saving
    profile.energy_saving = 1.0 - divide_nonzero(
        profile.energy, initial_energy, default=1.0
    )


def complete_fleet_profile(profile: FleetProfile) -> None:
    """
    Write the results of a fleet profile that combine its written ones.

    Parameters
    ----------
    profile
        Fleet profile, its vessels summed into it.
    """
    _complete_energy(profile)
    profile.baseline_energy = _baseline_energy(profile.raw_energy, profile.cargo_miles)
    _complete_fuel_consumer(profile)
    _complete_vessel_aggregate(profile)
    profile.fleet_technology_uptake = _fleet_technology_uptake(profile)


def complete_global_fleet_results(profile: GlobalProfile) -> None:
    """
    Write the fleet results of the global profile computed from its written ones.

    Parameters
    ----------
    profile
        Global profile, the fleets summed into it.
    """
    _complete_energy(profile)
    _complete_fuel_consumer(profile)
    _complete_vessel_aggregate(profile)


def _baseline_energy(raw_energy: FloatArray, cargo_miles: FloatArray) -> FloatArray:
    # the year-0 raw energy intensity times the transport work performed; a fleet
    # with no vessels at the first step has no year-0 intensity to measure against,
    # so its baseline stays 0, its intensity savings read 0, and it adds no baseline
    # to aggregate savings
    growth = divide_nonzero(cargo_miles, cargo_miles[0], default=1.0)
    initial_energy: float = raw_energy[0]
    return initial_energy * growth


def _complete_energy(profile: _ConsumerProfile) -> None:
    shape = profile.context.timeline.shape

    profile.raw_energy = sum_values(profile.raw_energy_sea, shape) + sum_values(
        profile.raw_energy_port, shape
    )
    profile.operational_energy = sum_values(
        profile.operational_energy_sea, shape
    ) + sum_values(profile.operational_energy_port, shape)
    profile.energy = sum_values(profile.energy_sea, shape) + sum_values(
        profile.energy_port, shape
    )


def _complete_fuel_consumer(profile: _ConsumerProfile) -> None:
    # after the energy totals and the baseline energy
    _complete_savings(profile)

    context = profile.context
    shape = context.timeline.shape

    # the fuel burnt and the emissions in energy and CO2-equivalents
    profile.consumed_energy = context.energy(profile.consumed_mass)
    profile.fuel_type_energy = context.fuel_type_energy(profile.consumed_mass)
    profile.converter_energy = {
        (fuel_type, fuel_name): energy
        for fuel_type, mass in profile.converter_mass.items()
        for fuel_name, energy in context.energy(mass).items()
    }
    profile.equivalent_wtt = context.equivalent(profile.wtt)
    profile.equivalent_ttw = context.equivalent(profile.ttw)
    profile.equivalent_wtw = context.equivalent(
        {
            fuel_emission: wtt + profile.ttw[fuel_emission]
            for fuel_emission, wtt in profile.wtt.items()
        }
    )

    profile.total_consumed_energy = (
        sum_values(profile.consumed_energy, shape) + profile.shore_power_energy
    )
    profile.pilot_fuel_share = _pilot_fuel_share(profile)

    # expenses
    profile.fuel_related_expenses = {
        fuel_name: expenses + profile.levy_expenses[fuel_name]
        for fuel_name, expenses in profile.fuel_expenses.items()
    }
    profile.regulation_expenses = (
        profile.remedial_expenses
        + profile.flexibility_expenses
        - profile.surplus_revenue
    )
    profile.total_fuel_expenses = (
        sum_values(profile.fuel_expenses, shape) + profile.shore_power_expenses
    )
    profile.total_fuel_related_expenses = profile.total_fuel_expenses + sum_values(
        profile.levy_expenses, shape
    )

    # emissions, the totals per total energy consumed; shore power emissions are a
    # WTW lump with no (fuel, emission) attribution, so they enter the WTW total but
    # not the per-key results
    consumed = profile.total_consumed_energy
    shore_power = context.equivalent_by_emission(profile.shore_power_emission)
    profile.total_equivalent_wtw = sum_values(
        profile.equivalent_wtw, shape
    ) + sum_values(shore_power, shape)

    profile.intensity_total_equivalent_wtt = _intensity(
        sum_values(profile.equivalent_wtt, shape), consumed
    )
    profile.intensity_total_equivalent_ttw = _intensity(
        sum_values(profile.equivalent_ttw, shape), consumed
    )
    profile.intensity_total_equivalent_wtw = _intensity(
        profile.total_equivalent_wtw, consumed
    )


def _complete_savings(profile: _ConsumerProfile) -> None:
    profile.saving = {
        demand_type: _saving(profile, demand_type) for demand_type in profile.energy_sea
    }

    baseline = profile.baseline_energy
    profile.speed_energy_intensity_saving = 1.0 - divide_nonzero(
        profile.raw_energy, baseline, default=1.0
    )
    profile.operational_energy_intensity_saving = 1.0 - divide_nonzero(
        profile.operational_energy, baseline, default=1.0
    )
    # cargo-miles cancel between energy and operational energy
    profile.technology_energy_intensity_saving = 1.0 - divide_nonzero(
        profile.energy, profile.operational_energy, default=1.0
    )
    profile.energy_intensity_saving = 1.0 - divide_nonzero(
        profile.energy, baseline, default=1.0
    )


def _saving(profile: _ConsumerProfile, demand_type: EnergyDemandID) -> FloatArray:
    if demand_type == EnergyDemandID.PROPULSION:
        return 1.0 - divide_nonzero(
            profile.energy_sea[demand_type],
            profile.raw_energy_sea[demand_type],
            default=1.0,
        )
    return 1.0 - divide_nonzero(
        profile.energy_sea[demand_type] + profile.energy_port[demand_type],
        profile.raw_energy_sea[demand_type] + profile.raw_energy_port[demand_type],
        default=1.0,
    )


def _pilot_fuel_share(profile: _ConsumerProfile) -> dict[FuelTypeID, FloatArray]:
    # the share of a vessel fuel type's converter energy from fuels of other types
    # TODO: may not work when using multiple main fuel types
    fuel_type = profile.context.fuel_type
    share = {}

    for vessel_fuel_type in FuelTypeID:
        fuel_energy = {
            fuel_name: profile.converter_energy[(vessel_fuel_type, fuel_name)]
            for fuel_name in fuel_type
        }
        main_fuel = np.sum(
            [
                energy
                for fuel_name, energy in fuel_energy.items()
                if fuel_type[fuel_name] == vessel_fuel_type
            ],
            axis=0,
        )
        total_fuel = np.sum(list(fuel_energy.values()), axis=0)
        share[vessel_fuel_type] = 1.0 - divide_nonzero(main_fuel, total_fuel)

    return share


def _complete_vessel_aggregate(profile: _AggregateProfile) -> None:
    # after the fuel consumer results, which the expenses total
    profile.weighted_average_age = {
        fuel_type: divide_nonzero(
            numerator, profile.weighted_age_denominator[fuel_type]
        )
        for fuel_type, numerator in profile.weighted_age_numerator.items()
    }

    profile.vessel_related_expenses = (
        profile.vessel_expenses
        + profile.technology_expenses
        + profile.fuel_conversion_expenses
    )
    profile.expenses = (
        profile.total_fuel_related_expenses
        + profile.regulation_expenses
        + profile.vessel_related_expenses
    )


def _fleet_technology_uptake(profile: FleetProfile) -> dict[str, FloatArray]:
    # the average of the vessels' uptake shares, weighted by vessel count; 0 where
    # the fleet is empty
    shares: dict[str, dict[str, FloatArray]] = {}
    for (vessel_name, technology_name), uptake in profile.technology_uptake.items():
        shares.setdefault(technology_name, {})[vessel_name] = uptake

    fleet_uptake: dict[str, FloatArray] = {}
    for technology_name, vessel_shares in shares.items():
        values = np.array(list(vessel_shares.values()))
        weights = np.array(
            [profile.existing_vessels[vessel_name] for vessel_name in vessel_shares]
        )
        fleet_uptake[technology_name] = divide_nonzero(
            (values * weights).sum(axis=0), weights.sum(axis=0)
        )

    return fleet_uptake


def _intensity(emission: FloatArray, energy: FloatLike) -> FloatArray:
    # emissions are converted from ton to g (10^6) and energy from GJ to MJ (10^3),
    # so dividing by 10^3
    return divide_nonzero(emission, energy / 1e3)
