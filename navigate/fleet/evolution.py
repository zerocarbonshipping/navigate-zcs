# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Fleet evolution: scrapping, fuel conversion, newbuilds and the expected fleet."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.fleet.aggregation import transfer_multipliers_to_profile
from navigate.fleet.planning import (
    add_newbuilds,
    calculate_modelled_newbuilds,
    calculate_orderbook_newbuilds,
    extract_cargo_miles,
    extract_cargo_miles_timeline,
)
from navigate.util import ROUND_OFF, TOLERANCE, YEAR, calculate_inertia, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.types_ import ForecastInput
    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)


def perform_primary_scrapping(fleet: Fleet, idx: int, time_step: float) -> None:
    """
    Scrap vessels by age, or by the fixed scrap rate when the fleet sets one.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    idx
        Current time-step index.
    time_step
        Current time-step size, days.
    """
    if fleet.fixed_scrap_rate is None:
        perform_age_based_scrapping(fleet, idx)
    else:
        perform_fixed_rate_scrapping(fleet, fleet.fixed_scrap_rate, time_step, idx)


def perform_secondary_scrapping(fleet: Fleet, trade_gap: float, idx: int) -> float:
    """
    Scrap the oldest vessels to remove the over-capacity left by primary scrapping.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    trade_gap
        Trade gap after primary scrapping, cargo-miles/year; negative.
    idx
        Current time-step index.

    Returns
    -------
    float
        Scrapped capacity, cargo-miles/year.
    """
    scrapped_capacity, youngest_age = perform_fixed_trade_scrapping(
        fleet, trade_gap, idx
    )

    trade = fleet.trade[idx]
    if trade > 0 and abs(trade_gap / trade) > 1e-3:
        youngest_age_str = (
            f"{round(youngest_age)} years" if youngest_age is not None else "undefined"
        )
        logger.info(
            "%s: Secondary scrapping of vessels to make up for an over capacity of %s "
            "cargo-miles. The youngest age of scrapping was %s.",
            fleet,
            round(trade_gap),
            youngest_age_str,
        )

    return scrapped_capacity


def perform_age_based_scrapping(fleet: Fleet, idx: int) -> None:
    """
    Scrap the increments at the vessel lifetime, and any older part of the next one.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    idx
        Current time-step index.
    """
    for v, (vessel, incs) in enumerate(
        zip(fleet.assets, fleet.increments, strict=True)
    ):
        scrapped_vessels = 0.0
        lifetime = vessel.lifetime.get()

        scrap_count = 0
        for inc in incs:
            if inc.age >= lifetime:
                scrapped_vessels += inc.multiplier
                scrap_count += 1
            else:
                break  # the increments are ordered oldest first

        if scrap_count > 0:
            fleet.increments[v] = incs[scrap_count:]
            incs = fleet.increments[v]

            if incs:
                incs[0].baseline = incs[0].multiplier

        # scrap the part of the oldest cohort beyond the lifetime, assuming its
        # vessels entered uniformly over its age span
        if incs and incs[0].baseline is not None:
            age_i = incs[0].age
            dt_i = incs[0].age_span

            if age_i + dt_i > lifetime:
                alpha = (lifetime - age_i) / dt_i

                remaining = incs[0].baseline * alpha
                scrapping = incs[0].multiplier - remaining

                # conversions out of the cohort can leave fewer vessels than the
                # baseline share that remains, so the scrapping is floored at zero
                scrapping = max(scrapping, 0.0)

                scrapped_vessels += scrapping
                incs[0].multiplier -= scrapping

        fleet.profile.add_scrap(vessel.name, scrapped_vessels, idx)


