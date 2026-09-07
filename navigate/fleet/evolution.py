# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.fleet.planning import add_newbuilds, calculate_modelled_newbuilds, calculate_orderbook_newbuilds
from navigate.fleet.utils import extract_cargo_miles
from navigate.util import ROUND_OFF, TOLERANCE, YEAR, calculate_inertia, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet

logger = logging.getLogger(__name__)


def perform_primary_scrapping(fleet: Fleet, idx: int, time_step: float):
    """
    Perform primary scrapping. This may either be based on the age distribution of the vessels and their lifetime
    or a fixed yearly scrap rate.

    Parameters
    ----------
    fleet
        The fleet instance.
    idx
        Current time-step index.
    time_step
        Current time-step size.
    """

    # scrap vessels based on age or fixed rate
    if fleet.fixed_scrap_rate is None:
        perform_age_based_scrapping(fleet, idx)
    else:
        perform_fixed_rate_scrapping(fleet, time_step, idx)


def perform_secondary_scrapping(fleet: Fleet, trade_gap: float, idx: int):
    """
    Perform secondary scrapping. This occurs if there is too much tonnage in the fleet after primary scrapping
    compared to the amount of trade required to be satisfied.

    Parameters
    ----------
    fleet
        The fleet instance.
    trade_gap
        The size of the trade gap after primary scrapping. Value is negative.
    idx
        Current time-step index.

    Returns
    -------
    float
        Scrapped capacity.
    """

    scrapped_capacity, youngest_age = perform_fixed_trade_scrapping(fleet, trade_gap, idx)

    trade = fleet.trade[idx]
    if trade > 0 and abs(trade_gap / trade) > 1e-3:
        logger.info(f"{fleet}: Secondary scrapping of vessels to make up for an over capacity of "
                    f"{round(trade_gap)} cargo-miles. "
                    f"The youngest age of scrapping was "
                    f"{f'{round(youngest_age)} years' if youngest_age is not None else 'undefined'}.")

    return scrapped_capacity


def perform_age_based_scrapping(fleet: Fleet, idx: int):
    """
    Perform scrapping based on the age of the vessels. This means that every increment which is greater than the
    lifetime of the vessel is scrapped from the fleet.

    Parameters
    ----------
    fleet
        The fleet instance.
    idx
        Current time-step index.
    """

    for v, (vessel, incs) in enumerate(zip(fleet.assets, fleet.increments)):

        scrapped_vessels = 0.

        # update ages
        lifetime = vessel.lifetime.get()

        # find increments to scrap (age >= lifetime)
        scrap_count = 0
        for inc in incs:
            if inc.age >= lifetime:
                scrapped_vessels += inc.multiplier
                scrap_count += 1
            else:
                break  # increments are ordered oldest-first, so we can stop

        if scrap_count > 0:

            # remove the scrapped vessels from the lists
            fleet.increments[v] = incs[scrap_count:]
            incs = fleet.increments[v]

            # set baseline on the new oldest increment
            if incs:
                incs[0].baseline = incs[0].multiplier

        # scrap vessels from the oldest segment if part of it
        # is older than the lifetime (based on an assumption of
        # vessels entering uniformly over a time-step)
        if incs and incs[0].baseline is not None:

            age_i = incs[0].age
            dt_i = incs[0].dt

            if age_i + dt_i > lifetime:
                alpha = (lifetime - age_i) / dt_i

                remaining = incs[0].baseline * alpha
                scrapping = incs[0].multiplier - remaining

                # part of the increment may have been fuel converted
                # so the scrapped number is truncated to ensure it
                # does not surpass the actual remaining number of vessels
                scrapping = max(scrapping, 0.)

                scrapped_vessels += scrapping

                incs[0].multiplier -= scrapping

        # transfer to profile
        fleet.profile.add_scrap(vessel.name, idx, scrapped_vessels)


