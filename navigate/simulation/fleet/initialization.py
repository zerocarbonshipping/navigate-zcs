# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""One-time initialization of the existing fleets at simulation start."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.increment import VesselIncrement
from navigate.simulation.cohort import split_by_age
from navigate.simulation.fleet._composition import extract_cargo_miles, get_multipliers
from navigate.simulation.fleet._package import (
    build_technology_packages,
    calculate_package_charter_rates,
    update_packages,
)
from navigate.simulation.fleet.expectation import calculate_fleet_evolution_expectation
from navigate.simulation.fleet.technology_adoption import (
    transfer_technology_charter_rate,
)
from navigate.simulation.fleet.technology_effect import update_residual_energy_demand
from navigate.util import calculate_compound_growth

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.technology import Technology
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.technology_package import TechnologyPackage
    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)


def assign_vessels_to_fleets(fleets: Iterable[Fleet]) -> None:
    """
    Assign every vessel to the fleet that lists it.

    Parameters
    ----------
    fleets
        All fleets in the simulation.

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
        Simulation timeline, in days.
    """
    idx = 0

    # build the technology packages and anchor their cost flows at the start;
    # this must precede seeding the initial technology uptake, which levelizes
    # the cost flows into the carried technology charter rate
    fleet.technology_packages = build_technology_packages(fleet.technologies)
    update_packages(fleet.technology_packages, fleet.package_cost_flows, timeline[idx])

    n_packages = fleet.get_number_of_packages()
    fleet.newbuild_package_uptake = [np.zeros(n_packages) for _ in fleet.vessels]
    fleet.orders_delivered = np.zeros(len(fleet.vessels))
    fleet.orders_postponed = np.zeros(len(fleet.vessels))
    fleet.fuel_conversion_expenses = np.zeros_like(timeline)

    # the initial split of the existing fleet need not match the current newbuild
    # trend, but it is the best available proxy for it
    # TODO: allow this to be user-defined
    fleet.current_uptake = np.array(fleet.initial_split)

    fleet.increments = _build_initial_increments(fleet)
    _seed_initial_uptake(fleet)
    _define_initial_trade(fleet, timeline)

    update_residual_energy_demand(fleet, idx)

    fleet.expectation.set_uptakes(idx, fleet.current_uptake)
    calculate_fleet_evolution_expectation(fleet, timeline, idx)

    transfer_technology_charter_rate(fleet, idx)


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
    return [_build_vessel_increments(fleet, v) for v in range(len(fleet.vessels))]


def _build_vessel_increments(fleet: Fleet, vessel_idx: int) -> list[VesselIncrement]:
    """
    Build the initial increments of one vessel type, one per age bin.

    Where the type's initial age distribution is a number, its vessels are spread
    evenly over its initial age range.

    Parameters
    ----------
    fleet
        Fleet the vessels belong to.
    vessel_idx
        Index of the vessel type in the fleet.

    Returns
    -------
    list[VesselIncrement]
        The increments of the type, oldest first.
    """
    vessel = fleet.vessels[vessel_idx]
    count = fleet.initial_split[vessel_idx] * fleet.initial_vessels.get()
    distribution = fleet.initial_age_distribution[vessel_idx]
    age_range = _calculate_initial_age_range(fleet, vessel)
    n_packages = fleet.get_number_of_packages()

    # a NaN count, such as from an expression dividing by zero, builds no cohorts
    if not count > 0.0:
        return []

    increments: list[VesselIncrement] = []
    for age, span, multiplier in split_by_age(count, distribution, age_range):
        increment = VesselIncrement(
            multiplier=multiplier,
            age=float(age),
            age_span=float(span),
            package_uptake=np.zeros(n_packages),
        )
        increments.append(increment)

    # the oldest cohort holds the baseline of partial age-based scrapping
    if increments:
        increments[0].baseline = increments[0].multiplier

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


def _seed_initial_uptake(fleet: Fleet) -> None:
    """
    Seed the initial package uptake of every vessel type from its technology shares.

    Without any share the increments keep no uptake, not even of the empty package.

    Parameters
    ----------
    fleet
        Fleet whose increments are seeded.
    """
    if all(share is None for share in fleet.initial_technology_share.values()):
        return

    for v in range(len(fleet.vessels)):
        _seed_vessel_uptake(fleet, v)


