# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Newbuild and retrofit technology choice under technology caps.

The cumulative technology package is the unit of choice.
``perform_technology_installation`` runs four phases per fleet and time-step:

1. ``_propose_newbuild_uptake`` and ``_propose_retrofits`` make the unconstrained MNL
   choices per vessel.
2. ``_reconcile_retrofit_technology_caps`` scales the retrofit proposals to the caps.
3. ``_apply_retrofits`` updates the per-increment uptake and the carried charge.
4. ``_transfer_retrofit_uptake`` and ``transfer_technology_charter_rate`` write the
   results.

The retrofit phases communicate through ``_RetrofitProposal`` objects. Newbuild uptake
is reconciled later, in ``close_trade_gap`` (``reconcile_newbuild_technology_caps``),
once newbuild counts per vessel type are known; the fleet results takes the reconciled
shares at the end of the time-step.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import UtilityID
from navigate.simulation.economics.decision import calculate_asset_shares
from navigate.simulation.economics.flows import (
    timeline_to_yearly,
    trim_flow_to_lifetime,
)
from navigate.simulation.fleet._composition import (
    get_multipliers,
    get_total_multiplier,
    is_retrofit_cycle,
)
from navigate.simulation.fleet._marginal_saving import (
    calculate_marginal_technology_saving,
)
from navigate.simulation.fleet._package import (
    calculate_newbuild_npv,
    calculate_retrofit_charter_rates,
    calculate_retrofit_npv,
    get_package_cost_flows,
    get_technologies_by_capex,
    update_packages,
)
from navigate.simulation.fleet._trip import bind_conditions_to_legs
from navigate.util import ROUND_OFF, TOLERANCE, YEAR, divide_nonzero