def perform_fixed_rate_scrapping(
    fleet: Fleet, fixed_scrap_rate: ForecastInput, time_step: float, idx: int
) -> None:
    """
    Scrap a fixed yearly share of the fleet's trade, oldest increments first.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    fixed_scrap_rate
        Share of the fleet's trade scrapped per year, fraction.
    time_step
        Current time-step size, days.
    idx
        Current time-step index.
    """
    scrap_rate = fixed_scrap_rate.get() * time_step / YEAR
    target_scrap = scrap_rate * _get_cargo_miles(fleet, idx)
    perform_fixed_trade_scrapping(fleet, -target_scrap, idx)

    for v, vessel in enumerate(fleet.assets):
        if not fleet.increments[v]:
            continue

        # rounding keeps round-off error from tripping the lifetime check
        oldest_age = np.round(fleet.increments[v][0].age, ROUND_OFF)
        lifetime = np.round(vessel.lifetime.get(), ROUND_OFF)

        if oldest_age > lifetime:
            raise ValueError(
                f"{fleet}: The oldest increment from {vessel} is older ({oldest_age}"
                f" years) than the allowed lifetime ({lifetime} years)."
            )


def perform_fixed_trade_scrapping(
    fleet: Fleet, trade_gap: float, idx: int
) -> tuple[float, float | None]:
    """
    Scrap a given amount of trade, oldest increments first.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    trade_gap
        Trade to scrap, cargo-miles/year; negative.
    idx
        Current time-step index.

    Returns
    -------
    tuple[float, float | None]
        Scrapped capacity, cargo-miles/year, and the youngest age scrapped, years, or
        None when nothing was scrapped in part.
    """
    # the increments of one age are scrapped together across vessel types, so their
    # (vessel, increment) indices are grouped by the rounded age
    age_to_group: dict[float, list[tuple[int, int]]] = {}

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

    cargo_miles = extract_cargo_miles(fleet.assets, idx)
    sorted_indices = np.argsort(ages)[::-1]

    trade_gap = -trade_gap
    initial_trade = trade_gap

    youngest_age = None
    youngest_index = [0 for _ in range(len(fleet.assets))]

    for i in sorted_indices:
        group = grouped_indices[i]
        capacity = np.sum(
            [fleet.increments[v][ii].multiplier * cargo_miles[v] for v, ii in group]
        )

        if capacity >= trade_gap:
            # the age group covers the gap: scrap the same fraction of each of its
            # increments
            scrap_fraction = trade_gap / capacity

            for v, ii in group:
                age = fleet.increments[v][ii].age
                dt = fleet.increments[v][ii].age_span

                to_scrap = fleet.increments[v][ii].multiplier * scrap_fraction
                fleet.increments[v][ii].multiplier -= to_scrap

                if ii == 0 and fleet.increments[v][0].baseline is not None:
                    fleet.increments[v][0].baseline -= to_scrap

                # vessels are scrapped from the oldest part of the uniform increment
                # first, which is inconsistent when several time-steps shorter than
                # the increment's age span pass
                youngest_age = age + dt * (1.0 - scrap_fraction)

                fleet.profile.add_scrap(fleet.assets[v].name, to_scrap, idx)

            trade_gap = 0.0

            break

        else:
            # the gap exceeds the age group's capacity: scrap all of its increments
            trade_gap -= capacity

            for v, ii in group:
                multiplier = fleet.increments[v][ii].multiplier
                youngest_index[v] = ii + 1
                fleet.profile.add_scrap(fleet.assets[v].name, multiplier, idx)

    # drop the increments scrapped in full
    for v, i in enumerate(youngest_index):
        if i > 0:
            fleet.increments[v] = fleet.increments[v][i:]

            if fleet.increments[v]:
                fleet.increments[v][0].baseline = fleet.increments[v][0].multiplier

    return initial_trade - trade_gap, youngest_age


def clean_up_multipliers(fleet: Fleet) -> None:
    """
    Merge increments of equal age and age span, and drop those below 1e-3 vessels.

    The simulation's CPU time grows with the number of increments per vessel type.

    Parameters
    ----------
    fleet
        Fleet whose increments are cleaned up.
    """
    for v in range(len(fleet.assets)):
        incs = fleet.increments[v]
        n = len(incs)
        available = [True] * n

        for i in range(n):
            if not available[i]:
                continue

            age_i = incs[i].age
            dt_i = incs[i].age_span

            matching = [
                j
                for j in range(n)
                if j != i
                and available[j]
                and incs[j].age == age_i
                and incs[j].age_span == dt_i
            ]

            if matching:
                merge_indices = [*matching, i]
                package_uptake = np.zeros_like(fleet.newbuild_package_uptake[v])
                charter_rate = 0.0

                for j in merge_indices:
                    package_uptake += incs[j].multiplier * incs[j].package_uptake
                    charter_rate += incs[j].multiplier * incs[j].technology_charter_rate

                incs[i].multiplier += sum(incs[j].multiplier for j in matching)
                incs[i].package_uptake = package_uptake / incs[i].multiplier
                incs[i].technology_charter_rate = charter_rate / incs[i].multiplier

                # a zeroed increment is dropped by the filter below
                for j in matching:
                    incs[j].multiplier = 0.0
                    available[j] = False

    for v in range(len(fleet.assets)):
        fleet.increments[v] = [
            inc for inc in fleet.increments[v] if inc.multiplier >= 1e-3
        ]


