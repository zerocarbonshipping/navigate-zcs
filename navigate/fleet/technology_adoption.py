# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Technology adoption on the existing fleet and on newbuilds.

Technologies are CAPEX-sorted into cumulative packages (``build_technology_packages``);
the package is the unit of choice. ``perform_technology_installation`` runs four phases
per fleet and time-step:

1. ``_propose_newbuild_uptake`` and ``_propose_retrofits`` make the unconstrained MNL
   choices per vessel.
2. ``_reconcile_retrofit_technology_caps`` scales the retrofit proposals to the caps.
3. ``_apply_retrofits`` updates the per-increment uptake and the carried charge.
4. ``_transfer_retrofit_uptake`` and ``transfer_technology_charter_rate`` write the
   profile.

The retrofit phases communicate through ``_RetrofitProposal`` objects. Newbuild uptake
is reconciled later, in ``perform_fleet_evolution``
(``reconcile_newbuild_technology_caps``), once newbuild counts per vessel type are
known; the reconciled shares reach the profile there.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import EnergyDemandTypeID, EnergyDemandTypePortID, UtilityID
from navigate.core.technology_package import TechnologyPackage
from navigate.economics.decision import calculate_asset_shares
from navigate.economics.flows import timeline_to_yearly
from navigate.fleet.conversion import is_retrofit_cycle
from navigate.fleet.marginal_saving import calculate_marginal_technology_saving
from navigate.fleet.operation import (
    convert_to_regional_steps,
    transfer_operational_saving_to_vessels,
)
from navigate.fleet.package import (
    annual_costs_for_retrofit_steps,
    levelize_package_cost,
    npv_for_newbuilds,
    npv_for_retrofit_steps,
    preprocess_packages,
)
from navigate.fleet.residual_energy import (
    calculate_residual_energy,
    net_energy_from_raw,
)
from navigate.util import ROUND_OFF, TOLERANCE, YEAR, divide_nonzero

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from navigate.core.increment import VesselIncrement
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.technology import Technology
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.types_ import ForecastInput
    from navigate.util.types_ import FloatArray, FloatLike

logger = logging.getLogger(__name__)


@dataclass
class _AdoptionBasis:
    """
    Per-vessel invariants of one technology-adoption pass, newbuild and retrofit.

    Parameters
    ----------
    vessel
        Vessel type of the pass.
    vessel_idx
        Index of the vessel in ``fleet.assets`` and ``fleet.increments``.
    packages_saving
        Marginal-saving cash flow of each package, USD/year.
    discount_rate
        Discount rate of the adoption decision: the technology cost of capital,
        falling back to the vessel's, fraction.
    vessel_discount_rate
        Vessel cost of capital, fraction; it levelizes the carried retrofit charge
        consistently with the freight-rate NPVs, while the adoption decision keeps
        the technology rate.
    capex_npv
        Summed ship CAPEX NPV, USD; it non-dimensionalizes the NPVs in the DCM.
    """

    vessel: Vessel
    vessel_idx: int
    packages_saving: list[FloatArray]
    discount_rate: float
    vessel_discount_rate: float
    capex_npv: float


@dataclass
class _RetrofitProposal:
    """
    MNL retrofit jumps for the eligible share of one (vessel, increment, package).

    Parameters
    ----------
    vessel_idx
        Index of the vessel in ``fleet.assets``; it groups the proposals per vessel in
        the transfer.
    increment
        Age cohort whose ``package_uptake`` the apply step updates.
    package_idx
        Package the eligible share sits at.
    choices
        MNL shares over the retrofit steps, fraction: ``choices[0]`` stays and
        ``choices[k]`` jumps to ``package_idx + k``; the cap reconciliation rescales
        it in place.
    eligible_share
        Share of the increment at ``package_idx`` at propose time, fraction.
    annual_costs
        Levelized charge of each retrofit step, USD/year per vessel.
    """

    vessel_idx: int

    # holding the cohort is safe: nothing changes the structure of the
    # fleet.increments lists between propose and transfer, as that happens in
    # perform_fleet_evolution
    increment: VesselIncrement

    package_idx: int
    choices: FloatArray

    # equals the live share at apply time, as proposals apply in decreasing package
    # order and an apply only adds to higher packages
    eligible_share: float

    annual_costs: FloatArray

    @property
    def eligible_count(self) -> float:
        """Number of vessels able to make this jump."""
        return float(self.increment.multiplier) * self.eligible_share

    def first_adopting_step(self, technology_idx: int) -> int:
        """
        Return the first choice step reaching the technology at `technology_idx`.

        May exceed the number of steps; callers guard.

        Parameters
        ----------
        technology_idx
            Index of the technology in the CAPEX-sorted order.

        Returns
        -------
        int
            Index into ``choices`` of the first step reaching the technology.
        """
        return technology_idx - self.package_idx + 1

    def cap_contribution(self, technology_idx: int) -> _CapContribution | None:
        """
        Return this proposal's contribution to the cap of one technology.

        Parameters
        ----------
        technology_idx
            Index of the technology in the CAPEX-sorted order.

        Returns
        -------
        _CapContribution | None
            The contribution, or None when no retrofit step reaches the technology.
        """
        start = self.first_adopting_step(technology_idx)
        if not 0 < start < len(self.choices):
            return None

        return _CapContribution(self.choices, start, self.eligible_count)


