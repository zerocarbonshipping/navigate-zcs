# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Technology adoption on the existing fleet and on newbuilds.

Technologies are CAPEX-sorted into cumulative packages (``build_technology_packages``); the
package is the unit of choice. ``perform_technology_installation`` runs four phases per fleet
and time-step:

1. ``_propose_newbuild_uptake`` / ``_propose_retrofits`` — unconstrained MNL choices per vessel.
2. ``reconcile_retrofit_technology_caps`` — scale the retrofit proposals against the caps.
3. ``_apply_retrofits`` — mutate per-increment uptake and the carried charge.
4. ``transfer_retrofit_uptake`` / ``transfer_technology_charter_rate`` — profile writes.

The retrofit phases communicate through ``_RetrofitProposal`` objects. Newbuild uptake is
reconciled later, in ``perform_fleet_evolution`` (``reconcile_newbuild_technology_caps``), once
newbuild counts per vessel type are known; the reconciled shares reach the profile there.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from navigate.core.enum_ import EnergyDemandTypeID, EnergyDemandTypePortID, UtilityID
from navigate.core.node import Node
from navigate.core.nodes.technology import Technology
from navigate.core.nodes.vessel import Vessel
from navigate.economics.decision import calculate_asset_shares
from navigate.economics.flows import timeline_to_yearly
from navigate.fleet.marginal_saving import calculate_marginal_technology_saving
from navigate.fleet.operation import convert_to_regional_steps, transfer_operational_saving_to_vessels
from navigate.fleet.package import (
    Package,
    annual_costs_for_retrofit_steps,
    levelize_package_cost,
    npv_for_newbuilds,
    npv_for_retrofit_steps,
    preprocess_packages,
)
from navigate.fleet.residual_energy import calculate_residual_energy
from navigate.fleet.utils import get_remaining_lifetime, is_retrofit_cycle, net_energy_from_raw
from navigate.util import TOLERANCE, YEAR, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.increment import Increment
    from navigate.core.nodes.fleet import Fleet

logger = logging.getLogger(__name__)


@dataclass
class _AdoptionBasis:
    """Per-vessel invariants of one technology-adoption pass (newbuild choice and retrofit proposing)."""

    vessel: Vessel
    vessel_idx: int                    # index into fleet.assets and fleet.increments
    packages_saving: list[np.ndarray]  # marginal-saving cash flow per package

    # adoption-decision rate: technology cost of capital, falling back to the vessel's
    discount_rate: float

    # vessel cost of capital: levelizes the carried retrofit charge for consistency with the
    # freight-rate NPVs; the adoption decision keeps the technology rate
    vessel_discount_rate: float

    capex_npv: float                   # summed ship CAPEX NPV, non-dimensionalizes the NPVs in the DCM


@dataclass
class _RetrofitProposal:
    """Unconstrained MNL retrofit jumps for the eligible share of one (vessel, increment, package) cohort."""

    # index into fleet.assets; groups proposals per vessel in the transfer
    vessel_idx: int

    # age cohort whose package_uptake the apply step mutates; safe to hold, as nothing mutates
    # the fleet.increments list structure between propose and transfer (list mutation lives in
    # perform_fleet_evolution)
    increment: Increment

    # package the eligible share currently sits at
    package_idx: int

    # MNL shares over retrofit steps: choices[0] is stay, choices[k] jumps to package_idx + k;
    # rescaled in place by the cap reconciliation
    choices: np.ndarray

    # share of the increment sitting at package_idx at propose time; equals the live value at
    # apply time because proposals apply in decreasing package order (earlier applies only add
    # to higher packages)
    eligible_share: float

    # levelized yearly charge per retrofit step, USD/year per vessel
    annual_costs: np.ndarray

    @property
    def eligible_count(self) -> float:
        """Number of vessels able to make this jump."""
        return float(self.increment.multiplier) * self.eligible_share

    def first_adopting_step(self, technology_idx: int) -> int:
        """
        First choice step whose target package contains the technology at `technology_idx`
        (CAPEX-sorted order). May exceed the number of steps; callers guard.
        """
        return technology_idx - self.package_idx + 1


@dataclass
class _CapContribution:
    """One share vector's contribution to a technology's cap aggregate."""

    shares: np.ndarray  # retrofit choices or newbuild uptake; tail scaled in place when the cap binds
    start: int          # first index adopting the capped technology
    weight: float       # vessels behind the vector: eligible_count (retrofit) or newbuild count

    # sum of shares[start:], cached at construction and reused by the scale pass
    adopting_share: float = field(init=False)

    def __post_init__(self) -> None:
        self.adopting_share = float(np.sum(self.shares[self.start:]))


@dataclass
class _TechnologyEffect:
    """Uptake-weighted technology effect on one vessel type, accumulated over (increment, package) pairs."""

    saving_sea: dict[EnergyDemandTypeID, np.ndarray]       # weighted saving per leg: operational minus residual
    saving_port: dict[EnergyDemandTypePortID, np.ndarray]  # weighted saving per port call
    weight: float = 0.                                     # total uptake weight, normalizes the averages
    shore_capacity: float = 0.                             # weighted shore-power capacity


