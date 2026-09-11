# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.economics.flows import build_operating_flows, get_flow_size
from navigate.economics.metric import calculate_net_present_value
from navigate.fleet.utils import get_total_power_capacity
from navigate.util import TOLERANCE, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet

logger = logging.getLogger(__name__)


def post_process_fleet_profile(fleets: dict[str, Fleet]) -> None:
    """
    Fold the recorded per-step multipliers into the output-only fleet and
    vessel profile fields as whole-timeline array operations. Must run before
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
        aggregate_speed_profile(fleet)

        # after the consumer transfer, which the year-0 raw energy comes from
        transfer_transport_work(fleet)


def _transfer_in_fleet_flags(fleet: Fleet) -> None:
    """
    Transfer whether each vessel type was present in the fleet to its profile.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    for vessel in fleet.assets:
        in_fleet = fleet.profile.get_existing_vessels(vessel.name) > 0.0
        vessel.profile.set_in_fleet(np.s_[:], in_fleet)


def _transfer_fuel_consumer_profiles(fleet: Fleet) -> None:
    """
    Accumulate the multiplier-weighted vessel consumer profiles (emissions,
    energy, fuel expenses) onto the fleet profile.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    for vessel in fleet.assets:
        multipliers = fleet.profile.get_existing_vessels(vessel.name)
        fleet.profile.add_fuel_consumer_profile(vessel.profile, multipliers)


def _transfer_fuel_conversion_expenses(fleet: Fleet) -> None:
    """
    Transfer the running technology retrofit and fuel conversion expenses.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    fleet.profile.add_fuel_conversion_expenses(fleet.fuel_conversion_expenses)


def _transfer_power_totals(fleet: Fleet) -> None:
    """
    Transfer the installed, newbuild, and scrapped power per fuel type.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    for vessel in fleet.assets:
        vessel_name = vessel.name
        power = get_total_power_capacity(vessel)

        fleet.profile.add_installed_power(
            vessel.fuel_type, power * fleet.profile.get_existing_vessels(vessel_name)
        )
        fleet.profile.add_newbuild_power(
            vessel.fuel_type, power * fleet.profile.get_newbuilds(vessel_name)
        )
        fleet.profile.add_scrapped_power(
            vessel.fuel_type, power * fleet.profile.get_scrap(vessel_name)
        )


def _transfer_fuel_converted_power(fleet: Fleet) -> None:
    """
    Transfer the power converted between fuel types by fuel conversions.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    vessel_map = {vessel.name: vessel for vessel in fleet.assets}
    fuel_conversions = fleet.profile.get_fuel_conversions()

    for (v_from, v_to), multipliers in fuel_conversions.items():
        # conversions below tolerance are numerical residue, not decisions;
        # treat them as zero so they contribute no converted power
        converted = np.where(multipliers < TOLERANCE, 0.0, multipliers)

        if not np.any(converted):
            continue

        vessel_from = vessel_map[v_from]
        vessel_to = vessel_map[v_to]

        power_from = get_total_power_capacity(vessel_from)
        power_to = get_total_power_capacity(vessel_to)

        if abs(power_to - power_from) > TOLERANCE:
            logger.warning(
                f"{fleet}: Fuel conversion occurred with different installed power {vessel_from} ({round(power_from, 1)}) to {vessel_to} ({round(power_to, 1)})."
            )

        fleet.profile.add_fuel_converted_power(
            vessel_from.fuel_type, vessel_to.fuel_type, power_from * converted
        )