@dataclass
class _CapContribution:
    """
    One share vector's contribution to a technology's cap aggregate.

    It caches ``adopting_share``, the sum of ``shares[start:]``, for the scale pass.

    Parameters
    ----------
    shares
        Retrofit choices or newbuild uptake, fraction; the tail is scaled in place
        when the cap binds.
    start
        First index adopting the capped technology.
    weight
        Vessels behind the vector: the eligible count of a retrofit or the newbuild
        count, number of vessels.
    """

    shares: FloatArray
    start: int
    weight: float
    adopting_share: float = field(init=False)

    def __post_init__(self) -> None:
        self.adopting_share = float(np.sum(self.shares[self.start :]))


@dataclass
class _TechnologyEffect:
    """
    Uptake-weighted technology effect on a vessel type, over (increment, package).

    Parameters
    ----------
    saving_sea
        Weighted saving on each leg, operational minus residual energy, GJ/year.
    saving_port
        Weighted saving at each port call, GJ/year.
    weight
        Total uptake weight, which normalizes the averages, number of vessels.
    shore_capacity
        Weighted shore power capacity, MW.
    """

    saving_sea: dict[EnergyDemandTypeID, FloatArray]
    saving_port: dict[EnergyDemandTypeID, FloatArray]
    weight: float = 0.0
    shore_capacity: float = 0.0


def build_technology_packages(
    technologies: list[Technology],
) -> tuple[list[TechnologyPackage], dict[int, int]]:
    """
    Sort technologies by CAPEX and organize them into cumulative packages.

    Parameters
    ----------
    technologies
        Technologies to organize into packages.

    Returns
    -------
    list[TechnologyPackage]
        Technology packages from empty to full.
    dict[int, int]
        Map from a package index to the index, in ``technologies``, of the technology
        that package adds.
    """
    sorted_pairs = sorted(enumerate(technologies), key=lambda p: p[1].capex.get())
    sorted_techs = [t for _, t in sorted_pairs]
    packages = [
        TechnologyPackage(sorted_techs[:i]) for i in range(len(sorted_techs) + 1)
    ]
    package_to_technology_map = {
        i: sorted_pairs[i - 1][0] for i in range(1, len(sorted_pairs) + 1)
    }

    return packages, package_to_technology_map


def calculate_package_charter_rates(
    packages: list[TechnologyPackage], vessel: Vessel
) -> FloatArray:
    """
    Levelize each package's cost, installed at build, over the vessel lifetime.

    The vessel cost of capital levelizes it, so the charge is consistent with the
    freight-rate NPVs it feeds; the adoption decision keeps its own discount rate.

    Parameters
    ----------
    packages
        All technology packages, from empty to full, with the cost flows of
        ``preprocess_packages``.
    vessel
        Vessel whose lifetime and cost of capital govern the levelization.

    Returns
    -------
    FloatArray
        Constant yearly charge per package, USD/year.
    """
    lifetime = vessel.lifetime.get()
    discount_rate = vessel.cost_of_capital.get()

    return np.array(
        [
            levelize_package_cost(pkg.cost_flow, lifetime, discount_rate)
            for pkg in packages
        ]
    )


