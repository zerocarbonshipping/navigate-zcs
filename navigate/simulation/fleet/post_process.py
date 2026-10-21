# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The results of the vessel, fleet and global profiles, written after the run.

The time steps write energy, fuel, emissions and expenses to the vessel profiles.
Once the steps are done, each vessel's totals and savings are computed from them;
each fleet folds its vessels in by their multipliers, computes its own totals and
the achieved charter and freight rates; the global profile, the fleets summed into
it, computes its totals last.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import PORT_ENERGY_DEMANDS
from navigate.simulation.economics.flows import build_operating_flows
from navigate.simulation.economics.metric import calculate_net_present_value
from navigate.simulation.fleet.power import get_total_power_capacity
from navigate.util import TOLERANCE, divide_nonzero, sum_values

if TYPE_CHECKING:
    from navigate.core.enum_ import EnergyDemandID, FuelTypeID
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.profiles import FleetProfile, GlobalProfile, VesselProfile
    from navigate.util.types_ import FloatArray, FloatLike

type _ConsumerProfile = VesselProfile | FleetProfile | GlobalProfile
type _AggregateProfile = FleetProfile | GlobalProfile

logger = logging.getLogger(__name__)


def complete_vessel_results(vessel: Vessel) -> None:
    """
    Write the results of a vessel that combine its written ones.

    Runs over every vessel before any fleet is completed: a fleet's achieved rates
    read its vessels' completed expenses, and a vessel kept without a fleet is
    completed all the same.

    Parameters
    ----------
    vessel
        Vessel, its profile written for the whole run.
    """
    profile = vessel.profile

    _complete_energy(profile)
    _complete_baseline_energy(profile)
    _complete_savings(profile)
    _complete_vessel_savings(profile)
    _complete_fuel_consumer(profile)


def complete_fleet_results(fleet: Fleet, timeline: FloatArray) -> None:
    """
    Fold the completed vessels into the fleet profile and write the fleet's results.

    The vessels' written values enter weighted by their multipliers; the fleet's
    energies, baseline, savings, totals and technology uptake follow from them;
    last, each vessel's achieved charter and freight rates are computed from its
    completed expenses over the steps it was in the fleet, and the fleet's freight
    rate from those. Runs before the fleet is merged into the global profile, which
    sums the baseline energy written here.

    Parameters
    ----------
    fleet
        Fleet, its vessels completed.
    timeline
        Simulation timeline, days.
    """
    _fold_vessels(fleet)
    _derive_fleet(fleet.profile)
    _calculate_fleet_rates(fleet, timeline)


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


def _fold_vessels(fleet: Fleet) -> None:
    """
    Fold the per-step vessel values into the fleet profile by their multipliers.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    _transfer_in_fleet_flags(fleet)
    _transfer_fuel_consumer_profiles(fleet)
    _transfer_fuel_conversion_expenses(fleet)
    _transfer_power_totals(fleet)
    _transfer_fuel_converted_power(fleet)
    _aggregate_reference_speed(fleet)
    _aggregate_operating_speeds(fleet)
    _transfer_transport_work(fleet)


def _transfer_in_fleet_flags(fleet: Fleet) -> None:
    """
    Transfer whether each vessel type was present in the fleet to its profile.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    existing_vessels = fleet.profile.existing_vessels

    for vessel in fleet.vessels:
        vessel.profile.in_fleet[:] = existing_vessels[vessel.name] > 0.0


def _transfer_fuel_consumer_profiles(fleet: Fleet) -> None:
    """
    Add the multiplier-weighted vessel emissions, energy and fuel expenses to the fleet.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    existing_vessels = fleet.profile.existing_vessels

    for vessel in fleet.vessels:
        fleet.profile.add_fuel_consumer_profile(
            vessel.profile, existing_vessels[vessel.name]
        )


def _transfer_fuel_conversion_expenses(fleet: Fleet) -> None:
    """
    Transfer the fleet's fuel conversion expenses to its profile.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    fleet.profile.fuel_conversion_expenses[:] += fleet.fuel_conversion_expenses