def _seed_vessel_uptake(fleet: Fleet, vessel_idx: int) -> None:
    """
    Seed one vessel's age-dependent initial package mix and carried technology charge.

    Each (vessel, technology) pair may have an uptake Curve with age on the x-axis,
    read at each increment's age. Shares exceeding what the cumulative packages can
    represent are truncated, with one warning per vessel.

    Parameters
    ----------
    fleet
        Fleet the vessel belongs to.
    vessel_idx
        Index of the vessel type in the fleet.
    """
    vessel = fleet.vessels[vessel_idx]
    technologies = fleet.technologies
    packages = fleet.technology_packages
    truncation_count = 0
    truncated_names: set[str] = set()

    # seeded uptake is charged as if installed at build (consistent with the
    # hull, which the instantaneous freight rate charges at full newbuild cost)
    package_rates = calculate_package_charter_rates(
        packages, fleet.package_cost_flows, vessel
    )

    for increment in fleet.increments[vessel_idx]:
        shares = _get_initial_shares(fleet, vessel, increment.age)
        package_mix, truncated = _calculate_package_mix(technologies, packages, shares)
        increment.package_uptake = package_mix
        increment.technology_charter_rate = float(np.dot(package_mix, package_rates))

        if truncated:
            truncation_count += 1
            truncated_names |= truncated

    if truncation_count > 0:
        techs = ", ".join(sorted(truncated_names))

        logger.warning(
            "Truncated initial technology shares for vessel '%s' across %d age "
            "increment(s): %s",
            vessel.name,
            truncation_count,
            techs,
        )


def _get_initial_shares(fleet: Fleet, vessel: Vessel, age: float) -> FloatArray:
    """
    Return the initial uptake share of each technology of a vessel at an age.

    Parameters
    ----------
    fleet
        Fleet the vessel belongs to.
    vessel
        Vessel type the shares apply to.
    age
        Age of the vessels, in years.

    Returns
    -------
    FloatArray
        Uptake share of each technology, fraction; zero where no share is set.
    """
    shares = np.zeros(len(fleet.technologies))

    for t, technology in enumerate(fleet.technologies):
        share = fleet.initial_technology_share[(vessel.name, technology.name)]
        if share is not None:
            shares[t] = share.get(age)

    return shares


def _calculate_package_mix(
    technologies: list[Technology],
    packages: list[TechnologyPackage],
    shares: FloatArray,
) -> tuple[FloatArray, set[str]]:
    """
    Convert per-technology shares into per-package shares.

    Allocates greedily to larger packages first, then puts the remainder
    into the empty package.

    Parameters
    ----------
    technologies
        Technologies the shares refer to.
    packages
        Packages sorted by size, the empty package at index 0.
    shares
        Uptake share of each technology, fraction.

    Returns
    -------
    FloatArray
        Share of each package, fraction.
    set[str]
        Names of the technologies whose shares were truncated.
    """
    index = {technology: i for i, technology in enumerate(technologies)}
    remaining = shares.copy()
    package_shares = np.zeros(len(packages))

    for p in reversed(range(1, len(packages))):
        indices = [index[technology] for technology in packages[p].technologies]
        share = remaining[indices].min()
        if share > 0:
            package_shares[p] = share
            remaining[indices] -= share

    package_shares[0] = 1.0 - package_shares[1:].sum()
    truncated = {technologies[i].name for i in np.flatnonzero(remaining > 0)}

    return package_shares, truncated


def _define_initial_trade(fleet: Fleet, timeline: FloatArray) -> None:
    """
    Project the fleet's trade over the timeline by compound growth from its start.

    Parameters
    ----------
    fleet
        Fleet to define the trade for.
    timeline
        Simulation timeline, in days.
    """
    idx = 0
    multipliers = get_multipliers(fleet)
    cargo_miles = extract_cargo_miles(fleet.vessels, idx)
    trade_growth = fleet.trade_growth.get(timeline)

    initial_trade = np.dot(multipliers, cargo_miles)
    fleet.trade = calculate_compound_growth(initial_trade, trade_growth, timeline)
    fleet.results.trade[idx] = fleet.trade[idx]