def aggregate_speed_profile(fleet: Fleet) -> None:
    """
    Aggregate vessel-level speed profiles into fleet-level weighted averages.

    The reference speed averages every vessel with a defined reference over
    the full multiplier total; the remaining speeds average only vessels
    whose minimum, maximum, and actual speeds are all defined at the step. A
    NaN optimal, lowest, or highest speed on such a vessel poisons only its
    own average.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    profile = fleet.profile
    size = profile.get_reference_speed().size

    reference_speed = np.zeros(size)
    minimum_speed = np.zeros(size)
    maximum_speed = np.zeros(size)
    actual_speed = np.zeros(size)
    optimal_speed = np.zeros(size)
    lowest_speed = np.zeros(size)
    highest_speed = np.zeros(size)
    reference_multiplier = np.zeros(size)
    other_multiplier = np.zeros(size)

    for vessel in fleet.assets:
        vessel_profile = vessel.profile
        multiplier = profile.get_existing_vessels(vessel.name)

        reference = vessel_profile.get_reference_speed()
        minimum = vessel_profile.get_minimum_speed()
        maximum = vessel_profile.get_maximum_speed()
        actual = vessel_profile.get_actual_speed()
        optimal = vessel_profile.get_optimal_speed()
        lowest = vessel_profile.get_lowest_speed()
        highest = vessel_profile.get_highest_speed()

        reference_speed += np.where(np.isnan(reference), 0.0, multiplier * reference)
        reference_multiplier += multiplier

        defined = ~(np.isnan(minimum) | np.isnan(maximum) | np.isnan(actual))

        minimum_speed += np.where(defined, multiplier * minimum, 0.0)
        maximum_speed += np.where(defined, multiplier * maximum, 0.0)
        actual_speed += np.where(defined, multiplier * actual, 0.0)
        optimal_speed += np.where(defined, multiplier * optimal, 0.0)
        lowest_speed += np.where(defined, multiplier * lowest, 0.0)
        highest_speed += np.where(defined, multiplier * highest, 0.0)
        other_multiplier += np.where(defined, multiplier, 0.0)

    profile.set_reference_speed(
        np.s_[:], divide_nonzero(reference_speed, reference_multiplier, default=np.nan)
    )
    profile.set_minimum_speed(
        np.s_[:], divide_nonzero(minimum_speed, other_multiplier, default=np.nan)
    )
    profile.set_maximum_speed(
        np.s_[:], divide_nonzero(maximum_speed, other_multiplier, default=np.nan)
    )
    profile.set_actual_speed(
        np.s_[:], divide_nonzero(actual_speed, other_multiplier, default=np.nan)
    )
    profile.set_optimal_speed(
        np.s_[:], divide_nonzero(optimal_speed, other_multiplier, default=np.nan)
    )
    profile.set_lowest_speed(
        np.s_[:], divide_nonzero(lowest_speed, other_multiplier, default=np.nan)
    )
    profile.set_highest_speed(
        np.s_[:], divide_nonzero(highest_speed, other_multiplier, default=np.nan)
    )


def transfer_transport_work(fleet: Fleet) -> None:
    """
    Transfer the transport work performed and the counterfactual baseline
    energy: what the year-0 raw energy intensity would require to perform
    the transport work actually performed at each time step. A fleet with
    no vessels at the first time step has no year-0 intensity to measure
    against: its baseline stays 0 for the whole simulation, its intensity
    savings read 0, and it contributes no baseline to aggregate savings.

    Parameters
    ----------
    fleet
        Fleet instance.
    """
    multipliers = np.ascontiguousarray(
        np.array(
            [fleet.profile.get_existing_vessels(vessel.name) for vessel in fleet.assets]
        ).T
    )
    vessel_cargo_miles = np.ascontiguousarray(
        np.array([vessel.expectation.get_cargo_miles() for vessel in fleet.assets]).T
    )

    # one dot product per step over the vessel axis: a single matrix product
    # may reduce the vessel axis in a different order and drift in the last
    # bit, breaking bit-for-bit comparison of runs against per-step transfers
    cargo_miles = np.array(
        [
            np.dot(multipliers[idx], vessel_cargo_miles[idx])
            for idx in range(multipliers.shape[0])
        ]
    )

    fleet.profile.set_cargo_miles(np.s_[:], cargo_miles)

    growth = divide_nonzero(cargo_miles, cargo_miles[0], default=1.0)
    baseline = fleet.profile.get_raw_energy(idx=0) * growth
    fleet.profile.set_baseline_energy(np.s_[:], baseline)


def post_process_investment_metric(fleets, timeline):
    """
    As a post-processing of the simulation, the investment metric is calculated using the post-processed fuel costs.

    Parameters
    ----------
    fleets : dict[str, Fleet]
        All fleets in the simulation.
    timeline : np.ndarray
        Full timeline of the simulation.
    """
    for fleet in fleets.values():
        for vessel in fleet.vessels:
            profile = vessel.profile

            for idx, time in enumerate(timeline):
                discount = vessel.cost_of_capital.get(time)

                # extract the charter rate of the
                # asset excluding fuel expenses
                asset_charter_npv = vessel.expectation.get_asset_charter_npv(idx)

                # reconstruct the achieved operating cost-flow (fuel, levy, regulation,
                # technology) on the operating-year grid (zero during construction lead
                # time); None when the vessel lacks bunkering data over the horizon
                result = _calculate_total_vessel_operating_expenses(
                    vessel, idx, timeline
                )
                if result is None:
                    continue

                operating_cost_flow, year_flow, overlap = result

                # calculate the NPV of operating expenses and the total vessel NPV
                operating_npv = calculate_net_present_value(
                    operating_cost_flow, discount
                )
                cost_npv = asset_charter_npv + operating_npv

                # levelize the cost over the operating years (lead time excluded),
                # using the same grid as the fuel flow
                age_npv = calculate_net_present_value(overlap, discount)

                # NPV of cargo delivery over the same operating-year grid as the
                # cost (zero during lead time), not over the full simulation timeline
                cargo = (
                    np.interp(year_flow, timeline, vessel.expectation.get_cargo_miles())
                    * overlap
                )
                cargo_npv = calculate_net_present_value(cargo, discount)

                # calculate the achieved charter and freight rate
                cargo_charter_rate = cost_npv / age_npv
                freight_rate = cost_npv / cargo_npv

                profile.set_cargo_charter_rate(idx, cargo_charter_rate)
                profile.set_instantaneous_freight_rate(idx, freight_rate)

        # aggregate a fleet-level instantaneous freight rate from the
        # per-vessel achieved charter rates and cargo-miles delivered
        _aggregate_fleet_freight_rate(fleet, timeline)


def _aggregate_fleet_freight_rate(fleet, timeline):
    """
    Aggregate a fleet-level instantaneous freight rate (USD/cargo-mile).

    The fleet rate is the multiplier-weighted total achieved charter cost divided by the
    multiplier-weighted cargo-miles delivered, making it the cargo-mile-consistent counterpart of the
    per-vessel instantaneous freight rate. Only vessels with a positive multiplier and a calculated
    cost at the time-step contribute.

    Parameters
    ----------
    fleet : Fleet
        Fleet whose vessels are aggregated.
    timeline : np.ndarray
        Full timeline of the simulation.
    """
    for idx in range(timeline.size):
        cost_weighted = 0.0
        cargo_weighted = 0.0

        for vessel in fleet.vessels:
            multiplier = fleet.profile.get_existing_vessels(vessel.name, idx)
            if multiplier <= 0.0 or not vessel.profile.cost_is_calculated(idx):
                continue

            cost_weighted += multiplier * vessel.profile.get_cargo_charter_rate(idx)
            cargo_weighted += multiplier * vessel.expectation.get_cargo_miles(idx)

        if cargo_weighted > 0.0:
            fleet.profile.set_instantaneous_freight_rate(
                idx, cost_weighted / cargo_weighted
            )


def _calculate_total_vessel_operating_expenses(vessel, idx, timeline):
    """
    Assigns the fuel, levy, regulation, and technology expenses for a vessel in the fleet at a given time
    of the simulation.

    Parameters
    ----------
    vessel : Vessel
        Class Vessel.
    idx : int
        Time-step index that cost is starting at.
    timeline : np.ndarray
        Full timeline of the simulation.

    Returns
    -------
    tuple[np.ndarray, np.ndarray, np.ndarray] | None
        The total operating cost flow, the operating-year grid (days), and the per-year operating
        fraction (shared with the caller); None when the vessel lacks bunkering data over the horizon.
    """
    profile = vessel.profile

    # the cost requires bunkering knowledge over the construction lead time
    # plus the operational lifetime. If a vessel has become inactive it will
    # not have been part of the bunkering algorithm and so lacks the data.
    lifetime = profile.get_lifetime(idx)
    lead_time = profile.get_lead_time(idx)
    idx_to = min(
        timeline.size, idx + get_flow_size(lead_time=lead_time, lifetime=lifetime)
    )

    if not np.all(profile.is_in_fleet()[idx:idx_to]):
        logger.debug(
            f"{vessel}: Unable to post-process fuel related costs at time {round(timeline[idx], 0)} days."
        )

        return None

    # operating-year grid: zero during construction lead time, operational
    # thereafter, so costs are only incurred while the vessel operates
    year_flow, overlap = build_operating_flows(timeline[idx], lead_time, lifetime)

    fuel = np.interp(year_flow, timeline, profile.get_total_fuel_expenses()) * overlap
    levy = np.interp(year_flow, timeline, profile.get_total_levy_expenses()) * overlap
    regulation = (
        np.interp(year_flow, timeline, profile.get_regulation_expenses()) * overlap
    )
    technology = np.interp(year_flow, timeline, profile.get_technology_cost()) * overlap

    profile.set_cost_is_calculated(idx, True)

    return fuel + levy + regulation + technology, year_flow, overlap