def calculate_evolution_expectation(
    fleet: Fleet, timeline: FloatArray, idx: int
) -> None:
    """
    Calculate the expected existing and newbuild multipliers from this time-step on.

    The existing vessels decline by their expected scrapping; the trade gap this
    leaves is filled with newbuilds split by the memory-weighted recent uptake.

    Parameters
    ----------
    fleet
        Fleet whose expected evolution is calculated.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index, where the expectation starts.
    """
    idx_ = np.s_[idx:]
    times = timeline[idx_] / YEAR
    future = times - times[0]

    nv = len(fleet.assets)
    existing = np.zeros((nv, times.size))

    for v, (vessel, incs) in enumerate(
        zip(fleet.assets, fleet.increments, strict=True)
    ):
        if not incs:
            continue

        multipliers = np.array([inc.multiplier for inc in incs])
        ages = np.array([inc.age for inc in incs])

        lifetime = vessel.lifetime.get()

        # each increment reaches its lifetime after lifetime - age years, oldest
        # first, so the cumulative sum is the expected scrapping to date
        cum_increments = np.cumsum(multipliers)
        cum_increments = np.interp(future, (lifetime - ages), cum_increments, left=0.0)

        existing[v, :] = fleet.get_multiplier(v)
        existing[v, :] -= cum_increments

    # the multipliers become cargo-miles to take the speed expectations into account
    cargo_miles = extract_cargo_miles_timeline(fleet.assets, idx_)
    existing_trade = np.zeros_like(existing)
    for v in range(nv):
        existing_trade[v, :] = existing[v, :] * cargo_miles[v]

    gap = fleet.trade[idx_] - np.sum(existing_trade, axis=0)

    # a gap turned negative by falling trade is truncated to zero, which leaves more
    # vessels than trade; where secondary scrapping is allowed this overestimates the
    # fleet
    gap = np.where(gap > 0.0, gap, 0.0)

    # the gap is filled on the expectation that the recent uptake continues, weighted
    # by memory, with the current uptake renormalized in case inertia has reduced it;
    # the weights ignore the time-step size, so they misweigh a timeline of varying
    # step sizes
    index = np.arange(idx + 1)
    weights = fleet.memory.get() ** (idx - index)

    uptakes = fleet.expectation.get_uptakes(idx)
    for i in range(idx + 1):
        if np.all(uptakes[:, i] == 0.0):
            weights[i] = 0.0

    if np.any(weights) > 0.0:
        weighted_uptakes = np.sum(uptakes * weights[np.newaxis, :], axis=1)
        weighted_uptakes /= np.sum(weights)
    else:
        weighted_uptakes = divide_nonzero(
            fleet.current_uptake, np.sum(fleet.current_uptake), default=1.0 / nv
        )

    newbuild_trade = np.outer(weighted_uptakes, gap)
    newbuild = np.zeros_like(newbuild_trade)
    for v in range(nv):
        newbuild[v, :] = newbuild_trade[v, :] / cargo_miles[v]

    # the expected bunkering needs a multiplier above zero for every allowed vessel
    # type in every nested time-step to return a result per vessel; a small jump
    # start guarantees it while barely moving the fair shares of fuel
    # TODO: make assignable?
    jump_start_rel = 1e-3
    total_multipliers = np.sum(existing + newbuild, axis=0)
    jump_start = jump_start_rel * total_multipliers
    for v, vessel in enumerate(fleet.assets):
        if fleet.allow_vessel[vessel.name] and fleet.newbuild_available[vessel.name]:
            non_existent = np.where(existing[v, :] + newbuild[v, :] == 0.0)
            newbuild[v, non_existent] = jump_start[non_existent]

    # the expected newbuilds need no scrapping of their own beyond the vessel
    # lifetime: the vessels replacing them are expected to follow the same
    # distribution
    for v, vessel in enumerate(fleet.assets):
        fleet.expectation.set_existing_multipliers(idx, vessel.name, existing[v, :])
        fleet.expectation.set_newbuild_multipliers(idx, vessel.name, newbuild[v, :])


