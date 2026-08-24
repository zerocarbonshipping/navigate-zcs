# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import logging

import numpy as np

from navigate.core.unit import YEAR_TO_DAYS
from navigate.economics.flows import build_operating_age_flow, get_flow_size
from navigate.economics.metric import calculate_net_present_value

logger = logging.getLogger(__name__)


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

        for vessel in fleet.get_vessels():

            profile = vessel.profile

            for idx, time in enumerate(timeline):

                discount = vessel.cost_of_capital.get(time)

                # extract the charter rate of the
                # asset excluding fuel expenses
                asset_charter_npv = vessel.expectation.get_asset_charter_npv(idx)

                # reconstruct the achieved operating cost-flow (fuel, levy, regulation,
                # technology) on the operating-year grid (zero during construction lead
                # time); None when the vessel lacks bunkering data over the horizon
                result = _calculate_total_vessel_operating_expenses(vessel, idx, timeline)
                if result is None:
                    continue

                operating_cost_flow, year_flow, overlap = result

                # calculate the NPV of operating expenses and the total vessel NPV
                operating_npv = calculate_net_present_value(operating_cost_flow, discount)
                cost_npv = asset_charter_npv + operating_npv

                # levelize the cost over the operating years (lead time excluded),
                # using the same grid as the fuel flow
                age_npv = calculate_net_present_value(overlap, discount)

                # NPV of cargo delivery over the same operating-year grid as the
                # cost (zero during lead time), not over the full simulation timeline
                cargo = np.interp(year_flow, timeline, vessel.expectation.get_cargo_miles()) * overlap
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

        cost_weighted = 0.
        cargo_weighted = 0.

        for vessel in fleet.get_vessels():

            multiplier = fleet.profile.get_existing_vessels(vessel.get_name(), idx)
            if multiplier <= 0. or not vessel.profile.cost_is_calculated(idx):
                continue

            cost_weighted += multiplier * vessel.profile.get_cargo_charter_rate(idx)
            cargo_weighted += multiplier * vessel.expectation.get_cargo_miles(idx)

        if cargo_weighted > 0.:
            fleet.profile.set_instantaneous_freight_rate(idx, cost_weighted / cargo_weighted)


def _operating_flows(idx, lead_time, lifetime, timeline):
    """
    Build the lead-aware operating-year grid and overlap fractions for a vessel evaluated at a step.

    The overlap is zero during the construction lead time and (prorated) one during operational years;
    the year grid gives the absolute calendar time (days) of each bin, anchored at the evaluation step.
    Both span `lead_time + lifetime` years so reconstructed cost, cargo, and age flows share one basis.

    Parameters
    ----------
    idx : int
        Time-step index at which the vessel is evaluated.
    lead_time : float
        Construction lead time (years).
    lifetime : float
        Operational lifetime (years).
    timeline : np.ndarray
        Full timeline of the simulation (days).

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        Absolute year grid (days) and per-year operating fraction.
    """

    overlap = build_operating_age_flow(lead_time, lifetime)
    year_flow = timeline[idx] + np.arange(overlap.size) * YEAR_TO_DAYS

    return year_flow, overlap


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
    idx_to = min(timeline.size, idx + get_flow_size(lead_time=lead_time, lifetime=lifetime))

    if not np.all(profile.is_in_fleet()[idx:idx_to]):

        logger.debug("{}: Unable to post-process fuel related costs at time {} days."
                     .format(vessel, round(timeline[idx], 0)))

        return None

    # operating-year grid: zero during construction lead time, operational
    # thereafter, so costs are only incurred while the vessel operates
    year_flow, overlap = _operating_flows(idx, lead_time, lifetime, timeline)

    fuel = np.interp(year_flow, timeline, profile.get_total_fuel_expenses()) * overlap
    levy = np.interp(year_flow, timeline, profile.get_total_levy_expenses()) * overlap
    regulation = np.interp(year_flow, timeline, profile.get_regulation_expenses()) * overlap
    technology = np.interp(year_flow, timeline, profile.get_technology_cost()) * overlap

    profile.set_cost_is_calculated(idx, True)

    return fuel + levy + regulation + technology, year_flow, overlap