def perform_fixed_rate_scrapping(fleet: Fleet, time_step: float, idx: int):
    """
    Perform scrapping based on a fixed rate. This means scrapping a user-defined amount of trade from the fleet.
    The selection criteria for which vessels to scrap is based on age. This means that the oldest increments are
    scrapped first.

    Parameters
    ----------
    fleet
        The fleet instance.
    time_step
        Current time-step size.
    idx
        Current time-step index.
    """

    # calculate the targeted scrap in trade
    scrap_rate = fleet.fixed_scrap_rate.get() * time_step / YEAR
    target_scrap = scrap_rate * fleet.get_cargo_miles(idx)

    # scrap vessels matching the targeted trade
    perform_fixed_trade_scrapping(fleet, -target_scrap, idx)

    # ensure that all remaining increments have
    # an age lower than their technical lifetime
    for v, vessel in enumerate(fleet.assets):

        # if there are no increments, then skip
        if not fleet.increments[v]:
            continue

        # rounding is necessary, otherwise
        # the program might crash due to
        # minor round-off errors
        oldest_age = np.round(fleet.increments[v][0].age, ROUND_OFF)
        lifetime = np.round(vessel.lifetime.get(), ROUND_OFF)

        if oldest_age > lifetime:
            raise ValueError("{}: The oldest increment from {} is older ({}"
                             " years) than the allowed lifetime ({} years)."
                             .format(fleet, vessel, oldest_age, lifetime))


def perform_fixed_trade_scrapping(fleet: Fleet, trade_gap: float, idx: int):
    """
    Perform scrapping based on a fixed amount of trade. The selection criteria for which vessels to scrap is based
    on age. This means that the oldest increments are scrapped first.

    Parameters
    ----------
    fleet
        The fleet instance.
    trade_gap
        The size of the trade gap after primary scrapping. Value is negative.
    idx
        Index of current time-step.

    Returns
    -------
    Scrapped capacity and youngest age of all scrapped vessels.
    """

    # create two lists, one with all increment
    # ages across all vessels and a second with
    # the indices of increments with that age
    # (may contain multiple increment indices)
    age_to_group: dict[float, list] = {}

    for v in range(len(fleet.assets)):

        increment_ages = np.round([inc.age for inc in fleet.increments[v]], ROUND_OFF)

        for i, age in enumerate(increment_ages):

            index = (v, i)

            if age in age_to_group:
                age_to_group[age].append(index)
            else:
                age_to_group[age] = [index]

    ages = list(age_to_group.keys())
    grouped_indices = list(age_to_group.values())

    # extract ton-miles per vessel
    cargo_miles = extract_cargo_miles(fleet.assets, idx)

    # sort in descending order based on age
    sorted_indices = np.argsort(ages)[::-1]

    # changing the sign for convenience
    trade_gap = -trade_gap
    initial_trade = trade_gap

    youngest_age = None

    youngest_index = [0 for _ in range(len(fleet.assets))]

    # scrap vessels until the trade gap is removed
    for i in sorted_indices:

        # extract the vessel/increment
        # indices that share an age
        group = grouped_indices[i]

        # calculate the total scrapping potential
        # across the increments from all vessel types
        capacity = np.sum([fleet.increments[v][ii].multiplier * cargo_miles[v] for v, ii in group])

        if capacity >= trade_gap:

            # remove an equal fraction of trade
            # from each vessel type to reduce
            # the trade gap to zero
            scrap_fraction = trade_gap / capacity

            for v, ii in group:

                # extract necessary parameters
                age = fleet.increments[v][ii].age
                dt = fleet.increments[v][ii].dt

                to_scrap = fleet.increments[v][ii].multiplier * scrap_fraction
                fleet.increments[v][ii].multiplier -= to_scrap

                if ii == 0 and fleet.increments[v][0].baseline is not None:
                    fleet.increments[v][0].baseline -= to_scrap

                # assume that the vessels are scrapped from the
                # oldest part of the uniform increment first.
                # Notice that this may cause an inconsistency
                # if several time-steps are taken that are
                # shorter than the increments time-step length
                youngest_age = age + dt * (1. - scrap_fraction)

                # transfer to profile
                fleet.profile.add_scrap(fleet.assets[v].name, idx, to_scrap)

            # the trade-gap is per definition zero
            trade_gap = 0.

            break

        else:

            # the trade-gap is so large that the
            # entire increment must be scrapped
            # for all vessel types
            trade_gap -= capacity

            for v, ii in group:
                # extract necessary parameters
                increment = fleet.increments[v][ii].multiplier

                youngest_index[v] = ii + 1

                # transfer to profile
                fleet.profile.add_scrap(fleet.assets[v].name, idx, increment)

    # secondary scrapping for anything older than the youngest age
    for v, i in enumerate(youngest_index):

        if i > 0:
            fleet.increments[v] = fleet.increments[v][i:]

            # set baseline on the new oldest increment
            if fleet.increments[v]:
                fleet.increments[v][0].baseline = fleet.increments[v][0].multiplier

    return initial_trade - trade_gap, youngest_age