def define_initial_technology(fleet: Fleet) -> None:
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
    n_vessels = len(fleet.assets)

    fleet.newbuild_package_uptake = [
        np.zeros(n_pkgs, dtype=float) for _ in range(n_vessels)
    ]

    if all(share is None for share in fleet.initial_technology_share.values()):
        return

    for v, vessel in enumerate(fleet.assets):
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
        Index of `vessel` in `fleet.assets`.
    """
    vessel_name = vessel.name
    truncation_count = 0
    truncated_tech_names = set()

    # seeded uptake is charged as if installed at build (consistent with the
    # hull, which the instantaneous freight rate charges at full newbuild cost)
    package_rates = calculate_package_charter_rates(fleet.technology_packages, vessel)

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


def _calculate_packages_saving(
    vessel: Vessel, packages: list[TechnologyPackage], timeline: FloatArray, idx: int
) -> list[FloatArray]:
    """
    Calculate each technology package's marginal saving on the vessel's year grid.

    Parameters
    ----------
    vessel
        Vessel to calculate the savings for.
    packages
        All technology packages.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.

    Returns
    -------
    list[FloatArray]
        Saving flow of each package, USD/year.
    """
    idx_ = np.s_[idx:]
    times = timeline[idx_]

    time_flow = timeline_to_yearly(vessel, idx, timeline)

    savings = []
    for package in packages:
        saving = calculate_marginal_technology_saving(vessel, package, idx_)
        savings.append(np.interp(time_flow, times, saving))

    return savings


def perform_technology_installation(
    fleet: Fleet, timeline: FloatArray, time_step: float, idx: int
) -> None:
    """
    Install technologies on the fleet's newbuilds and existing vessels.

    Runs the phases described in the module docstring.

    Parameters
    ----------
    fleet
        Fleet whose vessels install technologies.
    timeline
        Simulation timeline, days.
    time_step
        Current time-step size, days.
    idx
        Current time-step index.
    """
    # a fleet with technologies always has a technology sensitivity, as its
    # requirements check enforces
    technology_sensitivity = fleet.technology_sensitivity
    if not fleet.technologies or technology_sensitivity is None:
        return

    preprocess_packages(fleet.technology_packages, fleet.assets, timeline[idx])

    # the fleet count before newbuilds is the denominator of both the retrofit and the
    # newbuild technology caps
    multipliers_total = float(sum(fleet.get_multipliers()))

    proposals = []
    for v, vessel in enumerate(fleet.assets):
        basis = _extract_adoption_basis(fleet, vessel, v, timeline, idx)
        fleet.newbuild_package_uptake[v] = _propose_newbuild_uptake(
            fleet, basis, technology_sensitivity
        )
        proposals += _propose_retrofits(fleet, basis, technology_sensitivity, time_step)

    _reconcile_retrofit_technology_caps(fleet, proposals, time_step, multipliers_total)
    _apply_retrofits(proposals)
    _transfer_retrofit_uptake(fleet, proposals, idx)

    # transfer the fleet-average carried technology charge before the cargo
    # charter reads it later in the same timestep
    transfer_technology_charter_rate(fleet, idx)


def _extract_adoption_basis(
    fleet: Fleet,
    vessel: Vessel,
    vessel_idx: int,
    timeline: FloatArray,
    idx: int,
) -> _AdoptionBasis:
    """
    Bundle the per-vessel invariants of one technology-adoption pass.

    Parameters
    ----------
    fleet
        Fleet owning the vessel.
    vessel
        Vessel type the basis is built for.
    vessel_idx
        Index of `vessel` in `fleet.assets`.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.

    Returns
    -------
    _AdoptionBasis
        The basis bundle.
    """
    if fleet.technology_cost_of_capital:
        discount_rate = fleet.technology_cost_of_capital.get()
    else:
        discount_rate = vessel.cost_of_capital.get()

    packages_saving = _calculate_packages_saving(
        vessel, fleet.technology_packages, timeline, idx
    )

    # the NPV is non-dimensionalized by the summed ship CAPEX so the sensitivity is
    # unit-free
    capex_npv = vessel.expectation.get_capex_npv(idx)

    return _AdoptionBasis(
        vessel,
        vessel_idx,
        packages_saving,
        discount_rate,
        vessel.cost_of_capital.get(),
        capex_npv,
    )


def _propose_newbuild_uptake(
    fleet: Fleet, basis: _AdoptionBasis, technology_sensitivity: ForecastInput
) -> FloatArray:
    """
    Make the unconstrained MNL choice over newbuild packages for one vessel type.

    ``reconcile_newbuild_technology_caps`` reconciles it to the per-technology caps
    later in ``perform_fleet_evolution``, once the newbuild counts per vessel type are
    known.

    Parameters
    ----------
    fleet
        Fleet owning the vessel.
    basis
        Per-vessel invariants of the adoption pass.
    technology_sensitivity
        Odds ratio of the adoption choice.

    Returns
    -------
    FloatArray
        MNL share of each newbuild package, fraction.
    """
    npv = npv_for_newbuilds(
        basis.packages_saving, fleet.technology_packages, basis.discount_rate
    )
    choices, msg = calculate_asset_shares(
        npv,
        UtilityID.SIGNED_REFERENCE,
        technology_sensitivity.get(),
        reference=basis.capex_npv,
    )

    if msg:
        logger.warning(
            "%s newbuild technology uptake for %s %s", fleet, basis.vessel, msg
        )

    return choices


def _propose_retrofits(
    fleet: Fleet,
    basis: _AdoptionBasis,
    technology_sensitivity: ForecastInput,
    time_step: float,
) -> list[_RetrofitProposal]:
    """
    Propose unconstrained MNL retrofit jumps for every (increment, package) pair.

    The reconciliation downstream scales them to the per-technology caps.

    Parameters
    ----------
    fleet
        Fleet owning the vessel.
    basis
        Per-vessel invariants of the adoption pass.
    technology_sensitivity
        Odds ratio of the adoption choice.
    time_step
        Current time-step size, days.

    Returns
    -------
    list[_RetrofitProposal]
        One proposal per (increment, package) pair with vessels eligible to move, in
        decreasing package order, which `_apply_retrofits` relies on.
    """
    vessel = basis.vessel
    n_packages = len(fleet.technology_packages)

    retrofit_frequency = fleet.retrofit_frequency.get()
    sensitivity = technology_sensitivity.get()
    dt_years = time_step / YEAR

    proposals = []

    for package_idx in range(n_packages - 1, -1, -1):
        for inc in fleet.increments[basis.vessel_idx]:
            if not is_retrofit_cycle(inc.age, retrofit_frequency, dt_years):
                continue

            remaining = _get_remaining_lifetime(vessel, inc.age, inc.age_span)
            if remaining <= 0:
                continue

            eligible_share = float(inc.package_uptake[package_idx])
            if eligible_share <= 0.0:
                continue

            npv = npv_for_retrofit_steps(
                package_idx,
                basis.packages_saving,
                fleet.technology_packages,
                remaining,
                basis.discount_rate,
            )
            choices, _ = calculate_asset_shares(
                npv,
                UtilityID.SIGNED_REFERENCE,
                sensitivity,
                reference=basis.capex_npv,
            )
            annual_costs = annual_costs_for_retrofit_steps(
                package_idx,
                fleet.technology_packages,
                remaining,
                basis.vessel_discount_rate,
            )
            proposals.append(
                _RetrofitProposal(
                    basis.vessel_idx,
                    inc,
                    package_idx,
                    choices,
                    eligible_share,
                    annual_costs,
                )
            )

    return proposals


def _get_remaining_lifetime(vessel: Vessel, age: float, dt: float) -> int:
    lifetime = vessel.lifetime.get()
    return max(0, int(round(lifetime - (age + dt / 2.0), ROUND_OFF)))


def _reconcile_retrofit_technology_caps(
    fleet: Fleet,
    proposals: list[_RetrofitProposal],
    time_step: float,
    multipliers_total: float,
) -> None:
    """
    Scale the proposals' retrofit `choices` to the per-technology caps.

    For every technology, the retrofits adopting it this time-step must not exceed
    `limit * multipliers_total * time_step / YEAR`. The cap aggregate weights each
    proposal's tail sum by its `eligible_count`, the count `_apply_retrofits` will
    produce, and the displaced share moves to the stay option (see
    `_scale_tails_to_cap`).

    The technologies run from outermost to innermost in the CAPEX-sorted package
    order: scaling one proposal's tail, `choices[k_start:]`, reduces the retrofits of
    every technology those steps introduce, so taking the outer technologies first
    keeps the inner-technology aggregates monotonic.

    Parameters
    ----------
    fleet
        Fleet whose retrofit caps are enforced.
    proposals
        Output of `_propose_retrofits`; each proposal's `choices` is rescaled in place
        when a technology it covers has a binding cap.
    time_step
        Current time-step size, days.
    multipliers_total
        Number of vessels in the fleet before newbuilds.
    """
    if multipliers_total <= 0.0 or not proposals or not fleet.technology_packages:
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
            contribution = proposal.cap_contribution(i)
            if contribution is not None:
                contributions.append(contribution)

        _scale_tails_to_cap(contributions, cap)


def reconcile_newbuild_technology_caps(
    fleet: Fleet, increments: FloatArray, time_step: float, multipliers_total: float
) -> None:
    """
    Scale `fleet.newbuild_package_uptake` to the per-technology caps.

    For every technology, the newbuild installs of it this time-step must not exceed
    `limit * multipliers_total * time_step / YEAR`. The technologies run from
    outermost to innermost in the CAPEX-sorted package order, as in the retrofit
    reconciliation, and the displaced share moves to the no-technology package (see
    `_scale_tails_to_cap`), so each vessel's uptake still sums to 1.

    Parameters
    ----------
    fleet
        Fleet whose newbuild caps are enforced.
    increments
        Newbuilds of each vessel type this time-step, number of vessels; they weight
        each vessel's contribution to the cap aggregate.
    time_step
        Current time-step size, days.
    multipliers_total
        Number of vessels in the fleet before newbuilds.
    """
    if multipliers_total <= 0.0 or not fleet.technology_packages:
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
            if k_start >= len(uptake) or increments[v] <= 0.0:
                continue

            contributions.append(
                _CapContribution(uptake, k_start, float(increments[v]))
            )

        _scale_tails_to_cap(contributions, cap)


def _scale_tails_to_cap(contributions: list[_CapContribution], cap: float) -> None:
    """
    Scale the contributions' adopting tails so their weighted aggregate fits the cap.

    When the cap binds, every contribution's displaced share goes to `shares[0]`, the
    stay or no-technology option. With the cumulative packages `[none, A, A+B]` and a
    binding cap on B, the excess demand for `A+B` goes to `none` even when A's own cap
    has slack: the package is the unit of choice in the DCM, so a rationed first
    choice reads as deferring this cycle for a retrofit, or building without
    technology for a newbuild.

    Parameters
    ----------
    contributions
        Share vectors adopting the capped technology, with cached tail sums.
    cap
        Largest weighted aggregate of adopting shares this time-step, number of
        vessels.
    """
    aggregate = 0.0
    for contribution in contributions:
        aggregate += contribution.weight * contribution.adopting_share

    if aggregate <= cap + TOLERANCE:
        return

    scale = cap / aggregate

    for contribution in contributions:
        contribution.shares[contribution.start :] *= scale
        contribution.shares[0] += (1.0 - scale) * contribution.adopting_share


def _apply_retrofits(proposals: list[_RetrofitProposal]) -> None:
    """
    Move each proposal's eligible uptake from its package level to chosen higher ones.

    Each moved share also adds its levelized retrofit charge to the increment's carried
    `technology_charter_rate`, so the retrofit cost is recovered as a constant yearly
    charge over the remaining vessel lifetime it was levelized against.

    Proposals must arrive in decreasing package order (the order `_propose_retrofits`
    emits): each apply only adds to higher packages, so the live `uptake[package_idx]`
    read below still equals the `eligible_share` snapshot taken at propose time.

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

        uptake[package_idx] = current * (1.0 - moved_total)

        for step in range(1, len(choices)):
            uptake[package_idx + step] += current * choices[step]
            increment.technology_charter_rate += (
                current * choices[step] * annual_costs[step]
            )


