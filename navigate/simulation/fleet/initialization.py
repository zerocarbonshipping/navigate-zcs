# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""One-time initialization of the existing fleets at simulation start."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.increment import VesselIncrement
from navigate.simulation.cohort import split_by_age
from navigate.simulation.fleet.composition import extract_cargo_miles, get_multipliers
from navigate.simulation.fleet.expectation import calculate_fleet_evolution_expectation
from navigate.simulation.fleet.package import (
    build_technology_packages,
    calculate_package_charter_rates,
    preprocess_packages,
)
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
    _define_initial_technology(fleet)
    _define_initial_trade(fleet, timeline)

    fleet.orders_delivered = np.zeros((nv,))
    fleet.orders_postponed = np.zeros((nv,))

    # the oldest cohort holds the baseline of partial age-based scrapping
    for incs in fleet.increments:
        if incs:
            incs[0].baseline = incs[0].multiplier

    update_residual_energy_demand(fleet, idx)

    fleet.expectation.set_uptakes(idx, fleet.current_uptake)
    calculate_fleet_evolution_expectation(fleet, timeline, idx)

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
    packages = fleet.get_number_of_packages()
    increments: list[VesselIncrement] = []

    if count > 0.0:
        for age, span, multiplier in split_by_age(count, distribution, age_range):
            increment = VesselIncrement(
                multiplier=multiplier,
                age=float(age),
                age_span=float(span),
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


def _define_initial_technology(fleet: Fleet) -> None:
    """
    Initialize the technology-adoption storage for the fleet.

    Seeds each vessel's initial package uptake; see
    `_seed_vessel_initial_uptake`.

    Parameters
    ----------
    fleet
        Fleet to initialize technology for.
    """
    n_pkgs = fleet.get_number_of_packages()
    n_vessels = len(fleet.vessels)

    fleet.newbuild_package_uptake = [
        np.zeros(n_pkgs, dtype=float) for _ in range(n_vessels)
    ]

    if all(share is None for share in fleet.initial_technology_share.values()):
        return

    for v, vessel in enumerate(fleet.vessels):
        _seed_vessel_initial_uptake(fleet, vessel, v)


def _seed_vessel_initial_uptake(fleet: Fleet, vessel: Vessel, vessel_idx: int) -> None:
    """
    Seed one vessel's age-dependent initial package mix and carried technology charge.

    Each (vessel, technology) pair may have an uptake Curve with age on the x-axis,
    queried via interpolation at each increment's age. Shares exceeding what the
    cumulative packages can represent are truncated, with one warning per vessel.

    Parameters
    ----------
    fleet
        Fleet owning the vessel.
    vessel
        Vessel to seed the initial uptake for.
    vessel_idx
        Index of `vessel` in `fleet.vessels`.
    """
    vessel_name = vessel.name
    truncation_count = 0
    truncated_tech_names = set()

    # seeded uptake is charged as if installed at build (consistent with the
    # hull, which the instantaneous freight rate charges at full newbuild cost)
    package_rates = calculate_package_charter_rates(
        fleet.technology_packages, fleet.package_cost_flows, vessel
    )

    for inc in fleet.increments[vessel_idx]:
        shares = np.zeros(len(fleet.technologies))
        for t, tech in enumerate(fleet.technologies):
            curve = fleet.initial_technology_share.get((vessel_name, tech.name))
            if curve is not None:
                shares[t] = curve.get(inc.age)

        package_mix, truncated = _shares_to_package_mix(
            fleet.technologies, fleet.technology_packages, shares
        )
        inc.package_uptake[:] = package_mix
        inc.technology_charter_rate = float(np.dot(package_mix, package_rates))

        if truncated:
            truncation_count += 1
            truncated_tech_names |= truncated

    if truncation_count > 0:
        techs = ", ".join(sorted(truncated_tech_names))

        logger.warning(
            "Truncated initial technology shares for vessel '%s' across %d age "
            "increment(s): %s",
            vessel_name,
            truncation_count,
            techs,
        )


def _shares_to_package_mix(
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
    tech_to_idx = {t: i for i, t in enumerate(technologies)}
    tech_names = [t.name for t in technologies]

    remaining = shares.astype(float, copy=True)
    pkg_shares = np.zeros(len(packages), dtype=float)

    for p in range(len(packages) - 1, 0, -1):
        pkg = packages[p]
        idxs = [tech_to_idx[t] for t in pkg.technologies]
        take = remaining[idxs].min()
        if take > 0:
            pkg_shares[p] = take
            remaining[idxs] -= take

    truncated_techs = {
        name for name, val in zip(tech_names, remaining, strict=True) if val > 0
    }

    pkg_shares[0] = 1.0 - pkg_shares[1:].sum()
    return pkg_shares, truncated_techs


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
