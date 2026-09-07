# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""One-time initialization of the existing fleets at simulation start."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.fleet.aggregation import transfer_multipliers_to_profile
from navigate.fleet.evolution import calculate_evolution_expectation
from navigate.fleet.package import preprocess_packages
from navigate.fleet.technology_adoption import (
    build_technology_packages,
    define_initial_technology,
    transfer_technology_charter_rate,
    transfer_technology_uptake,
    update_residual_energy_demand,
)
from navigate.fleet.utils import calculate_projected_multipliers, define_initial_split, define_initial_trade

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet


def initialize_existing_fleet(fleet: Fleet, timeline: np.ndarray) -> None:
    """
    Initialize the existing fleet. This means discretizing the existing fleet in time, by splitting the initial
    number of vessels into individual increments with varying age.

    Must be called exactly once per fleet: discretization appends to the increment stores.

    Parameters
    ----------
    fleet
        Fleet to initialize.
    timeline
        Simulation timeline.
    """

    for vessel in fleet.assets:
        vessel.set_fleet_assignment(fleet.name)

    idx = 0
    nv = len(fleet.assets)

    # build the technology packages and their cost flows; the cost flows
    # must exist before the initial technology uptake is seeded, since the
    # seeding levelizes them into the carried technology charter rate
    fleet.technology_packages, fleet.package_to_technology_map = build_technology_packages(fleet.technologies)
    preprocess_packages(fleet.technology_packages, fleet.assets, timeline[idx])

    # existing fleet; the initial split must be defined before the
    # discretization because _get_initial_multiplier reads it
    define_initial_split(fleet)
    fleet.discretize_initial_assets()
    define_initial_technology(fleet)
    define_initial_trade(fleet, timeline)

    # order book
    fleet.orders_delivered = np.zeros((nv,))
    fleet.orders_postponed = np.zeros((nv,))

    # initialize baseline for partial age-based scrapping
    for incs in fleet.increments:
        if incs:
            incs[0].baseline = incs[0].multiplier

    # calculate a naive projection of multipliers
    # which is used to calculate fair-share emissions
    # for fleet level and global regulations
    multipliers = sum(fleet.get_multipliers())
    fleet.projected_multipliers = calculate_projected_multipliers(multipliers, fleet.trade)

    # calculate the initial effect from technology
    update_residual_energy_demand(fleet, idx)

    # calculate the initial fleet evolution expectation
    fleet.expectation.set_uptakes(idx, fleet.current_uptake)
    calculate_evolution_expectation(fleet, timeline, idx)

    # initialize technology effect
    transfer_multipliers_to_profile(fleet, idx)
    transfer_technology_uptake(fleet, idx)
    transfer_technology_charter_rate(fleet, idx)

    # set dynamic properties
    fleet.fuel_conversion_expenses = np.zeros_like(timeline)