def clean_up_multipliers(fleet: Fleet):
    """
    The CPU time of the simulation is adversely affected by the number of increments per vessel type.
    In order to reduce the CPU time, increments are merged if they are similar and/or removed if they
    fall below a certain threshold.
    """

    # merge multipliers with same age and initial time-step entry size
    for v in range(len(fleet.assets)):

        incs = fleet.increments[v]
        n = len(incs)
        available = [True] * n

        for i in range(n):

            if not available[i]:
                continue

            age_i = incs[i].age
            dt_i = incs[i].dt

            # find other increments with matching age and dt
            matching = [j for j in range(n) if j != i and available[j]
                        and incs[j].age == age_i and incs[j].dt == dt_i]

            if matching:

                # calculate the weighted average of technology package
                # uptake and carried technology charter rate
                merge_indices = matching + [i]
                package_uptake = np.zeros_like(fleet.newbuild_package_uptake[v])
                charter_rate = 0.

                for j in merge_indices:
                    package_uptake += incs[j].multiplier * incs[j].package_uptake
                    charter_rate += incs[j].multiplier * incs[j].technology_charter_rate

                # move all multipliers into one
                incs[i].multiplier += sum(incs[j].multiplier for j in matching)

                # set the weighted average of uptake and carried rate
                incs[i].package_uptake = package_uptake / incs[i].multiplier
                incs[i].technology_charter_rate = charter_rate / incs[i].multiplier

                # by setting to 0, multipliers will be removed later
                for j in matching:
                    incs[j].multiplier = 0.
                    available[j] = False

    # remove multipliers of insignificant size
    for v in range(len(fleet.assets)):
        fleet.increments[v] = [inc for inc in fleet.increments[v] if inc.multiplier >= 1e-3]