if TYPE_CHECKING:
    from collections.abc import Iterator

    from navigate.core.increment import VesselIncrement
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.technology_package import TechnologyPackage
    from navigate.core.types_ import ForecastInput
    from navigate.util.types_ import FloatArray

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
        Index of the vessel in ``fleet.vessels`` and ``fleet.increments``.
    packages_saving
        Marginal-saving cash flow of each package, in USD/year.
    discount_rate
        Discount rate of the adoption decision: the technology cost of capital,
        falling back to the vessel's, fraction.
    vessel_discount_rate
        Vessel cost of capital, fraction; it levelizes the carried retrofit charge
        consistently with the freight-rate NPVs, while the adoption decision keeps
        the technology rate.
    capex_npv
        Summed ship CAPEX NPV, in USD; it non-dimensionalizes the NPVs in the DCM.
    sensitivity
        Odds ratio of the adoption choice.
    """

    vessel: Vessel
    vessel_idx: int
    packages_saving: list[FloatArray]
    discount_rate: float
    vessel_discount_rate: float
    capex_npv: float
    sensitivity: float

    def calculate_shares(self, npv: FloatArray) -> tuple[FloatArray, str]:
        """
        Calculate the MNL shares of the options from their NPVs.

        Parameters
        ----------
        npv
            NPV of each option, in USD.

        Returns
        -------
        tuple[FloatArray, str]
            Share of each option, fraction, and a potential warning message.
        """
        utility = UtilityID.SIGNED_REFERENCE
        return calculate_asset_shares(npv, utility, self.sensitivity, self.capex_npv)


@dataclass
class _RetrofitProposal:
    """
    MNL retrofit jumps for the eligible share of one (vessel, increment, package).

    Parameters
    ----------
    vessel_idx
        Index of the vessel in ``fleet.vessels``; it groups the proposals per vessel in
        the transfer.
    increment
        Age cohort whose ``package_uptake`` the apply step updates. Holding it is safe:
        the structure of the ``fleet.increments`` lists changes only in the fleet
        evolution, after the transfer.
    package_idx
        Package the eligible share sits at.
    choices
        MNL shares over the retrofit steps, fraction: ``choices[0]`` stays and
        ``choices[k]`` jumps to ``package_idx + k``; the cap reconciliation rescales
        it in place.
    eligible_share
        Share of the increment at ``package_idx`` at propose time, fraction.
    annual_costs
        Levelized charge of each retrofit step, in USD/year per vessel.
    """

    vessel_idx: int
    increment: VesselIncrement
    package_idx: int
    choices: FloatArray
    eligible_share: float
    annual_costs: FloatArray

    @property
    def eligible_count(self) -> float:
        """Number of vessels able to make this jump."""
        return self.increment.multiplier * self.eligible_share

    def first_adopting_step(self, technology_idx: int) -> int:
        """
        Return the first choice step reaching the technology at `technology_idx`.

        It is not positive when the package already holds the technology.

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
            The contribution, or None when the package already holds the technology.
        """
        start = self.first_adopting_step(technology_idx)
        if start <= 0:
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
        count, in vessels.
    """

    shares: FloatArray
    start: int
    weight: float
    adopting_share: float = field(init=False)

    def __post_init__(self) -> None:
        self.adopting_share = float(np.sum(self.shares[self.start :]))


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
        Simulation timeline, in days.
    time_step
        Current time-step size, in days.
    idx
        Current time-step index.
    """
    # a fleet with technologies always has a technology sensitivity, as its
    # requirements check enforces
    technology_sensitivity = fleet.technology_sensitivity
    if not fleet.technologies or technology_sensitivity is None:
        return

    update_packages(fleet.technology_packages, fleet.package_cost_flows, timeline[idx])

    # the fleet count before newbuilds is the denominator of both the retrofit and the
    # newbuild technology caps
    multipliers_total = get_total_multiplier(fleet)
    sensitivity = technology_sensitivity.get()

    proposals = []
    for v, vessel in enumerate(fleet.vessels):
        basis = _extract_adoption_basis(fleet, vessel, v, sensitivity, timeline, idx)
        fleet.newbuild_package_uptake[v] = _propose_newbuild_uptake(fleet, basis)
        proposals += _propose_retrofits(fleet, basis, time_step)

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
    sensitivity: float,
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
        Index of `vessel` in `fleet.vessels`.
    sensitivity
        Odds ratio of the adoption choice.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.

    Returns
    -------
    _AdoptionBasis
        The basis bundle.
    """
    technology_rate = fleet.technology_cost_of_capital
    vessel_rate = vessel.cost_of_capital.get()
    discount_rate = vessel_rate if technology_rate is None else technology_rate.get()

    packages = fleet.technology_packages
    packages_saving = _calculate_packages_saving(vessel, packages, timeline, idx)
    capex_npv = vessel.expectation.get_capex_npv(idx)

    return _AdoptionBasis(
        vessel,
        vessel_idx,
        packages_saving,
        discount_rate,
        vessel_rate,
        capex_npv,
        sensitivity,
    )


def _calculate_packages_saving(
    vessel: Vessel, packages: list[TechnologyPackage], timeline: FloatArray, idx: int
) -> list[FloatArray]:
    """
    Calculate each technology package's marginal saving over the vessel lifetime.

    The saving is sampled at the start of each year from the decision time; the last
    partial year is prorated, as the package cost flows are.

    Parameters
    ----------
    vessel
        Vessel to calculate the savings for.
    packages
        All technology packages.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.

    Returns
    -------
    list[FloatArray]
        Saving flow of each package, in USD/year.
    """
    lifetime = vessel.lifetime.get()
    forward = np.s_[idx:]
    legs = bind_conditions_to_legs(vessel.route)

    times = timeline[forward]
    yearly_times = timeline_to_yearly(vessel, idx, timeline)

    savings = []
    for package in packages:
        saving = calculate_marginal_technology_saving(vessel, legs, package, forward)
        yearly_saving = np.interp(yearly_times, times, saving)
        savings.append(trim_flow_to_lifetime(yearly_saving, lifetime))

    return savings