def _transfer_retrofit_uptake(
    fleet: Fleet, proposals: list[_RetrofitProposal], idx: int
) -> None:
    """
    Write each (vessel, technology) retrofit count to the profile.

    The stored value, laid out as in `transfer_technology_uptake`, is the share of the
    vessel type's existing fleet that retrofitted to the technology this time-step,
    directly comparable to `set_retrofit_technology_limit * time_step / YEAR`.

    Parameters
    ----------
    fleet
        Fleet whose retrofit uptake is recorded.
    proposals
        Reconciled and applied retrofit proposals.
    idx
        Current time-step index.
    """
    if not fleet.technology_packages or not proposals:
        return

    sorted_technologies = fleet.technology_packages[-1].technologies
    if not sorted_technologies:
        return

    retrofit_counts: dict[tuple[int, int], float] = {}
    for proposal in proposals:
        weight = proposal.eligible_count
        if weight <= 0.0:
            continue

        for i in range(proposal.package_idx, len(sorted_technologies)):
            k_start = proposal.first_adopting_step(i)
            if k_start >= len(proposal.choices):
                break

            # `_apply_retrofits` only reads `choices`, so the reconciled tail sums
            # are intact
            key = (proposal.vessel_idx, i)
            retrofit_counts[key] = retrofit_counts.get(key, 0.0) + weight * float(
                np.sum(proposal.choices[k_start:])
            )

    for v, vessel in enumerate(fleet.assets):
        multipliers_total = float(sum(inc.multiplier for inc in fleet.increments[v]))
        for i, technology in enumerate(sorted_technologies):
            count = retrofit_counts.get((v, i), 0.0)
            share = float(divide_nonzero(count, multipliers_total))
            fleet.profile.set_retrofit_technology_uptake(
                idx, vessel.name, technology.name, share
            )


