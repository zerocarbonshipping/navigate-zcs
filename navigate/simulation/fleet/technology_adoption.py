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
   profile.

The retrofit phases communicate through ``_RetrofitProposal`` objects. Newbuild uptake
is reconciled later, in ``close_trade_gap`` (``reconcile_newbuild_technology_caps``),
once newbuild counts per vessel type are known; ``transfer_technology_uptake`` writes
the reconciled shares to the profile after the fleet evolution.
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
from navigate.simulation.fleet.composition import get_multiplier, get_multipliers
from navigate.simulation.fleet.conversion import is_retrofit_cycle
from navigate.simulation.fleet.marginal_saving import (
    calculate_marginal_technology_saving,
)
from navigate.simulation.fleet.package import (
    annual_costs_for_retrofit_steps,
    get_package_cost_flows,
    npv_for_newbuilds,
    npv_for_retrofit_steps,
    preprocess_packages,
)
from navigate.simulation.fleet.trip import bind_conditions_to_legs
from navigate.util import ROUND_OFF, TOLERANCE, YEAR, divide_nonzero

if TYPE_CHECKING:
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
        Index of the vessel in ``fleet.vessels``; it groups the proposals per vessel in
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
    # the fleet evolution later in the step
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
        Simulation timeline, days.
    idx
        Current time-step index.

    Returns
    -------
    list[FloatArray]
        Saving flow of each package, USD/year.
    """
    lifetime = vessel.lifetime.get()
    idx_ = np.s_[idx:]
    times = timeline[idx_]

    time_flow = timeline_to_yearly(vessel, idx, timeline)
    condition_legs = bind_conditions_to_legs(vessel.route)

    savings = []
    for package in packages:
        saving = calculate_marginal_technology_saving(
            vessel, condition_legs, package, idx_
        )
        saving_flow = np.interp(time_flow, times, saving)
        savings.append(trim_flow_to_lifetime(saving_flow, lifetime))

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

    preprocess_packages(
        fleet.technology_packages, fleet.package_cost_flows, timeline[idx]
    )

    # the fleet count before newbuilds is the denominator of both the retrofit and the
    # newbuild technology caps
    multipliers_total = float(sum(get_multipliers(fleet)))

    proposals = []
    for v, vessel in enumerate(fleet.vessels):
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
        Index of `vessel` in `fleet.vessels`.
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
    later in ``close_trade_gap``, once the newbuild counts per vessel type are known.

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
    cost_flows = get_package_cost_flows(
        fleet.technology_packages,
        fleet.package_cost_flows,
        basis.vessel.lifetime.get(),
    )
    npv = npv_for_newbuilds(basis.packages_saving, cost_flows, basis.discount_rate)
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

            # the step is amortized over the years the cohort still serves
            cost_flows = get_package_cost_flows(
                fleet.technology_packages, fleet.package_cost_flows, remaining
            )
            npv = npv_for_retrofit_steps(
                package_idx,
                basis.packages_saving,
                cost_flows,
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
                cost_flows,
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
        for v in range(len(fleet.vessels)):
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

    for v, vessel in enumerate(fleet.vessels):
        multipliers_total = float(get_multiplier(fleet, v))
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
    for v, vessel in enumerate(fleet.vessels):
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
    for v, vessel in enumerate(fleet.vessels):
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