def _propose_newbuild_uptake(fleet: Fleet, basis: _AdoptionBasis) -> FloatArray:
    """
    Make the unconstrained MNL choice over newbuild packages for one vessel type.

    ``reconcile_newbuild_technology_caps`` reconciles it to the per-technology caps
    later in ``close_trade_gap``, once the newbuild counts per vessel type are known.

    Parameters
    ----------
    fleet
        Fleet owning the vessel.
    basis
        Per-vessel invariants of the adoption pass.

    Returns
    -------
    FloatArray
        MNL share of each newbuild package, fraction.
    """
    packages = fleet.technology_packages
    lifetime = basis.vessel.lifetime.get()

    cost_flows = get_package_cost_flows(packages, fleet.package_cost_flows, lifetime)
    npv = calculate_newbuild_npv(basis.packages_saving, cost_flows, basis.discount_rate)
    choices, msg = basis.calculate_shares(npv)

    if msg:
        logger.warning(
            "%s newbuild technology uptake for %s %s", fleet, basis.vessel, msg
        )

    return choices


def _propose_retrofits(
    fleet: Fleet, basis: _AdoptionBasis, time_step: float
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
    time_step
        Current time-step size, in days.

    Returns
    -------
    list[_RetrofitProposal]
        One proposal per (increment, package) pair with vessels eligible to move, in
        decreasing package order, which `_apply_retrofits` relies on.
    """
    cohorts = list(_retrofit_cohorts(fleet, basis, time_step))

    v = basis.vessel_idx
    savings = basis.packages_saving
    discount_rate = basis.discount_rate
    vessel_rate = basis.vessel_discount_rate

    proposals = []

    for p in reversed(range(len(fleet.technology_packages))):
        for increment, remaining, flows in cohorts:
            share = float(increment.package_uptake[p])
            if share <= 0.0:
                continue

            npv = calculate_retrofit_npv(p, savings, flows, remaining, discount_rate)
            choices, _ = basis.calculate_shares(npv)
            costs = calculate_retrofit_charter_rates(p, flows, remaining, vessel_rate)

            proposals.append(_RetrofitProposal(v, increment, p, choices, share, costs))

    return proposals


def _retrofit_cohorts(
    fleet: Fleet, basis: _AdoptionBasis, time_step: float
) -> Iterator[tuple[VesselIncrement, int, list[FloatArray]]]:
    """
    Yield the vessel's cohorts at a retrofit cycle that have lifetime left.

    Parameters
    ----------
    fleet
        Fleet owning the vessel.
    basis
        Per-vessel invariants of the adoption pass.
    time_step
        Current time-step size, in days.

    Yields
    ------
    tuple[VesselIncrement, int, list[FloatArray]]
        Each cohort, its remaining lifetime, in years, and the cost flow of each
        package over that lifetime, in USD/year.
    """
    packages = fleet.technology_packages
    frequency = fleet.retrofit_frequency.get()
    dt = time_step / YEAR

    for increment in fleet.increments[basis.vessel_idx]:
        if not is_retrofit_cycle(increment.age, frequency, dt):
            continue

        remaining = _get_remaining_lifetime(basis.vessel, increment)
        if remaining <= 0:
            continue

        # a retrofit is amortized over the years the cohort still serves
        flows = get_package_cost_flows(packages, fleet.package_cost_flows, remaining)
        yield increment, remaining, flows


def _get_remaining_lifetime(vessel: Vessel, increment: VesselIncrement) -> int:
    """Return the whole years of vessel lifetime left past the cohort's mean age."""
    age = increment.age + increment.age_span / 2.0
    return int(round(vessel.lifetime.get() - age, ROUND_OFF))


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
        Current time-step size, in days.
    multipliers_total
        Number of vessels in the fleet before newbuilds.
    """
    limits = fleet.retrofit_technology_limit
    caps = _technology_caps(fleet, limits, time_step, multipliers_total)

    for i, cap in caps:
        contributions = []
        for proposal in proposals:
            contribution = proposal.cap_contribution(i)
            if contribution is not None:
                contributions.append(contribution)

        _scale_tails_to_cap(contributions, cap)


def reconcile_newbuild_technology_caps(
    fleet: Fleet, newbuilds: FloatArray, time_step: float, multipliers_total: float
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
    newbuilds
        Newbuilds of each vessel type this time-step, in vessels; they weight each
        vessel's contribution to the cap aggregate.
    time_step
        Current time-step size, in days.
    multipliers_total
        Number of vessels in the fleet before newbuilds.
    """
    limits = fleet.newbuild_technology_limit
    caps = _technology_caps(fleet, limits, time_step, multipliers_total)
    uptakes = fleet.newbuild_package_uptake

    # package i + 1 is the first to hold technology i, as the packages are cumulative
    for i, cap in caps:
        contributions = []
        for uptake, count in zip(uptakes, newbuilds, strict=True):
            if count <= 0.0:
                continue

            contributions.append(_CapContribution(uptake, i + 1, count))

        _scale_tails_to_cap(contributions, cap)


def _technology_caps(
    fleet: Fleet,
    limits: dict[str, ForecastInput],
    time_step: float,
    multipliers_total: float,
) -> Iterator[tuple[int, float]]:
    """
    Yield each technology's cap this time-step, outermost technology first.

    A fleet without vessels before newbuilds has no caps to enforce.

    Parameters
    ----------
    fleet
        Fleet whose technologies are capped.
    limits
        Yearly cap of each technology as a share of the fleet, fraction.
    time_step
        Current time-step size, in days.
    multipliers_total
        Number of vessels in the fleet before newbuilds.

    Yields
    ------
    tuple[int, float]
        Index of the technology in the CAPEX-sorted order, and its cap, number of
        vessels.
    """
    if multipliers_total <= 0.0:
        return

    dt = time_step / YEAR
    technologies = get_technologies_by_capex(fleet.technology_packages)
    budget = multipliers_total * dt

    for i in reversed(range(len(technologies))):
        yield i, limits[technologies[i].name].get() * budget


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
        package_idx = proposal.package_idx

        current = uptake[package_idx]
        uptake[package_idx] = current * (1.0 - np.sum(choices[1:]))

        for step in range(1, len(choices)):
            moved = current * choices[step]
            uptake[package_idx + step] += moved
            increment.technology_charter_rate += moved * proposal.annual_costs[step]


def _transfer_retrofit_uptake(
    fleet: Fleet, proposals: list[_RetrofitProposal], idx: int
) -> None:
    """
    Write each (vessel, technology) retrofit count to the results.

    The stored value, laid out as the fleet results' technology uptake, is the share
    of the vessel type's existing fleet that retrofitted to the technology this
    time-step, directly comparable to `set_retrofit_technology_limit * time_step /
    YEAR`.

    Parameters
    ----------
    fleet
        Fleet whose retrofit uptake is recorded.
    proposals
        Reconciled and applied retrofit proposals.
    idx
        Current time-step index.
    """
    if not proposals:
        return

    technologies = get_technologies_by_capex(fleet.technology_packages)
    counts = np.zeros((len(fleet.vessels), len(technologies)))

    # `_apply_retrofits` only reads `choices`, so the reconciled tail sums are intact
    for proposal in proposals:
        v = proposal.vessel_idx
        count = proposal.eligible_count
        if count <= 0.0:
            continue

        for i in range(proposal.package_idx, len(technologies)):
            start = proposal.first_adopting_step(i)
            counts[v, i] += count * np.sum(proposal.choices[start:])

    multipliers = np.array(get_multipliers(fleet))
    shares = divide_nonzero(counts, multipliers[:, np.newaxis])
    uptake = fleet.results.retrofit_technology_uptake

    for v, vessel in enumerate(fleet.vessels):
        for i, technology in enumerate(technologies):
            uptake[vessel.name, technology.name][idx] = shares[v, i]


def transfer_technology_charter_rate(fleet: Fleet, idx: int) -> None:
    """
    Transfer the fleet-average carried charge to each vessel's expectation and results.

    The average is the multiplier-weighted mean of the per-increment carried charges,
    USD/year per vessel. It feeds the investment freight rate within the same
    time-step, as the cargo charter runs after technology installation, and the
    results keeps it as the realized series the instantaneous freight rate is
    post-processed from.

    Parameters
    ----------
    fleet
        Fleet whose carried charges are aggregated.
    idx
        Current time-step index.
    """
    for vessel, increments in zip(fleet.vessels, fleet.increments, strict=True):
        total = 0.0
        weight = 0.0
        for increment in increments:
            total += increment.multiplier * increment.technology_charter_rate
            weight += increment.multiplier

        average = float(divide_nonzero(total, weight))

        vessel.expectation.set_technology_charter_rate(idx, average)
        vessel.results.technology_cost[idx] = average
