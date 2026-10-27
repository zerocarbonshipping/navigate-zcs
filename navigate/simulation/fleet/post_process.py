# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The vessel, fleet and global results written after the run.

The time steps write energy, fuel, emissions and expenses to the vessel results.
Once the steps are done, each vessel's totals and savings are computed from them;
each fleet folds its vessels in by their multipliers, computes its own totals and
the achieved charter and freight rates; the global results, the fleets summed into
them, compute their totals last.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import PORT_ENERGY_DEMANDS
from navigate.simulation.economics import (
    build_operating_flows,
    calculate_net_present_value,
)
from navigate.simulation.fleet.power import get_total_power_capacity
from navigate.util import TOLERANCE, divide_nonzero, sum_values

if TYPE_CHECKING:
    from navigate.core.enum_ import EnergyDemandID, FuelTypeID
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.results import FleetResults, GlobalResults, VesselResults
    from navigate.util.types_ import FloatArray, FloatLike

type _ConsumerResults = VesselResults | FleetResults | GlobalResults
type _AggregateResults = FleetResults | GlobalResults

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
        Vessel, its results written for the whole run.
    """
    results = vessel.results

    _complete_energy(results)
    _complete_baseline_energy(results)
    _complete_savings(results)
    _complete_vessel_savings(results)
    _complete_fuel_consumer(results)


def complete_fleet_results(fleet: Fleet, timeline: FloatArray) -> None:
    """
    Fold the completed vessels into the fleet results and write the fleet's results.

    The vessels' written values enter weighted by their multipliers; the fleet's
    energies, baseline, savings, totals and technology uptake follow from them;
    last, each vessel's achieved charter and freight rates are computed from its
    completed expenses over the steps it was in the fleet, and the fleet's freight
    rate from those. Runs before the fleet is merged into the global results, which
    sums the baseline energy written here.

    Parameters
    ----------
    fleet
        Fleet, its vessels completed.
    timeline
        Simulation timeline, in days.
    """
    _fold_vessels(fleet)
    _derive_fleet(fleet.results)
    _calculate_fleet_rates(fleet, timeline)


def complete_global_fleet_results(results: GlobalResults) -> None:
    """
    Write the global fleet results computed from the written ones.

    Parameters
    ----------
    results
        Global results, the fleets summed into them.
    """
    _complete_energy(results)
    _complete_savings(results)
    _complete_fuel_consumer(results)
    _complete_vessel_aggregate(results)


def _fold_vessels(fleet: Fleet) -> None:
    """
    Fold the per-step vessel values into the fleet results by their multipliers.

    Parameters
    ----------
    fleet
        Fleet whose vessel values are folded into its results.
    """
    _transfer_in_fleet_flags(fleet)
    _transfer_fuel_consumer_results(fleet)
    _transfer_fuel_conversion_expenses(fleet)
    _transfer_power_totals(fleet)
    _transfer_fuel_converted_power(fleet)
    _aggregate_reference_speed(fleet)
    _aggregate_operating_speeds(fleet)
    _transfer_transport_work(fleet)


def _transfer_in_fleet_flags(fleet: Fleet) -> None:
    """
    Transfer whether each vessel type was present in the fleet to its results.

    Parameters
    ----------
    fleet
        Fleet whose vessel types' presence is transferred.
    """
    existing_vessels = fleet.results.existing_vessels

    for vessel in fleet.vessels:
        vessel.results.in_fleet[:] = existing_vessels[vessel.name] > 0.0


def _transfer_fuel_consumer_results(fleet: Fleet) -> None:
    """
    Add the multiplier-weighted vessel emissions, energy and fuel expenses to the fleet.

    Parameters
    ----------
    fleet
        Fleet receiving its vessels' emissions, energy and fuel expenses.
    """
    existing_vessels = fleet.results.existing_vessels

    for vessel in fleet.vessels:
        fleet.results.add_fuel_consumer_results(
            vessel.results, existing_vessels[vessel.name]
        )


def _transfer_fuel_conversion_expenses(fleet: Fleet) -> None:
    """
    Transfer the fleet's fuel conversion expenses to its results.

    Parameters
    ----------
    fleet
        Fleet whose fuel conversion expenses are transferred.
    """
    fleet.results.fuel_conversion_expenses[:] += fleet.fuel_conversion_expenses


def _transfer_power_totals(fleet: Fleet) -> None:
    """
    Transfer the installed, newbuild, and scrapped power per fuel type.

    Parameters
    ----------
    fleet
        Fleet whose power totals are transferred.
    """
    results = fleet.results
    existing_vessels = results.existing_vessels
    newbuilds = results.newbuilds
    scrap = results.scrap

    for vessel in fleet.vessels:
        fuel_type = vessel.primary_fuel_type
        power = get_total_power_capacity(vessel)

        results.installed_power[fuel_type][:] += power * existing_vessels[vessel.name]
        results.newbuild_power[fuel_type][:] += power * newbuilds[vessel.name]
        results.scrapped_power[fuel_type][:] += power * scrap[vessel.name]


def _transfer_fuel_converted_power(fleet: Fleet) -> None:
    """
    Transfer the power converted between fuel types by fuel conversions.

    Parameters
    ----------
    fleet
        Fleet whose fuel-converted power is transferred.
    """
    results = fleet.results
    vessel_map = {vessel.name: vessel for vessel in fleet.vessels}

    for (name_from, name_to), multipliers in results.fuel_conversions.items():
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
        results.fuel_converted_power[fuel_from, fuel_to][:] += power_from * converted


def _aggregate_reference_speed(fleet: Fleet) -> None:
    """
    Average the vessels' reference speeds, weighted by their multipliers.

    A vessel without a reference speed at a step adds nothing to the speed total but
    keeps its multiplier in the weight.

    Parameters
    ----------
    fleet
        Fleet whose vessels' reference speeds are averaged.
    """
    results = fleet.results
    multipliers = results.existing_vessels
    reference_total = np.zeros(results.reference_speed.size)
    weight = np.zeros(results.reference_speed.size)

    for vessel in fleet.vessels:
        multiplier = multipliers[vessel.name]
        reference = vessel.results.reference_speed

        reference_total += np.where(np.isnan(reference), 0.0, multiplier * reference)
        weight += multiplier

    results.reference_speed[:] = divide_nonzero(reference_total, weight, default=np.nan)


def _aggregate_operating_speeds(fleet: Fleet) -> None:
    """
    Average the vessels' operating speeds, weighted by their multipliers.

    A vessel is left out at a step where its minimum, maximum or actual speed is NaN.
    A NaN optimal, lowest or highest speed on a vessel left in poisons only its own
    average.

    Parameters
    ----------
    fleet
        Fleet whose vessels' operating speeds are averaged.
    """
    results = fleet.results
    multipliers = results.existing_vessels
    size = results.actual_speed.size

    minimum_total = np.zeros(size)
    maximum_total = np.zeros(size)
    actual_total = np.zeros(size)
    optimal_total = np.zeros(size)
    lowest_total = np.zeros(size)
    highest_total = np.zeros(size)
    weight = np.zeros(size)

    for vessel in fleet.vessels:
        multiplier = multipliers[vessel.name]
        vessel_results = vessel.results

        minimum = vessel_results.minimum_speed
        maximum = vessel_results.maximum_speed
        actual = vessel_results.actual_speed
        optimal = vessel_results.optimal_speed
        lowest = vessel_results.lowest_speed
        highest = vessel_results.highest_speed

        defined = ~(np.isnan(minimum) | np.isnan(maximum) | np.isnan(actual))

        minimum_total += np.where(defined, multiplier * minimum, 0.0)
        maximum_total += np.where(defined, multiplier * maximum, 0.0)
        actual_total += np.where(defined, multiplier * actual, 0.0)
        optimal_total += np.where(defined, multiplier * optimal, 0.0)
        lowest_total += np.where(defined, multiplier * lowest, 0.0)
        highest_total += np.where(defined, multiplier * highest, 0.0)
        weight += np.where(defined, multiplier, 0.0)

    results.minimum_speed[:] = divide_nonzero(minimum_total, weight, default=np.nan)
    results.maximum_speed[:] = divide_nonzero(maximum_total, weight, default=np.nan)
    results.actual_speed[:] = divide_nonzero(actual_total, weight, default=np.nan)
    results.optimal_speed[:] = divide_nonzero(optimal_total, weight, default=np.nan)
    results.lowest_speed[:] = divide_nonzero(lowest_total, weight, default=np.nan)
    results.highest_speed[:] = divide_nonzero(highest_total, weight, default=np.nan)


def _transfer_transport_work(fleet: Fleet) -> None:
    """
    Transfer the transport work the fleet performed.

    Parameters
    ----------
    fleet
        Fleet whose transport work is transferred.
    """
    results = fleet.results
    multipliers = results.existing_vessels
    cargo_miles = np.zeros(results.cargo_miles.size)

    for vessel in fleet.vessels:
        multiplier = multipliers[vessel.name]
        cargo_miles += multiplier * vessel.expectation.get_cargo_miles()

    results.cargo_miles[:] = cargo_miles


def _derive_fleet(results: FleetResults) -> None:
    """
    Write the fleet results that combine the written ones.

    Parameters
    ----------
    results
        Fleet results, its vessels folded in.
    """
    _complete_energy(results)
    _complete_baseline_energy(results)
    _complete_savings(results)
    _complete_fuel_consumer(results)
    _complete_vessel_aggregate(results)

    results.fleet_technology_uptake = _fleet_technology_uptake(results)


def _complete_baseline_energy(results: VesselResults | FleetResults) -> None:
    # the year-0 raw energy intensity times the transport work performed; a fleet
    # with no vessels at the first step has no year-0 intensity to measure against,
    # so its baseline stays 0, its intensity savings read 0, and it adds no baseline
    # to aggregate savings
    growth = divide_nonzero(results.cargo_miles, results.cargo_miles[0], default=1.0)
    initial_energy: float = results.raw_energy[0]
    results.baseline_energy = initial_energy * growth


def _complete_energy(results: _ConsumerResults) -> None:
    shape = results.context.timeline.shape

    raw_sea = sum_values(results.raw_energy_sea, shape)
    raw_port = sum_values(results.raw_energy_port, shape)
    operational_sea = sum_values(results.operational_energy_sea, shape)
    operational_port = sum_values(results.operational_energy_port, shape)
    energy_sea = sum_values(results.energy_sea, shape)
    energy_port = sum_values(results.energy_port, shape)

    results.raw_energy = raw_sea + raw_port
    results.operational_energy = operational_sea + operational_port
    results.energy = energy_sea + energy_port


def _saving(energy: FloatArray, reference: FloatLike) -> FloatArray:
    # no saving where there is no reference to save against
    return 1.0 - divide_nonzero(energy, reference, default=1.0)


def _complete_savings(results: _ConsumerResults) -> None:
    results.saving = _demand_savings(results)

    # the technology saving is against operational energy, as cargo-miles cancel
    # between the two
    raw_energy = results.raw_energy
    operational_energy = results.operational_energy
    energy = results.energy
    baseline = results.baseline_energy

    results.speed_energy_intensity_saving = _saving(raw_energy, baseline)
    results.operational_energy_intensity_saving = _saving(operational_energy, baseline)
    results.technology_energy_intensity_saving = _saving(energy, operational_energy)
    results.energy_intensity_saving = _saving(energy, baseline)


def _complete_vessel_savings(results: VesselResults) -> None:
    raw_energy = results.raw_energy
    operational_energy = results.operational_energy
    energy = results.energy
    initial_energy = raw_energy[0]

    results.speed_energy_saving = _saving(raw_energy, initial_energy)
    results.operational_energy_saving = _saving(operational_energy, initial_energy)
    results.technology_energy_saving = results.technology_energy_intensity_saving
    results.energy_saving = _saving(energy, initial_energy)


def _demand_savings(results: _ConsumerResults) -> dict[EnergyDemandID, FloatArray]:
    savings: dict[EnergyDemandID, FloatArray] = {}

    for demand_type in results.energy_sea:
        energy = results.energy_sea[demand_type]
        raw_energy = results.raw_energy_sea[demand_type]

        if demand_type in PORT_ENERGY_DEMANDS:
            energy = energy + results.energy_port[demand_type]
            raw_energy = raw_energy + results.raw_energy_port[demand_type]

        savings[demand_type] = _saving(energy, raw_energy)

    return savings


def _complete_fuel_consumer(results: _ConsumerResults) -> None:
    _complete_consumption(results)
    _complete_expenses(results)
    _complete_emissions(results)


def _complete_consumption(results: _ConsumerResults) -> None:
    context = results.context
    shape = context.timeline.shape
    mass = results.consumed_mass

    converter_energy: dict[tuple[FuelTypeID, str], FloatArray] = {}
    for vessel_fuel_type, converter_mass in results.converter_mass.items():
        for fuel_name, energy in context.calculate_energy(converter_mass).items():
            converter_energy[(vessel_fuel_type, fuel_name)] = energy

    results.consumed_energy = context.calculate_energy(mass)
    results.fuel_type_energy = context.calculate_fuel_type_energy(mass)
    results.converter_energy = converter_energy

    fuel_energy = sum_values(results.consumed_energy, shape)
    results.total_consumed_energy = fuel_energy + results.shore_power_energy
    results.pilot_fuel_share = _pilot_fuel_share(results)


def _pilot_fuel_share(results: _ConsumerResults) -> dict[FuelTypeID, FloatArray]:
    # the share of a vessel fuel type's converter energy from fuels of other types
    # TODO: may not work when using multiple main fuel types
    context = results.context
    shape = context.timeline.shape
    share: dict[FuelTypeID, FloatArray] = {}

    for vessel_fuel_type, mass in results.converter_mass.items():
        energy = context.calculate_fuel_type_energy(mass)
        total = sum_values(energy, shape)
        share[vessel_fuel_type] = 1.0 - divide_nonzero(energy[vessel_fuel_type], total)

    return share


def _complete_expenses(results: _ConsumerResults) -> None:
    shape = results.context.timeline.shape
    fuel_expenses = results.fuel_expenses
    levy_expenses = results.levy_expenses

    total_fuel = sum_values(fuel_expenses, shape) + results.shore_power_expenses
    total_levy = sum_values(levy_expenses, shape)
    related = {key: fuel_expenses[key] + levy_expenses[key] for key in fuel_expenses}

    results.fuel_related_expenses = related
    results.total_fuel_expenses = total_fuel
    results.total_fuel_related_expenses = total_fuel + total_levy
    results.regulation_expenses = (
        results.remedial_expenses
        + results.flexibility_expenses
        - results.surplus_revenue
    )


def _complete_emissions(results: _ConsumerResults) -> None:
    context = results.context
    shape = context.timeline.shape
    consumed = results.total_consumed_energy
    wtt = results.wtt
    ttw = results.ttw
    wtw = {key: wtt[key] + ttw[key] for key in wtt}

    results.equivalent_wtt = context.calculate_equivalent(wtt)
    results.equivalent_ttw = context.calculate_equivalent(ttw)
    results.equivalent_wtw = context.calculate_equivalent(wtw)

    # shore power emissions are a WTW lump with no (fuel, emission) attribution, so
    # they enter the WTW total but not the per-key results
    shore_power = context.calculate_emission_equivalent(results.shore_power_emission)
    total_shore_power = sum_values(shore_power, shape)
    total_wtt = sum_values(results.equivalent_wtt, shape)
    total_ttw = sum_values(results.equivalent_ttw, shape)
    total_wtw = sum_values(results.equivalent_wtw, shape) + total_shore_power

    results.total_equivalent_wtw = total_wtw
    results.intensity_total_equivalent_wtt = _intensity(total_wtt, consumed)
    results.intensity_total_equivalent_ttw = _intensity(total_ttw, consumed)
    results.intensity_total_equivalent_wtw = _intensity(total_wtw, consumed)


def _complete_vessel_aggregate(results: _AggregateResults) -> None:
    numerator = results.weighted_age_numerator
    denominator = results.weighted_age_denominator
    age = {key: divide_nonzero(numerator[key], denominator[key]) for key in numerator}
    results.weighted_average_age = age

    # after the fuel consumer results, which the expenses total
    results.vessel_related_expenses = (
        results.vessel_expenses
        + results.technology_expenses
        + results.fuel_conversion_expenses
    )
    results.expenses = (
        results.total_fuel_related_expenses
        + results.regulation_expenses
        + results.vessel_related_expenses
    )


def _fleet_technology_uptake(results: FleetResults) -> dict[str, FloatArray]:
    # the average of the vessels' uptake shares, weighted by vessel count; 0 where
    # the fleet is empty
    shares: dict[str, dict[str, FloatArray]] = {}
    for (vessel_name, technology_name), uptake in results.technology_uptake.items():
        shares.setdefault(technology_name, {})[vessel_name] = uptake

    fleet_uptake: dict[str, FloatArray] = {}
    for technology_name, vessel_shares in shares.items():
        values = np.array(list(vessel_shares.values()))
        weights = np.array(
            [results.existing_vessels[vessel_name] for vessel_name in vessel_shares]
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
        Fleet whose charter and freight rates are calculated.
    timeline
        Simulation timeline, in days.
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
        Simulation timeline, in days.
    """
    results = vessel.results
    cargo_miles = vessel.expectation.get_cargo_miles()
    expenses = _sum_operating_expenses(vessel)

    for idx, time in enumerate(timeline):
        lifetime = results.lifetime[idx]
        lead_time = results.lead_time[idx]
        year_starts, operating_flow = build_operating_flows(lead_time, lifetime, time)

        # the cost needs bunkering data over the lead time and the lifetime, which a
        # vessel that left the fleet lacks, as the bunkering algorithm no longer ran it
        if not np.all(results.in_fleet[idx : idx + operating_flow.size]):
            logger.debug(
                "%s: Unable to post-process fuel related costs at time %s days.",
                vessel,
                round(time, 0),
            )

            continue

        discount = vessel.cost_of_capital.get(time)
        asset_charter_npv = vessel.expectation.get_asset_charter_npv(idx)

        # costs and cargo resampled onto the operating years, zero during the lead time
        operating_cost = np.interp(year_starts, timeline, expenses) * operating_flow
        cargo = np.interp(year_starts, timeline, cargo_miles) * operating_flow

        operating_cost_npv = calculate_net_present_value(operating_cost, discount)
        cargo_npv = calculate_net_present_value(cargo, discount)
        years_npv = calculate_net_present_value(operating_flow, discount)
        cost_npv = asset_charter_npv + operating_cost_npv

        results.cargo_charter_rate[idx] = cost_npv / years_npv
        results.instantaneous_freight_rate[idx] = cost_npv / cargo_npv
        results.cost_is_calculated[idx] = True


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
    results = vessel.results
    levy = sum_values(results.levy_expenses, results.context.timeline.shape)

    return (
        results.total_fuel_expenses
        + levy
        + results.regulation_expenses
        + results.technology_cost
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
    results = fleet.results
    multipliers = results.existing_vessels
    cost_total = np.zeros(results.instantaneous_freight_rate.size)
    cargo_total = np.zeros(results.instantaneous_freight_rate.size)

    for vessel in fleet.vessels:
        multiplier = multipliers[vessel.name]
        charter_rate = vessel.results.cargo_charter_rate
        cargo_miles = vessel.expectation.get_cargo_miles()

        # a NaN multiplier stays active so it surfaces in the rate instead of
        # being dropped silently
        active = ~(multiplier <= 0.0) & vessel.results.cost_is_calculated

        cost_total += np.where(active, multiplier * charter_rate, 0.0)
        cargo_total += np.where(active, multiplier * cargo_miles, 0.0)

    results.instantaneous_freight_rate[:] = divide_nonzero(
        cost_total, cargo_total, default=np.nan
    )