def _transfer_power_totals(fleet: Fleet) -> None:
    """
    Transfer the installed, newbuild, and scrapped power per fuel type.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    profile = fleet.profile
    existing_vessels = profile.existing_vessels
    newbuilds = profile.newbuilds
    scrap = profile.scrap

    for vessel in fleet.vessels:
        fuel_type = vessel.primary_fuel_type
        power = get_total_power_capacity(vessel)

        profile.installed_power[fuel_type][:] += power * existing_vessels[vessel.name]
        profile.newbuild_power[fuel_type][:] += power * newbuilds[vessel.name]
        profile.scrapped_power[fuel_type][:] += power * scrap[vessel.name]


def _transfer_fuel_converted_power(fleet: Fleet) -> None:
    """
    Transfer the power converted between fuel types by fuel conversions.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    profile = fleet.profile
    vessel_map = {vessel.name: vessel for vessel in fleet.vessels}

    for (name_from, name_to), multipliers in profile.fuel_conversions.items():
        # conversions below tolerance are numerical residue, not decisions
        converted = np.where(multipliers < TOLERANCE, 0.0, multipliers)

        if not np.any(converted):
            continue

        vessel_from = vessel_map[name_from]
        vessel_to = vessel_map[name_to]

        power_from = get_total_power_capacity(vessel_from)
        power_to = get_total_power_capacity(vessel_to)

        if abs(power_to - power_from) > TOLERANCE:
            logger.warning(
                "%s: Fuel conversion occurred with different installed power %s (%s) "
                "to %s (%s).",
                fleet,
                vessel_from,
                round(power_from, 1),
                vessel_to,
                round(power_to, 1),
            )

        fuel_from = vessel_from.primary_fuel_type
        fuel_to = vessel_to.primary_fuel_type
        profile.fuel_converted_power[fuel_from, fuel_to][:] += power_from * converted


def _aggregate_reference_speed(fleet: Fleet) -> None:
    """
    Average the vessels' reference speeds, weighted by their multipliers.

    A vessel without a reference speed at a step adds nothing to the speed total but
    keeps its multiplier in the weight.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    profile = fleet.profile
    multipliers = profile.existing_vessels
    reference_total = np.zeros(profile.reference_speed.size)
    weight = np.zeros(profile.reference_speed.size)

    for vessel in fleet.vessels:
        multiplier = multipliers[vessel.name]
        reference = vessel.profile.reference_speed

        reference_total += np.where(np.isnan(reference), 0.0, multiplier * reference)
        weight += multiplier

    profile.reference_speed[:] = divide_nonzero(reference_total, weight, default=np.nan)


def _aggregate_operating_speeds(fleet: Fleet) -> None:
    """
    Average the vessels' operating speeds, weighted by their multipliers.

    A vessel is left out at a step where its minimum, maximum or actual speed is NaN.
    A NaN optimal, lowest or highest speed on a vessel left in poisons only its own
    average.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    profile = fleet.profile
    multipliers = profile.existing_vessels
    size = profile.actual_speed.size

    minimum_total = np.zeros(size)
    maximum_total = np.zeros(size)
    actual_total = np.zeros(size)
    optimal_total = np.zeros(size)
    lowest_total = np.zeros(size)
    highest_total = np.zeros(size)
    weight = np.zeros(size)

    for vessel in fleet.vessels:
        multiplier = multipliers[vessel.name]
        vessel_profile = vessel.profile

        minimum = vessel_profile.minimum_speed
        maximum = vessel_profile.maximum_speed
        actual = vessel_profile.actual_speed
        optimal = vessel_profile.optimal_speed
        lowest = vessel_profile.lowest_speed
        highest = vessel_profile.highest_speed

        defined = ~(np.isnan(minimum) | np.isnan(maximum) | np.isnan(actual))

        minimum_total += np.where(defined, multiplier * minimum, 0.0)
        maximum_total += np.where(defined, multiplier * maximum, 0.0)
        actual_total += np.where(defined, multiplier * actual, 0.0)
        optimal_total += np.where(defined, multiplier * optimal, 0.0)
        lowest_total += np.where(defined, multiplier * lowest, 0.0)
        highest_total += np.where(defined, multiplier * highest, 0.0)
        weight += np.where(defined, multiplier, 0.0)

    profile.minimum_speed[:] = divide_nonzero(minimum_total, weight, default=np.nan)
    profile.maximum_speed[:] = divide_nonzero(maximum_total, weight, default=np.nan)
    profile.actual_speed[:] = divide_nonzero(actual_total, weight, default=np.nan)
    profile.optimal_speed[:] = divide_nonzero(optimal_total, weight, default=np.nan)
    profile.lowest_speed[:] = divide_nonzero(lowest_total, weight, default=np.nan)
    profile.highest_speed[:] = divide_nonzero(highest_total, weight, default=np.nan)