def build_technology_packages(technologies: list[Technology]
                              ) -> tuple[list[Package], dict[int, int]]:
    """
    Sort technologies by CAPEX and organize them into cumulative packages, from empty to full,
    with a map from package index to the technology index in the original list.

    Parameters
    ----------
    technologies
        List of technologies to organize into packages.

    Returns
    -------
    Tuple of (packages, package_to_technology_map).
    """

    sorted_pairs = sorted(enumerate(technologies), key=lambda p: p[1].capex.get())
    sorted_techs = [t for _, t in sorted_pairs]
    packages = [Package(sorted_techs[:i]) for i in range(len(sorted_techs) + 1)]
    package_to_technology_map = {i: sorted_pairs[i - 1][0] for i in range(1, len(sorted_pairs) + 1)}

    return packages, package_to_technology_map


def calculate_package_charter_rates(packages: list[Package], vessel: Vessel) -> np.ndarray:
    """
    Levelized USD/year charge per package for an install at build, over the vessel lifetime.

    Levelized at the vessel cost of capital so the charge is consistent with the
    freight-rate NPVs it feeds; the adoption decision keeps its own discount rate.

    Parameters
    ----------
    packages
        All technology packages (from empty to full), with cost flows computed
        by ``preprocess_packages``.
    vessel
        Vessel whose lifetime and cost of capital govern the levelization.

    Returns
    -------
    np.ndarray
        Constant yearly charge per package, USD/year.
    """

    lifetime = vessel.lifetime.get()
    discount_rate = vessel.cost_of_capital.get()

    return np.array([levelize_package_cost(pkg.cost_flow, lifetime, discount_rate)
                     for pkg in packages])


def define_initial_technology(fleet: Fleet) -> None:
    """
    Initialize the technology-adoption storage for the fleet and seed each vessel's initial
    package uptake (see `_seed_vessel_initial_uptake`).

    Parameters
    ----------
    fleet
        The fleet to initialize technology for.
    """

    n_pkgs = len(fleet.technologies) + 1
    n_vessels = len(fleet.assets)

    fleet.newbuild_package_uptake = [np.zeros(n_pkgs, dtype=float) for _ in range(n_vessels)]

    # initialize package_uptake on each increment
    for v in range(n_vessels):
        for inc in fleet.increments[v]:
            inc.package_uptake = np.zeros(n_pkgs, dtype=float)

    if not any(isinstance(v, Node) for v in fleet.initial_technology_share.values()):
        return

    for v, vessel in enumerate(fleet.assets):
        _seed_vessel_initial_uptake(fleet, vessel, v)


def _seed_vessel_initial_uptake(fleet: Fleet, vessel: Vessel, vessel_idx: int) -> None:
    """
    Seed one vessel's age-dependent initial package mix and carried technology charge.

    Each (vessel, technology) pair may have an uptake Curve with age on the x-axis, queried via
    interpolation at each increment's age. Shares exceeding what the cumulative packages can
    represent are truncated, with one warning per vessel.

    Parameters
    ----------
    fleet
        The fleet owning the vessel.
    vessel
        The vessel to seed initial uptake for.
    vessel_idx
        Index of `vessel` in `fleet.assets`.
    """

    vessel_name = vessel.name
    truncation_count = 0
    truncated_tech_names = set()

    # seeded uptake is charged as if installed at build (consistent with the
    # hull, which the instantaneous freight rate charges at full newbuild cost)
    package_rates = calculate_package_charter_rates(fleet.technology_packages, vessel)

    for inc in fleet.increments[vessel_idx]:

        # build per-technology shares for this increment's age
        shares = np.zeros(len(fleet.technologies))
        for t, tech in enumerate(fleet.technologies):
            curve = fleet.initial_technology_share.get((vessel_name, tech.name))
            if isinstance(curve, Node):
                shares[t] = curve.get(inc.age)

        package_mix, truncated = _shares_to_package_mix(
            fleet.technologies, fleet.technology_packages, shares)
        inc.package_uptake[:] = package_mix
        inc.technology_charter_rate = float(np.dot(package_mix, package_rates))

        if truncated:
            truncation_count += 1
            truncated_tech_names |= truncated

    if truncation_count > 0:
        techs = ", ".join(sorted(truncated_tech_names))

        logger.warning(
            "Truncated initial technology shares for vessel '%s' across %d age increment(s): %s",
            vessel_name, truncation_count, techs,
        )