def calculate_evolution_expectation(fleet: Fleet, timeline: np.ndarray, idx: int) -> None:
    """
    Calculates the expected evolution of multipliers based on vessel scrapping,
    uptake patterns, and trade gaps within a given timeline.

    This function computes future multiplier baselines for existing vessels by accounting
    for expected vessel scrap rates. It calculates the trade gap between the required trade
    demand and the expected deliveries, and fills the gap using expectations of future
    vessel uptakes. The resulting multipliers (both for existing vessels and new builds)
    are adjusted to account for operational constraints and are stored as part of the
    expectation model.

    Parameters
    ----------
    fleet
        The fleet instance.
    timeline
        A timeline indicating the years for which the evolutions are calculated,
        expressed in numpy array format. Expected to be in units of time.
    idx
        The starting index for the timeline to begin recalculations of expectations.
    """
    idx_ = np.s_[idx:]
    times = timeline[idx_] / YEAR
    future = times - times[0]

    nv = len(fleet.assets)
    existing = np.zeros((nv, times.size))

    # loop over vessel types and subtract
    # expected future scrapping from the
    # baseline to establish the future baseline
    for v, (vessel, incs) in enumerate(zip(fleet.assets, fleet.increments)):

        if not incs:
            continue

        multipliers = np.array([inc.multiplier for inc in incs])
        ages = np.array([inc.age for inc in incs])

        lifetime = vessel.lifetime.get()

        # calculate cumulative scrap expectation
        cum_increments = np.cumsum(multipliers)
        cum_increments = np.interp(future, (lifetime - ages), cum_increments, left=0.)

        # start the baseline with
        # the current multiplier
        existing[v, :] = fleet.get_multiplier(v)

        # subtract from the baseline
        # of current multipliers
        existing[v, :] -= cum_increments

    # in order to take speed expectations into account
    # the multipliers need to be transformed into cargo-miles
    cargo_miles = extract_cargo_miles(fleet.assets, idx_)
    existing_trade = np.zeros_like(existing)
    for v in range(nv):
        existing_trade[v, :] = existing[v, :] * cargo_miles[v]

    # calculate the trade-gap between the required trade
    # top-line and the expected delivery from the existing
    # vessels
    gap = fleet.trade[idx_] - np.sum(existing_trade, axis=0)

    # if there are negatives due to expected
    # trade reduction the gap is simply truncated
    # to zero leading to too many multipliers
    # compared to trade. In the case where
    # secondary scrapping is allowed this is
    # an overestimation.
    gap = np.where(gap > 0., gap, 0.)

    # fill the gap based on an expectation that the
    # current uptake will continue. Ensure scaling
    # of current uptake in case inertia has reduced
    # it. Note, this does not work well with varying
    # time-step sizes but I am unsure how to include
    # a secondary weight based on time-step size
    index = np.arange(idx + 1)
    weights = fleet.memory.get() ** (idx - index)

    uptakes = fleet.expectation.get_uptakes(idx)
    for i in range(idx + 1):
        if np.all(uptakes[:, i] == 0.):
            weights[i] = 0.

    if np.any(weights) > 0.:
        weighted_uptakes = np.sum(uptakes * weights[np.newaxis, :], axis=1)
        weighted_uptakes /= np.sum(weights)
    else:
        weighted_uptakes = divide_nonzero(fleet.current_uptake, np.sum(fleet.current_uptake), default=1. / nv)

    # calculate the expected trade
    # delivered per vessel type
    newbuild_trade = np.outer(weighted_uptakes, gap)

    # turn the trade delivered per
    # vessel type into multipliers
    newbuild = np.zeros_like(newbuild_trade)
    for v in range(nv):
        newbuild[v, :] = newbuild_trade[v, :] / cargo_miles[v]

    # the expected newbuilds are used during the
    # expected bunkering. In order to ensure a
    # bunkering result per vessel it is a requirement
    # that multiplier > 0 in every nested time-step.
    # This is guaranteed by adjusting the newbuild
    # multipliers slightly. However, to minimize the
    # effect this has on fair-share of fuel, etc.,
    # only a minor perturbation is required
    # TODO: make assignable?
    jump_start_rel = 1e-3
    total_multipliers = np.sum(existing + newbuild, axis=0)
    jump_start = jump_start_rel * total_multipliers
    for v, vessel in enumerate(fleet.assets):

        if fleet.allow_vessel[vessel.name] and fleet.newbuild_available[vessel.name]:
            non_existent = np.where(existing[v, :] + newbuild[v, :] == 0.)
            newbuild[v, non_existent] = jump_start[non_existent]

    # the expected multipliers are then
    # the baseline plus the expected
    # multipliers for filling the gap.
    # Notice there is no need to account for
    # future scrapping of expected multipliers
    # if the timeline extends beyond vessel
    # lifetime as the multipliers that will
    # replace them is expected to follow the
    # same distribution.
    for v, vessel in enumerate(fleet.assets):
        fleet.expectation.set_existing_multipliers(idx, vessel.name, existing[v, :])
        fleet.expectation.set_newbuild_multipliers(idx, vessel.name, newbuild[v, :])


