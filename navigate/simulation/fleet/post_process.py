# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""End-of-run fleet profiles and the achieved investment metrics of each vessel."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.economics.flows import build_operating_flows
from navigate.simulation.economics.metric import calculate_net_present_value
from navigate.simulation.fleet.power import get_total_power_capacity
from navigate.util import TOLERANCE, divide_nonzero, sum_values

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)


def post_process_fleet_profile(fleets: dict[str, Fleet]) -> None:
    """
    Fold per-step multipliers into the output-only fleet and vessel profiles.

    Runs as whole-timeline array operations. Must run before
    post_process_investment_metric, which reads the in-fleet flags, and
    before the fleet profiles are merged into the global profile.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    """
    for fleet in fleets.values():
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


def post_process_investment_metric(
    fleets: dict[str, Fleet], timeline: FloatArray
) -> None:
    """
    Calculate each vessel's achieved charter and freight rates from the realized costs.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    timeline
        Simulation timeline, days.
    """
    for fleet in fleets.values():
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
    operating_expenses = _sum_operating_expenses(vessel, timeline)

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


def _sum_operating_expenses(vessel: Vessel, timeline: FloatArray) -> FloatArray:
    """
    Sum the vessel's achieved fuel, levy, regulation and technology expenses.

    Parameters
    ----------
    vessel
        Vessel whose operating expenses are summed.
    timeline
        Simulation timeline, days.

    Returns
    -------
    FloatArray
        Operating expenses at each time-step, in USD/year.
    """
    profile = vessel.profile
    levy = sum_values(profile.levy_expenses, timeline.shape)

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