def _shares_to_package_mix(technologies: list[Technology],
                           packages: list[Package],
                           shares: np.ndarray
                           ) -> tuple[np.ndarray, set[str]]:
    """
    Convert per-technology shares into per-package shares by greedily allocating
    to larger packages first, then putting remainder into the empty package.

    Parameters
    ----------
    technologies
        List of technologies corresponding to the shares array.
    packages
        List of packages (sorted by size, empty package at index 0).
    shares
        Per-technology uptake shares.

    Returns
    -------
    Tuple of (package mix array, set of truncated technology names).
    """

    tech_to_idx = {t: i for i, t in enumerate(technologies)}
    tech_names = [t.name for t in technologies]

    remaining = shares.astype(float, copy=True)
    pkg_shares = np.zeros(len(packages), dtype=float)

    # allocate from largest package to smallest, skipping empty package at index 0
    for p in range(len(packages) - 1, 0, -1):
        pkg = packages[p]
        idxs = [tech_to_idx[t] for t in pkg]
        take = remaining[idxs].min()
        if take > 0:
            pkg_shares[p] = take
            remaining[idxs] -= take

    truncated_techs = {name for name, val in zip(tech_names, remaining) if val > 0}

    # empty package gets whatever makes the total sum to 1
    pkg_shares[0] = 1. - pkg_shares[1:].sum()
    return pkg_shares, truncated_techs


def _calculate_packages_saving(vessel: Vessel,
                               packages: list[Package],
                               timeline: NDArray[np.float64],
                               idx: int
                               ) -> list[NDArray[np.float64]]:
    """
    Calculate the marginal energy saving for each technology package.

    Parameters
    ----------
    vessel
        The vessel to calculate savings for.
    packages
        The list of technology packages.
    timeline
        Simulation timeline.
    idx
        Current time-step index.

    Returns
    -------
    List of saving arrays, one per package.
    """

    idx_ = np.s_[idx:]
    times = timeline[idx_]

    time_flow = timeline_to_yearly(vessel, idx, timeline)

    savings = []
    for package in packages:
        saving = calculate_marginal_technology_saving(vessel, package, idx_)
        savings.append(np.interp(time_flow, times, saving))

    return savings


def perform_technology_installation(fleet: Fleet,
                                    timeline: np.ndarray,
                                    time_step: float,
                                    idx: int
                                    ) -> None:
    """
    Perform technology installation for all vessels in the fleet, running the phases described
    in the module docstring.

    Parameters
    ----------
    fleet
        The fleet to perform technology installation for.
    timeline
        Simulation timeline.
    time_step
        Current time-step size.
    idx
        Current time-step index.
    """

    if not fleet.technologies:
        return

    preprocess_packages(fleet.technology_packages, fleet.assets, timeline[idx])

    if not fleet.technology_cost_of_capital:
        logger.warning(f"No technology cost of capital supplied for {fleet}, using vessel cost of capital."
                       f" This will likely lead to a higher uptake of technologies.")

    # Pre-newbuild fleet count: denominator for both retrofit and newbuild-technology caps.
    multipliers_total = float(sum(fleet.get_multipliers()))

    proposals = []
    for v, vessel in enumerate(fleet.assets):
        basis = _extract_adoption_basis(fleet, vessel, v, timeline, idx)
        fleet.newbuild_package_uptake[v] = _propose_newbuild_uptake(fleet, basis)
        proposals += _propose_retrofits(fleet, basis, time_step)

    reconcile_retrofit_technology_caps(fleet, proposals, time_step, multipliers_total)
    _apply_retrofits(proposals)
    transfer_retrofit_uptake(fleet, proposals, idx)

    # transfer the fleet-average carried technology charge before the cargo
    # charter reads it later in the same timestep
    transfer_technology_charter_rate(fleet, idx)


def _extract_adoption_basis(fleet: Fleet,
                            vessel: Vessel,
                            vessel_idx: int,
                            timeline: NDArray[np.float64],
                            idx: int
                            ) -> _AdoptionBasis:
    """
    Bundle the per-vessel invariants of one technology-adoption pass.

    Parameters
    ----------
    fleet
        The fleet owning the vessel.
    vessel
        Vessel type the basis is built for.
    vessel_idx
        Index of `vessel` in `fleet.assets`.
    timeline
        Simulation timeline.
    idx
        Current time-step index.

    Returns
    -------
    The basis bundle.
    """

    if fleet.technology_cost_of_capital:
        discount_rate = fleet.technology_cost_of_capital.get()
    else:
        discount_rate = vessel.cost_of_capital.get()

    packages_saving = _calculate_packages_saving(vessel, fleet.technology_packages, timeline, idx)

    # NPV is non-dimensionalized by the summed ship CAPEX so the sensitivity is unit-free.
    capex_npv = vessel.expectation.get_capex_npv(idx)

    return _AdoptionBasis(vessel, vessel_idx, packages_saving, discount_rate,
                          vessel.cost_of_capital.get(), capex_npv)


def _propose_newbuild_uptake(fleet: Fleet, basis: _AdoptionBasis) -> np.ndarray:
    """
    Unconstrained MNL choice over newbuild packages for one vessel type.

    Reconciled against the per-technology caps later in ``perform_fleet_evolution``
    (``reconcile_newbuild_technology_caps``), once newbuild counts per vessel type are known.

    Parameters
    ----------
    fleet
        The fleet owning the vessel.
    basis
        Per-vessel invariants of the adoption pass.

    Returns
    -------
    MNL share vector over newbuild packages.
    """

    npv = npv_for_newbuilds(basis.packages_saving, fleet.technology_packages, basis.discount_rate)
    choices, msg = calculate_asset_shares(npv, UtilityID.SIGNED_REFERENCE,
                                          fleet.technology_sensitivity.get(), reference=basis.capex_npv)

    if msg:
        logger.warning("%s newbuild technology uptake for %s %s", fleet, basis.vessel, msg)

    return choices