def perform_fleet_evolution(
    fleet: Fleet, timeline: FloatArray, time_step: float, idx: int
) -> None:
    """
    Evolve the fleet by one time-step.

    Scraps old vessels, converts vessels, delivers the orderbook and the modelled
    newbuilds, and updates the expected fleet.

    Parameters
    ----------
    fleet
        Fleet to evolve.
    timeline
        Simulation timeline, days.
    time_step
        Current time-step size, days.
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

    perform_primary_scrapping(fleet, idx, time_step)
    perform_fuel_conversions(fleet, idx, timeline, time_step)

    trade = fleet.trade[idx]
    trade_gap = trade - _get_cargo_miles(fleet, idx)

    # each vessel type's newbuild budget for this time-step, shared by the three
    # newbuild sources; the fleet count before newbuilds stands in for yard capacity
    multipliers_total = float(sum(fleet.get_multipliers()))
    limit_share = np.array([fleet.newbuild_limit[v.name].get() for v in fleet.assets])
    cap_count = limit_share * multipliers_total * (time_step / YEAR)

    increments, delivered_capacity, cap_count = calculate_orderbook_newbuilds(
        fleet, trade_gap, cap_count, idx
    )
    trade_gap -= delivered_capacity

    # inertia decays the current uptake shares before the modelled newbuilds read them
    fleet.current_uptake *= calculate_inertia(fleet.inertia.get(), time_step)

    if trade_gap > TOLERANCE:
        increments_model, delivered_capacity = calculate_modelled_newbuilds(
            fleet, trade_gap, cap_count, idx
        )
        increments += increments_model
        trade_gap -= delivered_capacity

    elif (trade_gap < -TOLERANCE) and fleet.allow_secondary_scrapping:
        secondary_scrapping = perform_secondary_scrapping(fleet, trade_gap, idx)
        trade_gap += secondary_scrapping

    clean_up_multipliers(fleet)

    # reconcile newbuild package shares against per-technology flow caps now that
    # vessel-type counts are known
    reconcile_newbuild_technology_caps(fleet, increments, time_step, multipliers_total)
    add_newbuilds(fleet, increments, time_step)

    # the residual energy demand reads the updated fleet composition
    update_residual_energy_demand(fleet, idx)

    # transfer the technology uptake and refresh the fleet-average carried
    # technology charge after evolution, so both profile series consistently
    # reflect this timestep's scrapping, conversions, and newbuilds (the
    # pre-evolution charge transfer already served the cargo charter)
    transfer_technology_uptake(fleet, idx)
    transfer_technology_charter_rate(fleet, idx)

    if trade > 0 and (trade_gap / trade) > 1e-3:
        logger.warning(
            "%s: Model was only able to satisfy %s%% of the expected trade.",
            fleet,
            round((1.0 - trade_gap / trade) * 100.0),
        )

    if np.sum(increments) > 0.0:
        cargo_miles = extract_cargo_miles(fleet.assets, idx)
        fleet.current_uptake = (increments * cargo_miles) / np.dot(
            increments, cargo_miles
        )

    current_uptake = divide_nonzero(fleet.current_uptake, np.sum(fleet.current_uptake))
    fleet.expectation.set_uptakes(idx, current_uptake)

    calculate_evolution_expectation(fleet, timeline, idx)

    fleet.profile.set_trade(idx, trade - trade_gap)
    transfer_multipliers_to_profile(fleet, idx)


def _get_cargo_miles(fleet: Fleet, idx: int) -> float:
    multipliers = fleet.get_multipliers()
    cargo_miles = extract_cargo_miles(fleet.assets, idx)

    return float(np.dot(multipliers, cargo_miles))
