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

from navigate.core.enum_ import PORT_ENERGY_DEMANDS
from navigate.util import divide_nonzero, sum_values

if TYPE_CHECKING:
    from navigate.core.enum_ import EnergyDemandID, FuelTypeID
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

    _complete_savings(profile)
    _complete_vessel_savings(profile)

    _complete_fuel_consumer(profile)


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

    _complete_savings(profile)

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

    _complete_savings(profile)

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

    raw_sea = sum_values(profile.raw_energy_sea, shape)
    raw_port = sum_values(profile.raw_energy_port, shape)
    operational_sea = sum_values(profile.operational_energy_sea, shape)
    operational_port = sum_values(profile.operational_energy_port, shape)
    energy_sea = sum_values(profile.energy_sea, shape)
    energy_port = sum_values(profile.energy_port, shape)

    profile.raw_energy = raw_sea + raw_port
    profile.operational_energy = operational_sea + operational_port
    profile.energy = energy_sea + energy_port


def _saving(energy: FloatArray, reference: FloatLike) -> FloatArray:
    # no saving where there is no reference to save against
    return 1.0 - divide_nonzero(energy, reference, default=1.0)


def _complete_savings(profile: _ConsumerProfile) -> None:
    profile.saving = _demand_savings(profile)

    # the technology saving is against operational energy, as cargo-miles cancel
    # between the two
    raw_energy = profile.raw_energy
    operational_energy = profile.operational_energy
    energy = profile.energy
    baseline = profile.baseline_energy

    profile.speed_energy_intensity_saving = _saving(raw_energy, baseline)
    profile.operational_energy_intensity_saving = _saving(operational_energy, baseline)
    profile.technology_energy_intensity_saving = _saving(energy, operational_energy)
    profile.energy_intensity_saving = _saving(energy, baseline)


def _complete_vessel_savings(profile: VesselProfile) -> None:
    raw_energy = profile.raw_energy
    operational_energy = profile.operational_energy
    energy = profile.energy
    initial_energy = raw_energy[0]

    profile.speed_energy_saving = _saving(raw_energy, initial_energy)
    profile.operational_energy_saving = _saving(operational_energy, initial_energy)
    profile.technology_energy_saving = profile.technology_energy_intensity_saving
    profile.energy_saving = _saving(energy, initial_energy)


def _demand_savings(profile: _ConsumerProfile) -> dict[EnergyDemandID, FloatArray]:
    savings: dict[EnergyDemandID, FloatArray] = {}

    for demand_type in profile.energy_sea:
        energy = profile.energy_sea[demand_type]
        raw_energy = profile.raw_energy_sea[demand_type]

        if demand_type in PORT_ENERGY_DEMANDS:
            energy = energy + profile.energy_port[demand_type]
            raw_energy = raw_energy + profile.raw_energy_port[demand_type]

        savings[demand_type] = _saving(energy, raw_energy)

    return savings


def _complete_fuel_consumer(profile: _ConsumerProfile) -> None:
    _complete_consumption(profile)
    _complete_expenses(profile)
    _complete_emissions(profile)


def _complete_consumption(profile: _ConsumerProfile) -> None:
    context = profile.context
    shape = context.timeline.shape
    mass = profile.consumed_mass

    converter_energy: dict[tuple[FuelTypeID, str], FloatArray] = {}
    for vessel_fuel_type, converter_mass in profile.converter_mass.items():
        for fuel_name, energy in context.energy(converter_mass).items():
            converter_energy[(vessel_fuel_type, fuel_name)] = energy

    profile.consumed_energy = context.energy(mass)
    profile.fuel_type_energy = context.fuel_type_energy(mass)
    profile.converter_energy = converter_energy

    fuel_energy = sum_values(profile.consumed_energy, shape)
    profile.total_consumed_energy = fuel_energy + profile.shore_power_energy
    profile.pilot_fuel_share = _pilot_fuel_share(profile)


def _pilot_fuel_share(profile: _ConsumerProfile) -> dict[FuelTypeID, FloatArray]:
    # the share of a vessel fuel type's converter energy from fuels of other types
    # TODO: may not work when using multiple main fuel types
    context = profile.context
    shape = context.timeline.shape
    share: dict[FuelTypeID, FloatArray] = {}

    for vessel_fuel_type, mass in profile.converter_mass.items():
        energy = context.fuel_type_energy(mass)
        total = sum_values(energy, shape)
        share[vessel_fuel_type] = 1.0 - divide_nonzero(energy[vessel_fuel_type], total)

    return share


def _complete_expenses(profile: _ConsumerProfile) -> None:
    shape = profile.context.timeline.shape
    fuel_expenses = profile.fuel_expenses
    levy_expenses = profile.levy_expenses

    total_fuel = sum_values(fuel_expenses, shape) + profile.shore_power_expenses
    total_levy = sum_values(levy_expenses, shape)
    related = {key: fuel_expenses[key] + levy_expenses[key] for key in fuel_expenses}

    profile.fuel_related_expenses = related
    profile.total_fuel_expenses = total_fuel
    profile.total_fuel_related_expenses = total_fuel + total_levy
    profile.regulation_expenses = (
        profile.remedial_expenses
        + profile.flexibility_expenses
        - profile.surplus_revenue
    )


def _complete_emissions(profile: _ConsumerProfile) -> None:
    context = profile.context
    shape = context.timeline.shape
    consumed = profile.total_consumed_energy
    wtt = profile.wtt
    ttw = profile.ttw
    wtw = {key: wtt[key] + ttw[key] for key in wtt}

    profile.equivalent_wtt = context.equivalent(wtt)
    profile.equivalent_ttw = context.equivalent(ttw)
    profile.equivalent_wtw = context.equivalent(wtw)

    # shore power emissions are a WTW lump with no (fuel, emission) attribution, so
    # they enter the WTW total but not the per-key results
    shore_power = context.equivalent_by_emission(profile.shore_power_emission)
    total_shore_power = sum_values(shore_power, shape)
    total_wtt = sum_values(profile.equivalent_wtt, shape)
    total_ttw = sum_values(profile.equivalent_ttw, shape)
    total_wtw = sum_values(profile.equivalent_wtw, shape) + total_shore_power

    profile.total_equivalent_wtw = total_wtw
    profile.intensity_total_equivalent_wtt = _intensity(total_wtt, consumed)
    profile.intensity_total_equivalent_ttw = _intensity(total_ttw, consumed)
    profile.intensity_total_equivalent_wtw = _intensity(total_wtw, consumed)


def _complete_vessel_aggregate(profile: _AggregateProfile) -> None:
    numerator = profile.weighted_age_numerator
    denominator = profile.weighted_age_denominator
    age = {key: divide_nonzero(numerator[key], denominator[key]) for key in numerator}
    profile.weighted_average_age = age

    # after the fuel consumer results, which the expenses total
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