def _propose_retrofits(fleet: Fleet,
                       basis: _AdoptionBasis,
                       time_step: float
                       ) -> list[_RetrofitProposal]:
    """
    Walk every (age-increment, package) pair of the basis vessel and propose unconstrained MNL
    retrofit jumps; the reconciler downstream scales them against the per-technology caps.

    Parameters
    ----------
    fleet
        The fleet owning the vessel.
    basis
        Per-vessel invariants of the adoption pass.
    time_step
        Current time-step size in dateline units.

    Returns
    -------
    One proposal per (age-increment, package) pair with vessels eligible to move, in decreasing
    package order — the order `_apply_retrofits` relies on.
    """

    vessel = basis.vessel
    n_packages = len(fleet.technology_packages)

    retrofit_frequency = fleet.retrofit_frequency.get()
    technology_sensitivity = fleet.technology_sensitivity.get()
    dt_years = time_step / YEAR

    proposals = []

    for package_idx in range(n_packages - 1, -1, -1):
        for inc in fleet.increments[basis.vessel_idx]:

            if not is_retrofit_cycle(inc.age, retrofit_frequency, dt_years):
                continue

            remaining = get_remaining_lifetime(vessel, inc.age, inc.dt)
            if remaining <= 0:
                continue

            eligible_share = float(inc.package_uptake[package_idx])
            if eligible_share <= 0.:
                continue

            npv = npv_for_retrofit_steps(package_idx, basis.packages_saving,
                                         fleet.technology_packages, remaining, basis.discount_rate)
            choices, _ = calculate_asset_shares(npv, UtilityID.SIGNED_REFERENCE,
                                                technology_sensitivity, reference=basis.capex_npv)
            annual_costs = annual_costs_for_retrofit_steps(package_idx, fleet.technology_packages,
                                                           remaining, basis.vessel_discount_rate)
            proposals.append(_RetrofitProposal(basis.vessel_idx, inc, package_idx,
                                               choices, eligible_share, annual_costs))

    return proposals


def reconcile_retrofit_technology_caps(fleet: Fleet,
                                       proposals: list[_RetrofitProposal],
                                       time_step: float,
                                       multipliers_total: float) -> None:
    """
    Scale per-proposal retrofit `choices` so that, for every technology, the aggregate count of
    retrofits adopting it this timestep does not exceed `limit · multipliers_total · time_step / YEAR`.

    The cap aggregate weights each proposal's tail-sum by its `eligible_count`, matching the count
    `_apply_retrofits` will produce. Displaced mass moves to the stay option (see
    `_scale_tails_to_cap`).

    Iterates technologies from outermost to innermost in the CAPEX-sorted package order. Scaling a
    single proposal's tail (`choices[k_start:]`) reduces retrofits for *all* technologies introduced
    by those steps, so processing the outer technologies first keeps the inner-technology aggregates
    monotonic.

    Parameters
    ----------
    fleet
        The fleet whose retrofit caps are being enforced.
    proposals
        Output of `_propose_retrofits`. Mutated in place: each proposal's `choices` vector is
        rescaled when one of the technologies it covers has a binding cap.
    time_step
        Current time-step size; combined with `YEAR` to convert per-year limits into per-step caps.
    multipliers_total
        Sum of pre-newbuild fleet multipliers — the denominator for the per-technology cap
        (`cap = limit · multipliers_total · time_step / YEAR`).
    """

    if multipliers_total <= 0. or not proposals or not fleet.technology_packages:
        return

    sorted_technologies = fleet.technology_packages[-1].technologies
    if not sorted_technologies:
        return

    budget = multipliers_total * (time_step / YEAR)

    for i in range(len(sorted_technologies) - 1, -1, -1):
        technology_name = sorted_technologies[i].name
        cap = fleet.retrofit_technology_limit[technology_name].get() * budget

        contributions = []
        for proposal in proposals:
            if proposal.package_idx > i:
                continue

            k_start = proposal.first_adopting_step(i)
            if k_start >= len(proposal.choices):
                continue

            contributions.append(_CapContribution(proposal.choices, k_start, proposal.eligible_count))

        _scale_tails_to_cap(contributions, cap)


