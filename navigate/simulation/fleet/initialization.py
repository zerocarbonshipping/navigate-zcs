# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""One-time initialization of the existing fleets at simulation start."""

from __future__ import annotations

import itertools
import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.increment import VesselIncrement
from navigate.simulation.cohort import split_by_age
from navigate.simulation.fleet._composition import extract_cargo_miles, get_counts
from navigate.simulation.fleet._package import (
    build_empty_package_uptake,
    build_technology_packages,
    calculate_package_charter_rates,
    update_packages,
)
from navigate.simulation.fleet.expectation import calculate_fleet_evolution_expectation
from navigate.simulation.fleet.technology_adoption import (
    transfer_technology_charter_rate,
)
from navigate.simulation.fleet.technology_effect import update_residual_energy_demand
from navigate.util import calculate_compound_growth, subtract

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
        Simulation timeline, in years.
    """
    idx = 0
    start = timeline[idx]

    # build the technology packages and anchor their cost flows at the start;
    # this must precede seeding the initial technology uptake, which levelizes
    # the cost flows into the carried technology charter rate
    fleet.technology_packages = build_technology_packages(fleet.technologies)
    update_packages(fleet.technology_packages, fleet.package_cost_flows, start)

    n_packages = fleet.get_number_of_packages()
    fleet.newbuild_package_uptake = [
        build_empty_package_uptake(n_packages) for _ in fleet.vessels
    ]
    fleet.orders_delivered = np.zeros(len(fleet.vessels))
    fleet.orders_postponed = np.zeros(len(fleet.vessels))
    fleet.fuel_conversion_expenses = np.zeros_like(timeline)

    # the initial split of the existing fleet need not match the current newbuild
    # trend, but it is the best available proxy for it
    # TODO: allow this to be user-defined
    fleet.current_uptake = np.array(fleet.initial_split)

    fleet.increments = _build_initial_increments(fleet, start)
    _seed_initial_uptake(fleet, start)
    _define_initial_trade(fleet, timeline)

    update_residual_energy_demand(fleet, idx)

    fleet.expectation.uptakes[:, idx] = fleet.current_uptake
    calculate_fleet_evolution_expectation(fleet, timeline, idx, scrapping_pending=False)

    transfer_technology_charter_rate(fleet, idx)


def _build_initial_increments(
    fleet: Fleet, start: float
) -> list[list[VesselIncrement]]:
    """
    Build the initial increments of every vessel type from its initial count.

    Each type's age bins come from its own distribution, so bins of one age can lie
    a rounding residual apart between types. They are given one entry time and one
    span, so that consolidation, which compares vintages exactly, takes them as one.

    Parameters
    ----------
    fleet
        Fleet whose initial vessels are split.
    start
        Start time of the simulation, in years.

    Returns
    -------
    list[list[VesselIncrement]]
        The increments of each vessel type, oldest first.
    """
    vessel_count = len(fleet.vessels)
    increments = [
        _build_vessel_increments(fleet, v, start) for v in range(vessel_count)
    ]
    initial = list(itertools.chain.from_iterable(increments))

    entries = _align_residuals([increment.entered for increment in initial])
    spans = _align_residuals([increment.age_span for increment in initial])

    for increment, entered, span in zip(initial, entries, spans, strict=True):
        increment.entered = entered
        increment.age_span = span

    return increments


def _align_residuals(values: list[float]) -> list[float]:
    """
    Replace each value by the smallest of those within a residual of it.

    A value is compared to the first of its group, not the value before it, so that a
    group cannot drift.
    """
    aligned = list(values)
    anchor = 0.0

    for position, i in enumerate(np.argsort(values)):
        if position == 0 or subtract(anchor, values[i]) != 0.0:
            anchor = values[i]

        aligned[i] = anchor

    return aligned


def _build_vessel_increments(
    fleet: Fleet, vessel_idx: int, start: float
) -> list[VesselIncrement]:
    """
    Build the initial increments of one vessel type, one per age bin.

    Where the type's initial age distribution is a number, its vessels are spread
    evenly over its initial age range. The vessels carry the attributes of the first
    time step, as the model holds none from before it.

    Parameters
    ----------
    fleet
        Fleet the vessels belong to.
    vessel_idx
        Index of the vessel type in the fleet.
    start
        Start time of the simulation, in years.

    Returns
    -------
    list[VesselIncrement]
        The increments of the type, oldest first.
    """
    vessel = fleet.vessels[vessel_idx]
    total_count = fleet.initial_split[vessel_idx] * fleet.initial_vessels.get()
    distribution = fleet.initial_age_distribution[vessel_idx]
    age_range = _calculate_initial_age_range(fleet, vessel)
    n_packages = fleet.get_number_of_packages()

    # a NaN count, such as from an expression dividing by zero, builds no cohorts
    if not total_count > 0.0:
        return []

    increments: list[VesselIncrement] = []
    for age, span, count in split_by_age(total_count, distribution, age_range):
        increment = VesselIncrement(
            count=count,
            entered=start - float(age),
            age_span=float(span),
            origin=0,
            package_uptake=build_empty_package_uptake(n_packages),
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


def _seed_initial_uptake(fleet: Fleet, start: float) -> None:
    """
    Seed the initial package uptake of every vessel type from its technology shares.

    Without any share the increments keep the empty package they were built with.

    Parameters
    ----------
    fleet
        Fleet whose increments are seeded.
    start
        Start time of the simulation, in years.
    """
    if all(share is None for share in fleet.initial_technology_shares.values()):
        return

    for v in range(len(fleet.vessels)):
        _seed_vessel_uptake(fleet, v, start)


def _seed_vessel_uptake(fleet: Fleet, vessel_idx: int, start: float) -> None:
    """
    Seed one vessel's age-dependent initial package mix and carried technology charge.

    Each (vessel, technology) pair may have an uptake Curve with age on the x-axis.
    Each vessel of an increment takes the package mix its shares give at its own age,
    and the increment the mix averaged over its age span. Shares exceeding what the
    cumulative packages can represent are truncated, with one warning per vessel.

    Parameters
    ----------
    fleet
        Fleet the vessel belongs to.
    vessel_idx
        Index of the vessel type in the fleet.
    start
        Start time of the simulation, in years.
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
        # an empty increment, such as an age distribution's oldest bin at a share of
        # zero, has no vessel to read a share at, and keeps the empty package
        if increment.count <= 0.0:
            continue

        ages = _sample_vessel_ages(increment, start)
        shares = _get_initial_shares(fleet, vessel, ages)
        package_mix, truncated = _calculate_package_mix(technologies, packages, shares)
        package_uptake = package_mix.mean(axis=0)

        increment.package_uptake = package_uptake
        increment.technology_charter_rate = float(np.dot(package_uptake, package_rates))

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