def _transfer_transport_work(fleet: Fleet) -> None:
    """
    Transfer the transport work the fleet performed.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    profile = fleet.profile
    multipliers = profile.existing_vessels
    cargo_miles = np.zeros(profile.cargo_miles.size)

    for vessel in fleet.vessels:
        multiplier = multipliers[vessel.name]
        cargo_miles += multiplier * vessel.expectation.get_cargo_miles()

    profile.cargo_miles[:] = cargo_miles


def _derive_fleet(profile: FleetProfile) -> None:
    """
    Write the results of a fleet profile that combine its written ones.

    Parameters
    ----------
    profile
        Fleet profile, its vessels folded into it.
    """
    _complete_energy(profile)
    _complete_baseline_energy(profile)
    _complete_savings(profile)
    _complete_fuel_consumer(profile)
    _complete_vessel_aggregate(profile)

    profile.fleet_technology_uptake = _fleet_technology_uptake(profile)


def _complete_baseline_energy(profile: VesselProfile | FleetProfile) -> None:
    # the year-0 raw energy intensity times the transport work performed; a fleet
    # with no vessels at the first step has no year-0 intensity to measure against,
    # so its baseline stays 0, its intensity savings read 0, and it adds no baseline
    # to aggregate savings
    growth = divide_nonzero(profile.cargo_miles, profile.cargo_miles[0], default=1.0)
    initial_energy: float = profile.raw_energy[0]
    profile.baseline_energy = initial_energy * growth


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


def _calculate_fleet_rates(fleet: Fleet, timeline: FloatArray) -> None:
    """
    Calculate the achieved charter and freight rates of the vessels, then the fleet's.

    Parameters
    ----------
    fleet
        Fleet instance.
    timeline
        Simulation timeline, days.
    """
    for vessel in fleet.vessels:
        _calculate_achieved_rates(vessel, timeline)

    _aggregate_fleet_freight_rate(fleet)


def _calculate_achieved_rates(vessel: Vessel, timeline: FloatArray) -> None:
    """
    Calculate the vessel's achieved charter and freight rates at each time-step.

    Parameters
    ----------
    vessel
        Vessel whose rates are calculated.
    timeline
        Simulation timeline, days.
    """
    profile = vessel.profile
    cargo_miles = vessel.expectation.get_cargo_miles()
    operating_expenses = _sum_operating_expenses(vessel)

    for idx, time in enumerate(timeline):
        lifetime = profile.lifetime[idx]
        lead_time = profile.lead_time[idx]
        year_flow, overlap = build_operating_flows(time, lead_time, lifetime)

        # the cost needs bunkering data over the lead time and the lifetime, which a
        # vessel that left the fleet lacks, as the bunkering algorithm no longer ran it
        if not np.all(profile.in_fleet[idx : idx + overlap.size]):
            logger.debug(
                "%s: Unable to post-process fuel related costs at time %s days.",
                vessel,
                round(time, 0),
            )

            continue

        discount = vessel.cost_of_capital.get(time)
        asset_charter_npv = vessel.expectation.get_asset_charter_npv(idx)

        # costs and cargo resampled onto the operating years, zero during the lead time
        operating_cost = np.interp(year_flow, timeline, operating_expenses) * overlap
        cargo = np.interp(year_flow, timeline, cargo_miles) * overlap

        operating_cost_npv = calculate_net_present_value(operating_cost, discount)
        cargo_npv = calculate_net_present_value(cargo, discount)
        years_npv = calculate_net_present_value(overlap, discount)
        cost_npv = asset_charter_npv + operating_cost_npv

        profile.cargo_charter_rate[idx] = cost_npv / years_npv
        profile.instantaneous_freight_rate[idx] = cost_npv / cargo_npv
        profile.cost_is_calculated[idx] = True


def _sum_operating_expenses(vessel: Vessel) -> FloatArray:
    """
    Sum the vessel's achieved fuel, levy, regulation and technology expenses.

    Parameters
    ----------
    vessel
        Vessel whose operating expenses are summed.

    Returns
    -------
    FloatArray
        Operating expenses at each time-step, in USD/year.
    """
    profile = vessel.profile
    levy = sum_values(profile.levy_expenses, profile.context.timeline.shape)

    return (
        profile.total_fuel_expenses
        + levy
        + profile.regulation_expenses
        + profile.technology_cost
    )


def _aggregate_fleet_freight_rate(fleet: Fleet) -> None:
    """
    Aggregate a fleet-level instantaneous freight rate, in USD/cargo-mile.

    The fleet rate is the multiplier-weighted total achieved charter cost divided by the
    multiplier-weighted cargo-miles delivered, making it the cargo-mile-consistent
    counterpart of the per-vessel instantaneous freight rate. A vessel contributes at
    every time-step where its cost is calculated unless its multiplier is zero or
    negative; the rate is NaN wherever the weighted cargo-miles are not positive.

    Parameters
    ----------
    fleet
        Fleet whose vessels are aggregated.
    """
    profile = fleet.profile
    multipliers = profile.existing_vessels
    cost_total = np.zeros(profile.instantaneous_freight_rate.size)
    cargo_total = np.zeros(profile.instantaneous_freight_rate.size)

    for vessel in fleet.vessels:
        multiplier = multipliers[vessel.name]
        charter_rate = vessel.profile.cargo_charter_rate
        cargo_miles = vessel.expectation.get_cargo_miles()

        # a NaN multiplier stays active so it surfaces in the rate instead of
        # being dropped silently
        active = ~(multiplier <= 0.0) & vessel.profile.cost_is_calculated

        cost_total += np.where(active, multiplier * charter_rate, 0.0)
        cargo_total += np.where(active, multiplier * cargo_miles, 0.0)

    profile.instantaneous_freight_rate[:] = divide_nonzero(
        cost_total, cargo_total, default=np.nan
    )