def reconcile_newbuild_technology_caps(fleet: Fleet,
                                       increments: np.ndarray,
                                       time_step: float,
                                       multipliers_total: float) -> None:
    """
    Scale `fleet.newbuild_package_uptake` so that, for every technology, the aggregate count of
    newbuild installs of it this timestep does not exceed
    `limit · multipliers_total · time_step / YEAR`.

    Iterates technologies from outermost to innermost in the CAPEX-sorted package order, mirroring
    the retrofit reconciliation. Displaced probability moves to the no-technology package (see
    `_scale_tails_to_cap`), preserving the invariant that each per-vessel uptake vector sums to 1.

    Parameters
    ----------
    fleet
        The fleet whose newbuild caps are being enforced.
    increments
        Per-vessel newbuild counts for the current timestep. Used to weight each vessel's
        contribution to the aggregate when checking the cap.
    time_step
        Current time-step size; combined with `YEAR` to convert per-year limits into per-step caps.
    multipliers_total
        Sum of pre-newbuild fleet multipliers — the denominator for the per-technology cap
        (`cap = limit · multipliers_total · time_step / YEAR`).
    """

    if multipliers_total <= 0. or not fleet.technology_packages:
        return

    sorted_technologies = fleet.technology_packages[-1].technologies
    if not sorted_technologies:
        return

    budget = multipliers_total * (time_step / YEAR)

    for i in range(len(sorted_technologies) - 1, -1, -1):
        technology_name = sorted_technologies[i].name
        cap = fleet.newbuild_technology_limit[technology_name].get() * budget
        k_start = i + 1

        contributions = []
        for v in range(len(fleet.assets)):
            uptake = fleet.newbuild_package_uptake[v]
            if k_start >= len(uptake) or increments[v] <= 0.:
                continue

            contributions.append(_CapContribution(uptake, k_start, float(increments[v])))

        _scale_tails_to_cap(contributions, cap)


def _scale_tails_to_cap(contributions: list[_CapContribution], cap: float) -> None:
    """
    Scale the adopting tails of the contributions so their weighted aggregate fits the cap.

    Model choice — where displaced mass goes
    ----------------------------------------
    When a cap binds, the displaced share of every contribution is moved to `shares[0]` (the
    "stay" / no-technology option), not to the nearest feasible package below. For a cumulative
    package list `[none, A, A+B]` with a binding cap on B, demand for `A+B` in excess of the cap
    is sent to `none`, even when A's own cap has slack — it is *not* reallocated to the `A`-only
    package. The package is the unit of choice in the DCM upstream; if decision makers ranked
    `A+B` highest and B is rationed, the model reads that as "defer this cycle" (retrofits) or
    "build without technology" (newbuilds) rather than "fall back to a package they did not pick".

    Parameters
    ----------
    contributions
        The share vectors adopting the capped technology, with cached tail sums.
    cap
        Maximum weighted aggregate of adopting shares this time-step.
    """

    aggregate = 0.
    for contribution in contributions:
        aggregate += contribution.weight * contribution.adopting_share

    if aggregate <= cap + TOLERANCE:
        return

    scale = cap / aggregate

    for contribution in contributions:
        contribution.shares[contribution.start:] *= scale
        contribution.shares[0] += (1. - scale) * contribution.adopting_share


def _apply_retrofits(proposals: list[_RetrofitProposal]) -> None:
    """
    Move each proposal's eligible uptake from its package level to the chosen higher ones.

    Each moved share also adds its levelized retrofit charge to the increment's carried
    `technology_charter_rate`, so the retrofit cost is recovered as a constant yearly
    charge over the remaining vessel lifetime it was levelized against.

    Proposals must arrive in decreasing package order (the order `_propose_retrofits` emits):
    each apply only adds to higher packages, so the live `uptake[package_idx]` read below still
    equals the `eligible_share` snapshot taken at propose time.

    Parameters
    ----------
    proposals
        Reconciled retrofit proposals, in propose order.
    """

    for proposal in proposals:

        increment = proposal.increment
        uptake = increment.package_uptake
        choices = proposal.choices
        annual_costs = proposal.annual_costs
        package_idx = proposal.package_idx

        current = uptake[package_idx]
        moved_total = np.sum(choices[1:])

        uptake[package_idx] = current * (1. - moved_total)

        for step in range(1, len(choices)):
            uptake[package_idx + step] += current * choices[step]
            increment.technology_charter_rate += current * choices[step] * annual_costs[step]


def transfer_retrofit_uptake(fleet: Fleet,
                             proposals: list[_RetrofitProposal],
                             idx: int) -> None:
    """
    Aggregate the per-(vessel, technology) retrofit count from the (already reconciled and
    applied) proposals and write it to the profile as a fraction of that vessel's existing
    multiplier.

    Layout matches `transfer_technology_uptake`: per-technology, per-vessel, per-step. The stored
    value is the share of vessel-type `v`'s existing fleet that retrofitted to `technology` this
    step, directly comparable to `set_retrofit_technology_limit · time_step / YEAR`.

    Parameters
    ----------
    fleet
        The fleet whose retrofit uptake is being recorded.
    proposals
        Reconciled and applied retrofit proposal list.
    idx
        Current time-step index, used for the profile write.
    """

    if not fleet.technology_packages or not proposals:
        return

    sorted_technologies = fleet.technology_packages[-1].technologies
    if not sorted_technologies:
        return

    retrofit_counts = {}
    for proposal in proposals:
        weight = proposal.eligible_count
        if weight <= 0.:
            continue

        for i in range(proposal.package_idx, len(sorted_technologies)):
            k_start = proposal.first_adopting_step(i)
            if k_start >= len(proposal.choices):
                break

            # `choices` is post-reconciliation post-application; the tail-sum has not been mutated
            # by `_apply_retrofits` because that function only reads choices and rewrites the
            # per-increment package_uptake — the proposal vector itself is preserved.
            key = (proposal.vessel_idx, i)
            retrofit_counts[key] = (retrofit_counts.get(key, 0.)
                                    + weight * float(np.sum(proposal.choices[k_start:])))

    for v, vessel in enumerate(fleet.assets):
        multipliers_total = float(sum(inc.multiplier for inc in fleet.increments[v]))
        for i, technology in enumerate(sorted_technologies):
            count = retrofit_counts.get((v, i), 0.)
            share = divide_nonzero(count, multipliers_total)
            fleet.profile.set_retrofit_technology_uptake(idx, vessel.name, technology.name, share)