def transfer_technology_charter_rate(fleet: Fleet, idx: int) -> None:
    """
    Transfer the fleet-average carried charge to each vessel's expectation and profile.

    The average is the multiplier-weighted mean of the per-increment carried charges,
    USD/year per vessel. It feeds the investment freight rate within the same
    time-step, as the cargo charter runs after technology installation, and the
    profile keeps it as the realized series the instantaneous freight rate is
    post-processed from.

    Parameters
    ----------
    fleet
        Fleet whose carried charges are aggregated.
    idx
        Current time-step index.
    """
    for v, vessel in enumerate(fleet.assets):
        total = 0.0
        weight = 0.0
        for inc in fleet.increments[v]:
            total += inc.multiplier * inc.technology_charter_rate
            weight += inc.multiplier

        average = float(divide_nonzero(total, weight))

        vessel.expectation.set_technology_charter_rate(idx, average)
        vessel.profile.set_technology_cost(idx, average)


def transfer_technology_uptake(fleet: Fleet, idx: int) -> None:
    """
    Transfer the newbuild and fleet-average technology uptake to the fleet profile.

    Parameters
    ----------
    fleet
        Fleet whose uptake is transferred.
    idx
        Current time-step index.
    """
    for v, vessel in enumerate(fleet.assets):
        for p, _package in enumerate(fleet.technology_packages[1:], start=1):
            t = fleet.package_to_technology_map[p]
            technology = fleet.technologies[t]

            nb_uptake = np.sum(fleet.newbuild_package_uptake[v][p:])
            fleet.profile.set_newbuild_technology_uptake(
                idx, vessel.name, technology.name, nb_uptake
            )

            weighted_uptake = 0.0
            weight = 0.0
            for inc in fleet.increments[v]:
                inc_uptake = float(np.sum(inc.package_uptake[p:]))
                weighted_uptake += inc_uptake * inc.multiplier
                weight += inc.multiplier

            avg_uptake = float(divide_nonzero(weighted_uptake, weight))
            fleet.profile.set_technology_uptake(
                idx, vessel.name, technology.name, avg_uptake
            )


