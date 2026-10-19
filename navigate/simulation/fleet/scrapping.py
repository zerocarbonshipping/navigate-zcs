# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Vessel ageing and the scrapping that removes vessels."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.cohort import calculate_share_below, extends_past
from navigate.simulation.fleet.composition import (
    extract_cargo_miles,
    get_trade_capacity,
)
from navigate.util import ROUND_OFF, YEAR

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.types_ import ForecastInput

logger = logging.getLogger(__name__)


def update_vessel_ages(fleet: Fleet, time_step: float) -> None:
    """
    Age the fleet's vessels by the time since the last time-step.

    Parameters
    ----------
    fleet
        Fleet whose vessels are aged.
    time_step
        Current time-step size, days.
    """
    dt = time_step / YEAR

    for increments in fleet.increments:
        for increment in increments:
            increment.age += dt


def perform_primary_scrapping(fleet: Fleet, time_step: float, idx: int) -> None:
    """
    Scrap vessels by age, or by the fixed scrap rate when the fleet sets one.

    Parameters
    ----------
    fleet
        Fleet whose vessels are scrapped.
    time_step
        Current time-step size, days.
    idx
        Current time-step index.
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
        zip(fleet.vessels, fleet.increments, strict=True)
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

        surviving = incs
        if scrap_count > 0:
            surviving = incs[scrap_count:]
            fleet.increments[v] = surviving

            if surviving:
                surviving[0].baseline = surviving[0].multiplier

        baseline = surviving[0].baseline if surviving else None

        # scrap the part of the oldest cohort beyond the lifetime, assuming its
        # vessels entered uniformly over its age span
        if baseline is not None and extends_past(surviving[0], lifetime):
            alpha = calculate_share_below(surviving[0], lifetime)

            remaining = baseline * alpha
            scrapping = surviving[0].multiplier - remaining

            # conversions out of the cohort can leave fewer vessels than the
            # baseline share that remains, so the scrapping is floored at zero
            scrapping = max(scrapping, 0.0)

            scrapped_vessels += scrapping
            surviving[0].multiplier -= scrapping

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
    target_scrap = scrap_rate * get_trade_capacity(fleet, idx)
    perform_fixed_trade_scrapping(fleet, -target_scrap, idx)

    for v, vessel in enumerate(fleet.vessels):
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

    for v in range(len(fleet.vessels)):
        increment_ages = np.round([inc.age for inc in fleet.increments[v]], ROUND_OFF)

        for i, age in enumerate(increment_ages):
            index = (v, i)

            if age in age_to_group:
                age_to_group[age].append(index)
            else:
                age_to_group[age] = [index]

    ages = list(age_to_group.keys())
    grouped_indices = list(age_to_group.values())

    cargo_miles = extract_cargo_miles(fleet.vessels, idx)
    sorted_indices = np.argsort(ages)[::-1]

    trade_gap = -trade_gap
    initial_trade = trade_gap

    youngest_age = None
    youngest_index = [0 for _ in range(len(fleet.vessels))]

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

                fleet.profile.add_scrap(fleet.vessels[v].name, to_scrap, idx)

            trade_gap = 0.0

            break

        # the gap exceeds the age group's capacity: scrap all of its increments
        trade_gap -= capacity

        for v, ii in group:
            multiplier = fleet.increments[v][ii].multiplier
            youngest_index[v] = ii + 1
            fleet.profile.add_scrap(fleet.vessels[v].name, multiplier, idx)

    # drop the increments scrapped in full
    for v, i in enumerate(youngest_index):
        if i > 0:
            fleet.increments[v] = fleet.increments[v][i:]

            if fleet.increments[v]:
                fleet.increments[v][0].baseline = fleet.increments[v][0].multiplier

    return initial_trade - trade_gap, youngest_age