def transfer_technology_charter_rate(fleet: Fleet, idx: int) -> None:
    """
    Transfer the fleet-average carried technology charge to each vessel's expectation and profile.

    The average is the multiplier-weighted mean of the per-increment carried charges, in USD/year
    per vessel. It feeds the investment freight rate within the same timestep (the cargo charter
    runs after technology installation) and accumulates on the profile as the realized series the
    instantaneous freight rate is post-processed from.

    Parameters
    ----------
    fleet
        The fleet whose carried charges are aggregated.
    idx
        Current time-step index.
    """

    for v, vessel in enumerate(fleet.assets):

        total = 0.
        weight = 0.
        for inc in fleet.increments[v]:
            total += inc.multiplier * inc.technology_charter_rate
            weight += inc.multiplier

        average = divide_nonzero(total, weight)

        vessel.expectation.set_technology_charter_rate(idx, average)
        vessel.profile.set_technology_cost(idx, average)


def transfer_technology_uptake(fleet: Fleet, idx: int) -> None:
    """
    Transfer technology uptake data to the fleet profile.

    Parameters
    ----------
    fleet
        The fleet to transfer uptake data for.
    idx
        Current time-step index.
    """

    for v, vessel in enumerate(fleet.assets):
        for p, _package in enumerate(fleet.technology_packages[1:], start=1):

            t = fleet.package_to_technology_map[p]
            technology = fleet.technologies[t]

            # transfer newbuild uptake
            nb_uptake = np.sum(fleet.newbuild_package_uptake[v][p:])
            fleet.profile.set_newbuild_technology_uptake(idx, vessel.name, technology.name, nb_uptake)

            # transfer average fleet uptake
            avg_uptake = 0.
            weight = 0.
            for inc in fleet.increments[v]:
                inc_uptake = float(np.sum(inc.package_uptake[p:]))
                avg_uptake += inc_uptake * inc.multiplier
                weight += inc.multiplier

            avg_uptake = divide_nonzero(avg_uptake, weight)
            fleet.profile.set_technology_uptake(idx, vessel.name, technology.name, avg_uptake)


def update_residual_energy_demand(fleet: Fleet, idx: int) -> None:
    """
    Update the residual energy demand for all vessels after technology installation.

    Parameters
    ----------
    fleet
        The fleet to update residual energy demand for.
    idx
        Current time-step index.
    """

    # Transfer fleet-level operational savings to each vessel expectation
    transfer_operational_saving_to_vessels(fleet)

    for v, vessel in enumerate(fleet.assets):
        op_sea, op_port = _apply_operational_savings(vessel, idx)

        # Pre-compute arrays for use in saving/residual calculations
        op_sea_arr = {d: np.asarray(op_sea[d], dtype=float) for d in EnergyDemandTypeID}
        op_port_arr = {d: np.asarray(op_port[d], dtype=float) for d in EnergyDemandTypePortID}

        effect = _accumulate_technology_effect(fleet, v, vessel, op_sea_arr, op_port_arr, idx)
        _transfer_residual_energy(vessel, op_sea_arr, op_port_arr, effect, idx)


def _apply_operational_savings(vessel: Vessel,
                               idx: int
                               ) -> tuple[dict[EnergyDemandTypeID, list[np.ndarray]],
                                          dict[EnergyDemandTypePortID, list[np.ndarray]]]:
    """
    Apply the operational saving fractions (zero-cost reductions: JIT, weather routing, etc.)
    to the vessel's raw energy demand and store the result on expectation and profile.

    Parameters
    ----------
    vessel
        The vessel to apply operational savings for.
    idx
        Current time-step index.

    Returns
    -------
    Tuple of (operational energy at sea per leg, operational energy in port per port call).
    """

    expectation = vessel.expectation

    raw_sea = expectation.get_raw_energy_sea(idx=idx)
    raw_port = expectation.get_raw_energy_port(idx=idx)

    saving_sea = expectation.get_operational_saving_fraction_sea()
    saving_port = expectation.get_operational_saving_fraction_port()

    op_sea = {d: [np.asarray(leg, dtype=float) * (1. - saving_sea[d])
                  for leg in raw_sea[d]]
              for d in EnergyDemandTypeID}
    op_port = {d: [np.asarray(port, dtype=float) * (1. - saving_port[d])
                   for port in raw_port[d]]
               for d in EnergyDemandTypePortID}

    vessel.expectation.set_operational_energy_sea(idx, op_sea)
    vessel.expectation.set_operational_energy_port(idx, op_port)

    vessel.profile.set_operational_energy_sea(
        idx, {d: float(np.sum(op_sea[d])) for d in EnergyDemandTypeID})
    vessel.profile.set_operational_energy_port(
        idx, {d: float(np.sum(op_port[d])) for d in EnergyDemandTypePortID})

    regional_op_sea = convert_to_regional_steps(vessel, op_sea)
    vessel.expectation.set_regional_operational_energy_sea(idx, regional_op_sea)

    return op_sea, op_port