def update_residual_energy_demand(fleet: Fleet, idx: int) -> None:
    """
    Update every vessel's residual energy demand after technology installation.

    Parameters
    ----------
    fleet
        Fleet whose vessels are updated.
    idx
        Current time-step index.
    """
    transfer_operational_saving_to_vessels(fleet)

    for v, vessel in enumerate(fleet.assets):
        op_sea, op_port = _apply_operational_savings(vessel, idx)
        op_sea_arr = {d: np.asarray(op_sea[d], dtype=float) for d in EnergyDemandTypeID}
        op_port_arr = {
            d: np.asarray(op_port[d], dtype=float) for d in EnergyDemandTypePortID
        }

        effect = _accumulate_technology_effect(
            fleet, v, vessel, op_sea_arr, op_port_arr, idx
        )
        _transfer_residual_energy(vessel, op_sea_arr, op_port_arr, effect, idx)


def _apply_operational_savings(
    vessel: Vessel, idx: int
) -> tuple[
    dict[EnergyDemandTypeID, list[FloatArray]],
    dict[EnergyDemandTypeID, list[FloatArray]],
]:
    """
    Apply the operational saving fractions to the vessel's raw energy demand.

    The operational savings are zero-cost reductions such as JIT and weather routing.
    The result is stored on the expectation and the profile.

    Parameters
    ----------
    vessel
        Vessel to apply the operational savings for.
    idx
        Current time-step index.

    Returns
    -------
    dict[EnergyDemandTypeID, list[FloatArray]]
        Operational energy at sea per energy demand type and leg, GJ/year.
    dict[EnergyDemandTypeID, list[FloatArray]]
        Operational energy in port per energy demand type and port call, GJ/year.
    """
    expectation = vessel.expectation

    raw_sea = expectation.get_raw_energy_sea(idx=idx)
    raw_port = expectation.get_raw_energy_port(idx=idx)

    saving_sea = expectation.get_operational_saving_fraction_sea()
    saving_port = expectation.get_operational_saving_fraction_port()

    op_sea = {
        d: [np.asarray(leg, dtype=float) * (1.0 - saving_sea[d]) for leg in raw_sea[d]]
        for d in EnergyDemandTypeID
    }
    op_port = {
        d: [
            np.asarray(port, dtype=float) * (1.0 - saving_port[d])
            for port in raw_port[d]
        ]
        for d in EnergyDemandTypePortID
    }

    vessel.expectation.set_operational_energy_sea(idx, op_sea)
    vessel.expectation.set_operational_energy_port(idx, op_port)

    vessel.profile.set_operational_energy_sea(
        idx, {d: float(np.sum(op_sea[d])) for d in EnergyDemandTypeID}
    )
    vessel.profile.set_operational_energy_port(
        idx, {d: float(np.sum(op_port[d])) for d in EnergyDemandTypePortID}
    )

    regional_op_sea = convert_to_regional_steps(vessel, op_sea)
    vessel.expectation.set_regional_operational_energy_sea(idx, regional_op_sea)

    return op_sea, op_port


