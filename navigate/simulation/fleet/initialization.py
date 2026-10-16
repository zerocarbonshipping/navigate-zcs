# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""One-time initialization of the existing fleets at simulation start."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.increment import VesselIncrement
from navigate.core.nodes.curve import Curve
from navigate.simulation.fleet.aggregation import (
    get_multipliers,
    transfer_multipliers_to_profile,
)
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
    from navigate.core.types_ import CurveTableInput
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
        for vessel in fleet.vessels:
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

    Parameters
    ----------
    fleet
        Fleet to initialize.
    timeline
        Simulation timeline, days.
    """
    idx = 0
    nv = len(fleet.vessels)

    # build the technology packages and anchor their cost flows at the start;
    # this must precede seeding the initial technology uptake, which levelizes
    # the cost flows into the carried technology charter rate
    fleet.technology_packages, fleet.package_to_technology_map = (
        build_technology_packages(fleet.technologies)
    )
    preprocess_packages(
        fleet.technology_packages, fleet.package_cost_flows, timeline[idx]
    )

    # the initial split of the existing fleet need not match the current newbuild
    # trend, but it is the best available proxy for it
    # TODO: allow this to be user-defined
    fleet.current_uptake = np.array(fleet.initial_split)

    fleet.increments = _build_initial_increments(fleet)
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


def _build_initial_increments(fleet: Fleet) -> list[list[VesselIncrement]]:
    """
    Build the initial increments of every vessel type from its initial count.

    Parameters
    ----------
    fleet
        Fleet whose initial vessels are split.

    Returns
    -------
    list[list[VesselIncrement]]
        The increments of each vessel type, oldest first.
    """
    increments: list[list[VesselIncrement]] = []

    for v, vessel in enumerate(fleet.vessels):
        multiplier = fleet.initial_split[v] * fleet.initial_vessels.get()
        distribution = fleet.initial_age_distribution[v]

        if multiplier > 0.0:
            increments.append(_split_by_age(fleet, vessel, multiplier, distribution))
        else:
            increments.append([])

    return increments


def _split_by_age(
    fleet: Fleet, vessel: Vessel, multiplier: float, distribution: CurveTableInput
) -> list[VesselIncrement]:
    """
    Split the initial vessels of one type into one increment per age bin.

    A Curve distribution sets the ages and the share of each; otherwise the vessels
    are spread evenly over yearly bins across their initial age range.

    Parameters
    ----------
    fleet
        Fleet the vessels belong to.
    vessel
        Vessel type of the vessels.
    multiplier
        Number of initial vessels of the type.
    distribution
        Initial age distribution of the type; a number spreads the ages evenly.

    Returns
    -------
    list[VesselIncrement]
        The increments of the type, oldest first.
    """
    if isinstance(distribution, Curve):
        ages = distribution.x[::-1]
        multipliers = multiplier * distribution.y[::-1]

    else:
        age_range = _calculate_initial_age_range(fleet, vessel)
        bins = int(age_range)
        ages = np.linspace(age_range - 1.0, 0.0, bins)
        multipliers = [multiplier / bins for _ in range(bins)]

    # the oldest increment is assumed to have entered over a year
    spans = np.insert(ages[:-1] - ages[1:], 0, 1.0)
    packages = fleet.get_number_of_packages()
    increments: list[VesselIncrement] = []

    for i in range(ages.size):
        increment = VesselIncrement(
            multiplier=multipliers[i],
            age=float(ages[i]),
            age_span=float(spans[i]),
            package_uptake=np.zeros(packages),
        )
        increments.append(increment)

    return increments


def _calculate_initial_age_range(fleet: Fleet, vessel: Vessel) -> float:
    """
    Return the age range the initial vessels of a type are spread over.

    It is the vessel lifetime, capped at the inverse of the fleet's fixed scrap rate.

    Parameters
    ----------
    fleet
        Fleet the vessels belong to.
    vessel
        Vessel type of the vessels.

    Returns
    -------
    float
        Age range, in years.
    """
    lifetime = vessel.lifetime.get()

    if fleet.fixed_scrap_rate is None:
        return lifetime

    scrap_rate = fleet.fixed_scrap_rate.get()

    if scrap_rate > 0.0:
        return min(lifetime, 1.0 / scrap_rate)

    return lifetime


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
    cargo_miles = extract_cargo_miles(fleet.vessels, idx)

    multipliers = get_multipliers(fleet)
    initial_trade = np.dot(multipliers, cargo_miles)
    trade_growth = fleet.trade_growth.get(timeline)
    fleet.trade = calculate_compound_growth(initial_trade, trade_growth, timeline)

    fleet.profile.set_trade(idx, fleet.trade[idx])