def _accumulate_technology_effect(fleet: Fleet,
                                  vessel_idx: int,
                                  vessel: Vessel,
                                  op_sea_arr: dict[EnergyDemandTypeID, np.ndarray],
                                  op_port_arr: dict[EnergyDemandTypePortID, np.ndarray],
                                  idx: int
                                  ) -> _TechnologyEffect:
    """
    Accumulate the uptake-weighted technology effect over the vessel's (increment, package) pairs.

    Technology savings are computed relative to operational energy: saving = operational - residual.

    Parameters
    ----------
    fleet
        The fleet owning the increments and technology packages.
    vessel_idx
        Index of `vessel` in `fleet.assets`.
    vessel
        The vessel to accumulate the effect for.
    op_sea_arr
        Operational energy at sea per demand type, one array over legs.
    op_port_arr
        Operational energy in port per demand type, one array over ports.
    idx
        Current time-step index.

    Returns
    -------
    The accumulated effect.
    """

    route = vessel.route
    n_legs = route.get_number_of_legs()
    n_ports = route.get_number_of_ports()

    effect = _TechnologyEffect(
        {d: np.zeros(n_legs, dtype=float) for d in EnergyDemandTypeID},
        {d: np.zeros(n_ports, dtype=float) for d in EnergyDemandTypePortID},
    )

    for inc in fleet.increments[vessel_idx]:
        uptake = inc.package_uptake

        for p, package in enumerate(fleet.technology_packages):
            w = float(inc.multiplier) * float(uptake[p])
            if w <= 0.:
                continue

            residual_sea, residual_port = calculate_residual_energy(vessel, package, np.s_[idx])

            for demand, residual in residual_sea.items():
                effect.saving_sea[demand] += w * (op_sea_arr[demand] - np.asarray(residual, dtype=float))

            for demand, residual in residual_port.items():
                effect.saving_port[demand] += w * (op_port_arr[demand] - np.asarray(residual, dtype=float))

            effect.weight += w
            effect.shore_capacity += w * package.shore_power_capacity

    return effect


def _transfer_residual_energy(vessel: Vessel,
                              op_sea_arr: dict[EnergyDemandTypeID, np.ndarray],
                              op_port_arr: dict[EnergyDemandTypePortID, np.ndarray],
                              effect: _TechnologyEffect,
                              idx: int
                              ) -> None:
    """
    Average the accumulated technology effect and write shore power capacity and residual
    energy demand to the vessel's expectation and profile.

    Parameters
    ----------
    vessel
        The vessel to write results for.
    op_sea_arr
        Operational energy at sea per demand type, one array over legs.
    op_port_arr
        Operational energy in port per demand type, one array over ports.
    effect
        The accumulated technology effect.
    idx
        Current time-step index.
    """

    avg_shore_capacity = effect.shore_capacity / effect.weight if effect.weight > 0. else 0.
    vessel.expectation.set_shore_power_capacity(idx, avg_shore_capacity)

    # If there is no effective uptake/weight, leave residual = operational (no technology change)
    if effect.weight <= 0.:
        avg_residual_sea = op_sea_arr
        avg_residual_port = op_port_arr
    else:
        inv_w = 1. / effect.weight
        avg_residual_sea = {
            d: op_sea_arr[d] - effect.saving_sea[d] * inv_w
            for d in EnergyDemandTypeID
        }
        avg_residual_port = {
            d: op_port_arr[d] - effect.saving_port[d] * inv_w
            for d in EnergyDemandTypePortID
        }

    vessel.expectation.set_energy_sea(idx, avg_residual_sea)
    vessel.expectation.set_energy_port(idx, avg_residual_port)

    vessel.profile.set_energy_sea(idx, {d: float(arr.sum()) for d, arr in avg_residual_sea.items()})
    vessel.profile.set_energy_port(idx, {d: float(arr.sum()) for d, arr in avg_residual_port.items()})

    regional_sea = convert_to_regional_steps(vessel, avg_residual_sea)
    vessel.expectation.set_regional_energy_sea(idx, regional_sea)