def _accumulate_technology_effect(
    fleet: Fleet,
    vessel_idx: int,
    vessel: Vessel,
    op_sea_arr: dict[EnergyDemandTypeID, FloatArray],
    op_port_arr: dict[EnergyDemandTypeID, FloatArray],
    idx: int,
) -> _TechnologyEffect:
    """
    Accumulate the uptake-weighted technology effect over (increment, package) pairs.

    A technology saving is the operational energy less the residual energy.

    Parameters
    ----------
    fleet
        Fleet owning the increments and technology packages.
    vessel_idx
        Index of `vessel` in `fleet.assets`.
    vessel
        Vessel to accumulate the effect for.
    op_sea_arr
        Operational energy at sea per demand type, one array over legs, GJ/year.
    op_port_arr
        Operational energy in port per demand type, one array over ports, GJ/year.
    idx
        Current time-step index.

    Returns
    -------
    _TechnologyEffect
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
            if w <= 0.0:
                continue

            residual_sea, residual_port = calculate_residual_energy(
                vessel, package, np.s_[idx]
            )

            for demand, residual in residual_sea.items():
                effect.saving_sea[demand] += w * (
                    op_sea_arr[demand] - np.asarray(residual, dtype=float)
                )

            for demand, residual in residual_port.items():
                effect.saving_port[demand] += w * (
                    op_port_arr[demand] - np.asarray(residual, dtype=float)
                )

            effect.weight += w
            effect.shore_capacity += w * package.shore_power_capacity

    return effect


def _transfer_residual_energy(
    vessel: Vessel,
    op_sea_arr: dict[EnergyDemandTypeID, FloatArray],
    op_port_arr: dict[EnergyDemandTypeID, FloatArray],
    effect: _TechnologyEffect,
    idx: int,
) -> None:
    """
    Store the averaged technology effect's shore power and residual energy demand.

    Parameters
    ----------
    vessel
        Vessel to store the results for.
    op_sea_arr
        Operational energy at sea per demand type, one array over legs, GJ/year.
    op_port_arr
        Operational energy in port per demand type, one array over ports, GJ/year.
    effect
        Accumulated technology effect.
    idx
        Current time-step index.
    """
    avg_shore_capacity = (
        effect.shore_capacity / effect.weight if effect.weight > 0.0 else 0.0
    )
    vessel.expectation.set_shore_power_capacity(idx, avg_shore_capacity)

    # without any uptake weight the residual energy stays the operational energy
    if effect.weight <= 0.0:
        avg_residual_sea = op_sea_arr
        avg_residual_port = op_port_arr
    else:
        inv_w = 1.0 / effect.weight
        avg_residual_sea = {
            d: op_sea_arr[d] - effect.saving_sea[d] * inv_w for d in EnergyDemandTypeID
        }
        avg_residual_port = {
            d: op_port_arr[d] - effect.saving_port[d] * inv_w
            for d in EnergyDemandTypePortID
        }

    vessel.expectation.set_energy_sea(idx, avg_residual_sea)
    vessel.expectation.set_energy_port(idx, avg_residual_port)

    vessel.profile.set_energy_sea(
        idx, {d: float(arr.sum()) for d, arr in avg_residual_sea.items()}
    )
    vessel.profile.set_energy_port(
        idx, {d: float(arr.sum()) for d, arr in avg_residual_port.items()}
    )

    regional_sea = convert_to_regional_steps(
        vessel, {d: list(arr) for d, arr in avg_residual_sea.items()}
    )
    vessel.expectation.set_regional_energy_sea(idx, regional_sea)


def approximate_missing_technology(fleets: dict[str, Fleet], idx: int) -> None:
    """
    Estimate the energy-efficiency savings of the fleets that cannot retrofit.

    The average saving of the fleets that can retrofit applies to the energy demand
    of every fleet allowing the approximation. It carries no cost, so the cost of the
    efficiency improvements is underestimated.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.
    """
    average_saving_sea, average_saving_port = _average_retrofit_savings(fleets, idx)

    for fleet in fleets.values():
        if fleet.can_retrofit() or not fleet.allow_technology_approximation:
            continue

        for vessel in fleet.vessels:
            _apply_approximated_saving(
                vessel, average_saving_sea, average_saving_port, idx
            )


def _average_retrofit_savings(
    fleets: dict[str, Fleet], idx: int
) -> tuple[dict[EnergyDemandTypeID, float], dict[EnergyDemandTypeID, float]]:
    """
    Calculate the energy-weighted average technology saving of retrofit-capable fleets.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.

    Returns
    -------
    dict[EnergyDemandTypeID, float]
        Average saving at sea per demand type, fraction.
    dict[EnergyDemandTypeID, float]
        Average saving in port per demand type, fraction.
    """
    average_saving_sea = dict.fromkeys(EnergyDemandTypeID, 0.0)
    average_saving_port = dict.fromkeys(EnergyDemandTypePortID, 0.0)

    weight_sea = dict.fromkeys(average_saving_sea, 0.0)
    weight_port = dict.fromkeys(average_saving_port, 0.0)

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

            _accumulate_energy_weighted_saving(
                raw_energy_sea, savings_sea, multiplier, average_saving_sea, weight_sea
            )
            _accumulate_energy_weighted_saving(
                raw_energy_port,
                savings_port,
                multiplier,
                average_saving_port,
                weight_port,
            )

    for k in average_saving_sea:
        average_saving_sea[k] = (
            (average_saving_sea[k] / weight_sea[k]) if weight_sea[k] else 0.0
        )
    for k in average_saving_port:
        average_saving_port[k] = (
            (average_saving_port[k] / weight_port[k]) if weight_port[k] else 0.0
        )

    return average_saving_sea, average_saving_port


def _accumulate_energy_weighted_saving(
    raw_energy: Mapping[EnergyDemandTypeID, Sequence[FloatLike]],
    savings: Mapping[EnergyDemandTypeID, Sequence[float]],
    multiplier: float,
    saving_totals: dict[EnergyDemandTypeID, float],
    weight_totals: dict[EnergyDemandTypeID, float],
) -> None:
    """
    Accumulate one vessel's energy-weighted saving fractions into the running totals.

    Parameters
    ----------
    raw_energy
        Raw energy demand per demand type, one value per leg or port call, GJ/year;
        with `multiplier`, it weights the accumulation.
    savings
        Saving per demand type, one value per leg or port call, fraction.
    multiplier
        Number of vessels of this type.
    saving_totals
        Running weighted saving sums per demand type; updated in place.
    weight_totals
        Running weight sums per demand type; updated in place.
    """
    for k in saving_totals:
        for leg, raw in enumerate(raw_energy[k]):
            weight = float(raw) * multiplier
            saving_totals[k] += savings[k][leg] * weight
            weight_totals[k] += weight


def _apply_approximated_saving(
    vessel: Vessel,
    average_saving_sea: dict[EnergyDemandTypeID, float],
    average_saving_port: dict[EnergyDemandTypeID, float],
    idx: int,
) -> None:
    """
    Apply the fleet-average savings to one vessel's operational energy and store it.

    Parameters
    ----------
    vessel
        Vessel to apply the approximated savings to.
    average_saving_sea
        Average saving at sea per demand type, fraction.
    average_saving_port
        Average saving in port per demand type, fraction.
    idx
        Current time-step index.
    """
    op_sea = vessel.expectation.get_operational_energy_sea(idx=idx)
    op_port = vessel.expectation.get_operational_energy_port(idx=idx)

    sav_sea = {
        k: [average_saving_sea[k]] * len(op_sea[k])
        for k in average_saving_sea
        if k in op_sea
    }

    sav_port = {
        k: [average_saving_port[k]] * len(op_port[k])
        for k in average_saving_port
        if k in op_port
    }

    net_sea = net_energy_from_raw(op_sea, sav_sea)
    net_port = net_energy_from_raw(op_port, sav_port)
    regional_sea = convert_to_regional_steps(vessel, net_sea)

    vessel.expectation.set_energy_sea(idx, net_sea)
    vessel.expectation.set_energy_port(idx, net_port)
    vessel.expectation.set_regional_energy_sea(idx, regional_sea)

    vessel.profile.set_energy_sea(
        idx, {k: float(np.sum(np.asarray(net_sea[k]))) for k in net_sea}
    )
    vessel.profile.set_energy_port(
        idx, {k: float(np.sum(np.asarray(net_port[k]))) for k in net_port}
    )
