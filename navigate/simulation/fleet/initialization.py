# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""One-time initialization of the existing fleets at simulation start."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.fleet.aggregation import transfer_multipliers_to_profile
from navigate.simulation.fleet.evolution import calculate_evolution_expectation
from navigate.simulation.fleet.package import preprocess_packages
from navigate.simulation.fleet.planning import extract_cargo_miles
from navigate.simulation.fleet.technology_adoption import (
    build_technology_packages,
    define_initial_technology,
    transfer_technology_charter_rate,
    transfer_technology_uptake,
    update_residual_energy_demand,
)
from navigate.util import calculate_compound_growth

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray


def assign_vessels_to_fleets(fleets: Iterable[Fleet]) -> None:
    """
    Assign every vessel to the fleet that lists it.

    Parameters
    ----------
    fleets
        All fleets of the simulation.

    Raises
    ------
    ValueError
        If a vessel is listed in more than one fleet.
    """
    first_fleet_names: dict[Vessel, str] = {}

    for fleet in fleets:
        for vessel in fleet.assets:
            if vessel in first_fleet_names:
                raise ValueError(
                    f'Fleet("{fleet.name}"): {vessel} is already assigned to a'
                    f' different fleet, Fleet("{first_fleet_names[vessel]}").'
                )

            first_fleet_names[vessel] = fleet.name
            vessel.fleet_assignment = fleet.name


def initialize_existing_fleet(fleet: Fleet, timeline: FloatArray) -> None:
    """
    Initialize the existing fleet, splitting its vessels into increments of varying age.

    Must be called exactly once per fleet: discretization appends to the increment
    stores.

    Parameters
    ----------
    fleet
        Fleet to initialize.
    timeline
        Simulation timeline, days.
    """
    idx = 0
    nv = len(fleet.assets)

    # build the technology packages and their cost flows; the cost flows
    # must exist before the initial technology uptake is seeded, since the
    # seeding levelizes them into the carried technology charter rate
    fleet.technology_packages, fleet.package_to_technology_map = (
        build_technology_packages(fleet.technologies)
    )
    preprocess_packages(fleet.technology_packages, fleet.assets, timeline[idx])

    # the initial split must be defined before the age discretization, as
    # _get_initial_multiplier reads it
    _define_initial_split(fleet)
    fleet.define_initial_age()
    fleet.define_initial_multipliers()
    define_initial_technology(fleet)
    _define_initial_trade(fleet, timeline)

    fleet.orders_delivered = np.zeros((nv,))
    fleet.orders_postponed = np.zeros((nv,))

    # the oldest cohort holds the baseline of partial age-based scrapping
    for incs in fleet.increments:
        if incs:
            incs[0].baseline = incs[0].multiplier

    update_residual_energy_demand(fleet, idx)

    fleet.expectation.set_uptakes(idx, fleet.current_uptake)
    calculate_evolution_expectation(fleet, timeline, idx)

    transfer_multipliers_to_profile(fleet, idx)
    transfer_technology_uptake(fleet, idx)
    transfer_technology_charter_rate(fleet, idx)

    fleet.fuel_conversion_expenses = np.zeros_like(timeline)


def _define_initial_split(fleet: Fleet) -> None:
    """
    Define the initial fraction of each vessel type in the fleet.

    Parameters
    ----------
    fleet
        Fleet to define the initial split for.
    """
    # without a supplied initial split, the cargo-miles are split uniformly
    if not fleet.initial_split:
        nv = len(fleet.assets)
        fleet.initial_split = [1.0 / nv for v in range(nv)]

    # the initial split of the existing fleet need not match the current newbuild
    # trend, but it is the best available proxy for it
    # TODO: allow this to be user-defined
    fleet.current_uptake = np.array(fleet.initial_split)


def _define_initial_trade(fleet: Fleet, timeline: FloatArray) -> None:
    """
    Project the fleet's trade over the timeline by compound growth from its start.

    Parameters
    ----------
    fleet
        Fleet to define the trade for.
    timeline
        Simulation timeline, days.
    """
    idx = 0
    cargo_miles = extract_cargo_miles(fleet.assets, idx)

    multipliers = fleet.get_multipliers()
    initial_trade = np.dot(multipliers, cargo_miles)
    trade_growth = fleet.trade_growth.get(timeline)
    fleet.trade = calculate_compound_growth(initial_trade, trade_growth, timeline)

    fleet.profile.set_trade(idx, fleet.trade[idx])