def approximate_missing_technology(fleets: dict, idx: int) -> None:
    """
    Estimate energy-efficiency savings for fleets that cannot retrofit technologies from the
    fleet-average savings of those that can, and apply them to the energy demand at sea and
    in port of every fleet allowing the approximation.

    Costs are ignored in this calculation, so the costs of energy efficiency improvements
    are underestimated.

    Parameters
    ----------
    fleets
        Mapping of fleet name to fleet object.
    idx
        Current time-step index.
    """

    average_saving_sea, average_saving_port = _average_retrofit_savings(fleets, idx)

    for fleet in fleets.values():
        if fleet.can_retrofit() or not fleet.allow_technology_approximation:
            continue

        for vessel in fleet.vessels:
            _apply_approximated_saving(vessel, average_saving_sea, average_saving_port, idx)


def _average_retrofit_savings(fleets: dict,
                              idx: int
                              ) -> tuple[dict[EnergyDemandTypeID, float],
                                         dict[EnergyDemandTypePortID, float]]:
    """
    Energy-weighted average technology saving fractions over the retrofit-capable fleets.

    Parameters
    ----------
    fleets
        Mapping of fleet name to fleet object.
    idx
        Current time-step index.

    Returns
    -------
    Tuple of (average saving fraction at sea, average saving fraction in port), per demand type.
    """

    average_saving_sea = {energy: 0. for energy in EnergyDemandTypeID}
    average_saving_port = {energy: 0. for energy in EnergyDemandTypePortID}

    weight_sea = {k: 0.0 for k in average_saving_sea}
    weight_port = {k: 0.0 for k in average_saving_port}

    for fleet in fleets.values():
        if not fleet.can_retrofit():
            continue

        for v, vessel in enumerate(fleet.vessels):
            multiplier = fleet.get_multiplier(v)
            expectation = vessel.expectation

            raw_energy_sea = expectation.get_raw_energy_sea(idx=idx)
            raw_energy_port = expectation.get_raw_energy_port(idx=idx)
            savings_sea = expectation.get_energy_saving_sea(idx=idx)
            savings_port = expectation.get_energy_saving_port(idx=idx)

            _accumulate_energy_weighted_saving(raw_energy_sea, savings_sea, multiplier,
                                               average_saving_sea, weight_sea)
            _accumulate_energy_weighted_saving(raw_energy_port, savings_port, multiplier,
                                               average_saving_port, weight_port)

    for k in average_saving_sea:
        average_saving_sea[k] = (average_saving_sea[k] / weight_sea[k]) if weight_sea[k] else 0.0
    for k in average_saving_port:
        average_saving_port[k] = (average_saving_port[k] / weight_port[k]) if weight_port[k] else 0.0

    return average_saving_sea, average_saving_port


def _accumulate_energy_weighted_saving(raw_energy: dict,
                                       savings: dict,
                                       multiplier: float,
                                       saving_totals: dict,
                                       weight_totals: dict) -> None:
    """
    Accumulate one vessel's energy-weighted saving fractions into the running totals.

    Parameters
    ----------
    raw_energy
        Raw energy demand per demand type, one value per leg or port call; forms the
        accumulation weight together with `multiplier`.
    savings
        Saving fraction per demand type, one value per leg or port call.
    multiplier
        Number of vessels of this type.
    saving_totals
        Running weighted saving sums per demand type; updated in place.
    weight_totals
        Running weight sums per demand type; updated in place.
    """

    for k in saving_totals:
        for leg, raw in enumerate(raw_energy[k]):
            weight = raw * multiplier
            saving_totals[k] += savings[k][leg] * weight
            weight_totals[k] += weight


def _apply_approximated_saving(vessel: Vessel,
                               average_saving_sea: dict[EnergyDemandTypeID, float],
                               average_saving_port: dict[EnergyDemandTypePortID, float],
                               idx: int) -> None:
    """
    Apply the fleet-average saving fractions to one vessel's operational energy and store the
    net energy demand on expectation and profile.

    Parameters
    ----------
    vessel
        The vessel to apply the approximated savings to.
    average_saving_sea
        Average saving fraction at sea per demand type.
    average_saving_port
        Average saving fraction in port per demand type.
    idx
        Current time-step index.
    """

    op_sea = vessel.expectation.get_operational_energy_sea(idx=idx)
    op_port = vessel.expectation.get_operational_energy_port(idx=idx)

    sav_sea = {k: [average_saving_sea[k]] * len(op_sea[k])
               for k in average_saving_sea if k in op_sea}

    sav_port = {k: [average_saving_port[k]] * len(op_port[k])
                for k in average_saving_port if k in op_port}

    net_sea = net_energy_from_raw(op_sea, sav_sea)
    net_port = net_energy_from_raw(op_port, sav_port)
    regional_sea = convert_to_regional_steps(vessel, net_sea)

    vessel.expectation.set_energy_sea(idx, net_sea)
    vessel.expectation.set_energy_port(idx, net_port)
    vessel.expectation.set_regional_energy_sea(idx, regional_sea)

    vessel.profile.set_energy_sea(
        idx, {k: float(np.sum(net_sea[k])) for k in net_sea}
    )
    vessel.profile.set_energy_port(
        idx, {k: float(np.sum(net_port[k])) for k in net_port}
    )