def _sample_vessel_ages(increment: VesselIncrement, start: float) -> FloatArray:
    """
    Return ages spread evenly over the ages an increment's vessels hold at the start.

    The ages are the midpoints of equal parts of the held ages, over which the vessels
    are spread uniformly, so the mean of a quantity at these ages is its average over
    the vessels by the midpoint rule. No age lies on an end of the held ages.

    Parameters
    ----------
    increment
        Increment whose vessels are sampled.
    start
        Start time of the simulation, in years.

    Returns
    -------
    FloatArray
        Ages of the sampled vessels, in years, youngest first.
    """
    # the mean over a hundred parts is exact where a quantity is linear within each
    # part, and misses a jump inside the span by at most half a percent of it
    parts = 100
    youngest = increment.youngest_age(start)

    return youngest + increment.age_span * (np.arange(parts) + 0.5) / parts


def _get_initial_shares(fleet: Fleet, vessel: Vessel, ages: FloatArray) -> FloatArray:
    """
    Return the initial uptake share of each technology of a vessel at each age.

    Parameters
    ----------
    fleet
        Fleet the vessel belongs to.
    vessel
        Vessel type the shares apply to.
    ages
        Ages of the vessels, in years.

    Returns
    -------
    FloatArray
        Uptake share of each technology, fraction, one row per age and one column per
        technology; zero where no share is set.
    """
    shares = np.zeros((len(ages), len(fleet.technologies)))

    for t, technology in enumerate(fleet.technologies):
        share = fleet.initial_technology_shares[(vessel.name, technology.name)]
        if share is not None:
            shares[:, t] = share.get(ages)

    return shares


def _calculate_package_mix(
    technologies: list[Technology],
    packages: list[TechnologyPackage],
    shares: FloatArray,
) -> tuple[FloatArray, set[str]]:
    """
    Convert per-technology shares into per-package shares, one row per age.

    Allocates greedily to larger packages first, then puts the remainder
    into the empty package.

    Parameters
    ----------
    technologies
        Technologies the shares refer to.
    packages
        Packages sorted by size, the empty package at index 0.
    shares
        Uptake share of each technology, fraction, one row per age and one column
        per technology.

    Returns
    -------
    FloatArray
        Share of each package, fraction, one row per age and one column per package.
    set[str]
        Names of the technologies whose shares were truncated at any age.
    """
    index = {technology: i for i, technology in enumerate(technologies)}
    remaining = shares.copy()
    package_shares = np.zeros((len(shares), len(packages)))

    for p in reversed(range(1, len(packages))):
        indices = [index[technology] for technology in packages[p].technologies]
        share = remaining[:, indices].min(axis=1)
        package_shares[:, p] = share
        remaining[:, indices] -= share[:, np.newaxis]

    package_shares[:, 0] = 1.0 - package_shares[:, 1:].sum(axis=1)
    truncated_indices = np.flatnonzero((remaining > 0).any(axis=0))
    truncated = {technologies[i].name for i in truncated_indices}

    return package_shares, truncated


def _define_initial_trade(fleet: Fleet, timeline: FloatArray) -> None:
    """
    Project the fleet's trade over the timeline by compound growth from its start.

    Parameters
    ----------
    fleet
        Fleet to define the trade for.
    timeline
        Simulation timeline, in years.
    """
    idx = 0
    counts = get_counts(fleet)
    cargo_miles = extract_cargo_miles(fleet.vessels, idx)
    growth_rate = fleet.trade_growth.get

    initial_trade = np.dot(counts, cargo_miles)
    fleet.trade = calculate_compound_growth(initial_trade, growth_rate, timeline)
    fleet.results.trade[idx] = fleet.trade[idx]