def perform_fleet_evolution(fleet: Fleet, timeline: np.ndarray, time_step: float, idx: int) -> None:
    """
    Evolve the fleet forward in time. This includes scrapping old vessels, performing fuel conversions,
    delivering newbuilds from the orderbook and model newbuilds based on inertia and the discrete choice model.

    Parameters
    ----------
    fleet
        Fleet instance.
    timeline
        Simulation timeline.
    time_step
        Current time-step size.
    idx
        Current time-step index.
    """

    from navigate.fleet.conversion import perform_fuel_conversions
    from navigate.fleet.technology_adoption import (
        reconcile_newbuild_technology_caps,
        transfer_technology_charter_rate,
        transfer_technology_uptake,
        update_residual_energy_demand,
    )

    # scrap old vessels
    perform_primary_scrapping(fleet, idx, time_step)

    # perform fuel conversions
    perform_fuel_conversions(fleet, idx, timeline, time_step)

    # calculate the existing trade-gap
    trade = fleet.trade[idx]
    trade_gap = trade - fleet.get_cargo_miles(idx)

    # per-vessel newbuild count budget for this timestep, threaded across the three newbuild sources.
    # Cap denominator is the pre-newbuild fleet count (proxy for yard capacity); time_step/YEAR scales
    # the per-year limit to a per-step budget.
    multipliers_total = float(sum(fleet.get_multipliers()))
    limit_share = np.array([fleet.newbuild_limit[v.name].get() for v in fleet.assets])
    cap_count = limit_share * multipliers_total * (time_step / YEAR)

    # handle order book
    increments, delivered_capacity, cap_count = calculate_orderbook_newbuilds(fleet, trade_gap, cap_count, idx)
    trade_gap -= delivered_capacity

    # reduce the current uptake shares by
    # the inertia prior to calculating
    # inertia related newbuilds
    fleet.current_uptake *= calculate_inertia(fleet.inertia.get(), time_step)

    if trade_gap > TOLERANCE:
        # calculate newbuilds entering the fleet
        increments_model, delivered_capacity = calculate_modelled_newbuilds(fleet, trade_gap, cap_count, idx)
        increments += increments_model
        trade_gap -= delivered_capacity

    elif (trade_gap < -TOLERANCE) and fleet.allow_secondary_scrapping:
        # perform secondary scrapping to meet exact trade level
        secondary_scrapping = perform_secondary_scrapping(fleet, trade_gap, idx)
        trade_gap += secondary_scrapping

    # clean up multipliers for computational performance enhancement
    clean_up_multipliers(fleet)

    # reconcile newbuild package shares against per-technology flow caps now that vessel-type
    # counts are known
    reconcile_newbuild_technology_caps(fleet, increments, time_step, multipliers_total)

    # add the newbuilds to the list of increments
    add_newbuilds(fleet, increments, time_step)

    # update the residual energy demand now that the fleet composition is updated
    update_residual_energy_demand(fleet, idx)

    # transfer the technology uptake and refresh the fleet-average carried
    # technology charge after evolution, so both profile series consistently
    # reflect this timestep's scrapping, conversions, and newbuilds (the
    # pre-evolution charge transfer already served the cargo charter)
    transfer_technology_uptake(fleet, idx)
    transfer_technology_charter_rate(fleet, idx)

    # check that all the trade has been satisfied otherwise print a warning
    if trade > 0 and (trade_gap / trade) > 1e-3:
        logger.warning("{}: Model was only able to satisfy {}% of the expected trade."
                       .format(fleet, round((1. - trade_gap / trade) * 100.)))

    # calculate and assign current vessel uptake shares
    if np.sum(increments) > 0.:
        cargo_miles = extract_cargo_miles(fleet.assets, idx)
        fleet.current_uptake = (increments * cargo_miles) / np.dot(increments, cargo_miles)

    # save the current uptake to expectations
    current_uptake = divide_nonzero(fleet.current_uptake, np.sum(fleet.current_uptake))
    fleet.expectation.set_uptakes(idx, current_uptake)

    # calculate expected fleet evolution
    calculate_evolution_expectation(fleet, timeline, idx)

    # assign to the profile
    fleet.profile.set_trade(idx, trade - trade_gap)
    fleet.transfer_multipliers_to_profile(idx)
