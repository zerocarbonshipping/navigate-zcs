# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from navigate.core.enum_ import EnergyDemandTypeID, EnergyDemandTypePortID, UtilityID
from navigate.core.misc import TOLERANCE, YEAR
from navigate.core.nodes.node import Node
from navigate.core.nodes.technology import Technology
from navigate.core.nodes.vessel import Vessel
from navigate.economics.decision import calculate_asset_shares
from navigate.economics.flows import timeline_to_yearly
from navigate.fleet.heuristic import calculate_marginal_technology_saving
from navigate.fleet.operation import convert_to_regional_steps
from navigate.fleet.package import (
    Package,
    annual_costs_for_retrofit_steps,
    levelize_package_cost,
    npv_for_newbuilds,
    npv_for_retrofit_steps,
    preprocess_packages,
)
from navigate.fleet.saving import calculate_residual_energy
from navigate.fleet.utils import get_remaining_lifetime, is_retrofit_cycle
from navigate.util import divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet

logger = logging.getLogger(__name__)


def build_technology_packages(technologies: list[Technology]
                              ) -> tuple[list[Package], dict[int, int]]:
    """
    Sorts technologies by their CAPEX values and organizes them into packages.

    Processes a list of technologies, sorts them based on their CAPEX
    (Capital Expenditure) values, and then creates incremental subsets (packages)
    of technologies. Also produces a mapping dictionary to associate package
    indices with their respective technology indices from the original list.

    Parameters
    ----------
    technologies
        List of technologies to organize into packages.

    Returns
    -------
    Tuple of (packages, package_to_technology_map).
    """

    sorted_pairs = sorted(enumerate(technologies), key=lambda p: p[1].CAPEX.get())
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
    Define and initialize the technology adoption structure and initial package uptakes.

    Computes age-dependent initial technology adoption shares for each vessel increment.
    Each (vessel, technology) pair may have an uptake Curve with age on the x-axis,
    which is queried via interpolation at each increment's age.

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

    # apply per vessel, per age increment
    for v, vessel in enumerate(fleet.assets):
        vessel_name = vessel.get_name()
        truncation_count = 0
        truncated_tech_names: set[str] = set()

        # seeded uptake is charged as if installed at build (consistent with the
        # hull, which the instantaneous freight rate charges at full newbuild cost)
        package_rates = calculate_package_charter_rates(fleet.technology_packages, vessel)

        for inc in fleet.increments[v]:

            # build per-technology shares for this increment's age
            shares = np.zeros(len(fleet.technologies))
            for t, tech in enumerate(fleet.technologies):
                curve = fleet.initial_technology_share.get((vessel_name, tech.get_name()))
                if isinstance(curve, Node):
                    shares[t] = curve.get(inc.age)

            package_mix, truncated = shares_to_package_mix(
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


def shares_to_package_mix(technologies: list[Technology],
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
    tech_names = [t.get_name() for t in technologies]

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


def calculate_packages_saving(vessel: Vessel,
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
    Perform technology installation for all vessels in the fleet.

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

    retrofit_proposals: list[tuple[int, int, int, np.ndarray, float, np.ndarray]] = []
    for v, vessel in enumerate(fleet.assets):

        discount_rate = get_technology_discount_rate(fleet.technology_cost_of_capital, vessel)
        packages_saving = calculate_packages_saving(vessel, fleet.technology_packages, timeline, idx)

        # NPV is non-dimensionalized by the summed ship CAPEX so the sensitivity is unit-free.
        capex_npv = vessel.expectation.get_capex_npv(idx)

        # Unconstrained MNL on newbuild packages — reconciled in reconcile_newbuild_technology_caps
        # later in the timestep, once newbuild counts per vessel type are known.
        npv_newbuild = npv_for_newbuilds(packages_saving, fleet.technology_packages, discount_rate)
        choices, msg = calculate_asset_shares(npv_newbuild, UtilityID.SIGNED_REFERENCE,
                                              fleet.technology_sensitivity.get(), reference=capex_npv)
        fleet.newbuild_package_uptake[v] = choices

        if msg:
            logger.warning("%s newbuild technology uptake for %s %s", fleet, vessel, msg)

        # Unconstrained MNL on retrofit jumps — reconciled below using multipliers_total.
        collect_retrofit_proposals(fleet, vessel, v, packages_saving, discount_rate,
                                   capex_npv, time_step, retrofit_proposals)

    # Reconcile retrofit caps and apply the (possibly scaled) transitions.
    # Newbuild uptake is reconciled later in perform_fleet_evolution, where the profile transfer
    # is also issued so the stored uptake reflects the reconciled shares.
    reconcile_retrofit_technology_caps(fleet, retrofit_proposals, time_step, multipliers_total)

    for (vessel_idx, age_idx, package_idx, choices, _current, annual_costs) in retrofit_proposals:
        apply_uptake_transition(fleet, vessel_idx, age_idx, package_idx, choices, annual_costs)

    transfer_retrofit_uptake(fleet, retrofit_proposals, idx)

    # transfer the fleet-average carried technology charge before the cargo
    # charter reads it later in the same timestep
    transfer_technology_charter_rate(fleet, idx)


def get_technology_discount_rate(technology_cost_of_capital, vessel: Vessel) -> float:
    """
    Get the discount rate for technology investment decisions.

    Parameters
    ----------
    technology_cost_of_capital
        Cost of capital scalar for technology investments, or None to fall back to vessel.
    vessel
        The vessel to get the cost of capital from as fallback.

    Returns
    -------
    Discount rate.
    """

    if technology_cost_of_capital:
        return technology_cost_of_capital.get()

    return vessel.cost_of_capital.get()


def collect_retrofit_proposals(fleet: Fleet,
                               vessel: Vessel,
                               vessel_idx: int,
                               packages_saving: list[np.ndarray],
                               discount_rate: float,
                               capex_npv: float,
                               time_step: float,
                               proposals: list[tuple[int, int, int, np.ndarray, float, np.ndarray]],
                               ) -> None:
    """
    Walk every (age-increment, package_idx) pair for `vessel` and append unconstrained MNL retrofit
    proposals to `proposals`. The reconciler downstream scales them against the per-technology caps.

    Parameters
    ----------
    fleet
        The fleet owning the vessel.
    vessel
        Vessel type whose existing-fleet increments are evaluated for retrofitting.
    vessel_idx
        Index of `vessel` in `fleet.assets`; threaded through the proposal tuple so the apply step
        can address the correct multiplier slot.
    packages_saving
        Per-package marginal-saving cash-flows for `vessel`, indexed by package position.
    discount_rate
        Discount rate used in the retrofit NPV — fleet's technology cost-of-capital, falling back
        to the vessel's cost-of-capital.
    capex_npv
        Summed ship CAPEX NPV used to non-dimensionalize the retrofit NPV in the discrete choice model.
    time_step
        Current time-step size in dateline units.
    proposals
        Output list. Each appended entry is
        `(vessel_idx, age_idx, package_idx, choices, current, annual_costs)` where `choices` is the
        MNL share vector over retrofit steps, `current` is the eligible share of vessels actually
        sitting at `package_idx`, and `annual_costs` is the per-step levelized yearly charge that
        recovers the retrofit cost over the remaining vessel lifetime.
    """

    n_packages = len(fleet.technology_packages)

    retrofit_frequency = fleet.retrofit_frequency.get()
    technology_sensitivity = fleet.technology_sensitivity.get()
    dt_years = time_step / YEAR

    # the carried charge is levelized at the vessel cost of capital for consistency with
    # the freight-rate NPVs; the adoption decision keeps the technology discount rate
    vessel_discount_rate = vessel.cost_of_capital.get()

    for package_idx in range(n_packages - 1, -1, -1):
        for i, inc in enumerate(fleet.increments[vessel_idx]):

            if not is_retrofit_cycle(inc.age, retrofit_frequency, dt_years):
                continue

            remaining = get_remaining_lifetime(vessel, inc.age, inc.dt)
            if remaining <= 0:
                continue

            # Snapshot the share of vessels at this (vessel, age, package) — only this fraction can
            # actually transition. Used as an eligibility weight in the cap reconciler and the profile
            # writer; the snapshot is valid because proposals are applied in decreasing package_idx
            # order, so each apply_uptake_transition reads the same `current` value at apply time.
            current = float(inc.package_uptake[package_idx])
            if current <= 0.:
                continue

            npv = npv_for_retrofit_steps(package_idx, packages_saving,
                                         fleet.technology_packages, remaining, discount_rate)
            choices, _ = calculate_asset_shares(npv, UtilityID.SIGNED_REFERENCE,
                                                technology_sensitivity, reference=capex_npv)
            annual_costs = annual_costs_for_retrofit_steps(package_idx, fleet.technology_packages,
                                                           remaining, vessel_discount_rate)
            proposals.append((vessel_idx, i, package_idx, choices, current, annual_costs))


def reconcile_retrofit_technology_caps(fleet: Fleet,
                                       proposals: list[tuple[int, int, int, np.ndarray, float, np.ndarray]],
                                       time_step: float,
                                       multipliers_total: float) -> None:
    """
    Scale per-proposal retrofit `choices` so that, for every technology, the aggregate count of
    retrofits adopting it this timestep does not exceed `limit · multipliers_total · time_step / YEAR`.

    Each proposal carries a `current` eligibility share (the fraction of vessels at `(v, age)` that
    sit at `package_idx` and can therefore actually transition). The cap aggregate weights each
    tail-sum by `multiplier · current`, matching the count `apply_uptake_transition` will produce.

    Iterates technologies from outermost to innermost in the CAPEX-sorted package order. Scaling a
    single proposal's tail (`choices[k_start:]`) reduces retrofits for *all* technologies introduced
    by those steps, so processing the outer technologies first keeps the inner-technology aggregates
    monotonic.

    Model choice — where displaced mass goes
    ----------------------------------------
    When a cap on technology `i` binds, the displaced share of every proposal that adopts `i` is
    moved to `choices[0]` (the "stay" / no-retrofit option), not to the nearest feasible package
    below `i`. For a cumulative package list `[none, A, A+B]` with a binding cap on B, demand for
    `A+B` in excess of the cap is sent to `none`, even when A's own cap has slack — it is *not*
    reallocated to the `A`-only package.

    This is intentional. The package is the unit of choice in the DCM upstream; if decision makers
    ranked `A+B` highest and B is rationed, the model reads that as "defer this cycle" rather than
    "fall back to a package they did not pick".

    Parameters
    ----------
    fleet
        The fleet whose retrofit caps are being enforced.
    proposals
        Output of `collect_retrofit_proposals`. Mutated in place: each proposal's `choices` vector
        is rescaled when one of the technologies it covers has a binding cap.
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
        technology_name = sorted_technologies[i].get_name()
        cap = fleet.retrofit_technology_limit[technology_name].get() * budget

        # Cache (proposal, tail_sum) so the binding-case scale pass doesn't re-sum.
        contributions = []
        aggregate = 0.
        for (vessel_idx, age_idx, package_idx, choices, current, _annual_costs) in proposals:
            if package_idx > i:
                continue

            k_start = i - package_idx + 1
            if k_start >= len(choices):
                continue

            tail_sum = float(np.sum(choices[k_start:]))
            multiplier = float(fleet.increments[vessel_idx][age_idx].multiplier)
            weight = multiplier * current
            aggregate += weight * tail_sum
            contributions.append((choices, k_start, tail_sum))

        if aggregate <= cap + TOLERANCE:
            continue

        scale = cap / aggregate

        for choices, k_start, tail_sum in contributions:
            choices[k_start:] *= scale
            choices[0] += (1. - scale) * tail_sum


def reconcile_newbuild_technology_caps(fleet: Fleet,
                                       increments: np.ndarray,
                                       time_step: float,
                                       multipliers_total: float) -> None:
    """
    Scale `fleet.newbuild_package_uptake` so that, for every technology, the aggregate count of
    newbuild installs of it this timestep does not exceed
    `limit · multipliers_total · time_step / YEAR`.

    Iterates technologies from outermost to innermost in the CAPEX-sorted package order, mirroring
    the retrofit reconciliation. Reductions push displaced probability into the no-technology
    package (`uptake[0]`), preserving the invariant that each per-vessel uptake vector sums to 1.

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
        technology_name = sorted_technologies[i].get_name()
        cap = fleet.newbuild_technology_limit[technology_name].get() * budget
        k_start = i + 1

        contributions = []
        aggregate = 0.
        for v in range(len(fleet.assets)):
            uptake = fleet.newbuild_package_uptake[v]
            if k_start >= len(uptake) or increments[v] <= 0.:
                continue

            tail_sum = float(np.sum(uptake[k_start:]))
            aggregate += float(increments[v]) * tail_sum
            contributions.append((uptake, tail_sum))

        if aggregate <= cap + TOLERANCE:
            continue

        scale = cap / aggregate

        for uptake, tail_sum in contributions:
            uptake[k_start:] *= scale
            uptake[0] += (1. - scale) * tail_sum


def apply_uptake_transition(fleet: Fleet,
                            v_idx: int,
                            age_idx: int,
                            pkg_idx: int,
                            choices: np.ndarray,
                            annual_costs: np.ndarray
                            ) -> None:
    """
    Transition technology uptake from one package level to higher ones.

    Each moved share also adds its levelized retrofit charge to the increment's carried
    `technology_charter_rate`, so the retrofit cost is recovered as a constant yearly
    charge over the remaining vessel lifetime it was levelized against.

    Parameters
    ----------
    fleet
        The fleet owning the multiplier arrays.
    v_idx
        Vessel index.
    age_idx
        Age increment index.
    pkg_idx
        Current package index.
    choices
        Choice shares for transitioning to higher packages.
    annual_costs
        Levelized yearly charge per retrofit step, USD/year per vessel.
    """

    increment = fleet.increments[v_idx][age_idx]
    uptake = increment.package_uptake
    current = uptake[pkg_idx]
    moved_total = np.sum(choices[1:])

    uptake[pkg_idx] = current * (1. - moved_total)

    for step in range(1, len(choices)):
        uptake[pkg_idx + step] += current * choices[step]
        increment.technology_charter_rate += current * choices[step] * annual_costs[step]


def transfer_retrofit_uptake(fleet: Fleet,
                             proposals: list[tuple[int, int, int, np.ndarray, float, np.ndarray]],
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
        Reconciled and applied retrofit proposal list; each tuple is
        `(vessel_idx, age_idx, package_idx, choices, current, annual_costs)`.
    idx
        Current time-step index, used for the profile write.
    """

    if not fleet.technology_packages or not proposals:
        return

    sorted_technologies = fleet.technology_packages[-1].technologies
    if not sorted_technologies:
        return

    retrofit_counts: dict[tuple[int, int], float] = {}
    for (vessel_idx, age_idx, package_idx, choices, current, _annual_costs) in proposals:
        multiplier = float(fleet.increments[vessel_idx][age_idx].multiplier)
        weight = multiplier * current
        if weight <= 0.:
            continue

        for i in range(package_idx, len(sorted_technologies)):
            k_start = i - package_idx + 1
            if k_start >= len(choices):
                break

            # `choices` is post-reconciliation post-application; the tail-sum has not been mutated
            # by `apply_uptake_transition` because that function only reads choices and rewrites
            # the per-increment package_uptake — the proposal vector itself is preserved.
            retrofit_counts[(vessel_idx, i)] = (retrofit_counts.get((vessel_idx, i), 0.)
                                                + weight * float(np.sum(choices[k_start:])))

    for v, vessel in enumerate(fleet.assets):
        multipliers_total = float(sum(inc.multiplier for inc in fleet.increments[v]))
        for i, technology in enumerate(sorted_technologies):
            count = retrofit_counts.get((v, i), 0.)
            share = divide_nonzero(count, multipliers_total)
            fleet.profile.set_retrofit_technology_uptake(vessel.get_name(), technology.get_name(),
                                                         idx, share)


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
            fleet.profile.set_newbuild_technology_uptake(vessel.get_name(), technology.get_name(), idx, nb_uptake)

            # transfer average fleet uptake
            avg_uptake = 0.
            weight = 0.
            for inc in fleet.increments[v]:
                inc_uptake = float(np.sum(inc.package_uptake[p:]))
                avg_uptake += inc_uptake * inc.multiplier
                weight += inc.multiplier

            avg_uptake = divide_nonzero(avg_uptake, weight)
            fleet.profile.set_technology_uptake(vessel.get_name(), technology.get_name(), idx, avg_uptake)


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
    fleet.transfer_operational_saving_to_vessels()

    for v, vessel in enumerate(fleet.assets):
        route = vessel.route
        expectation = vessel.expectation

        n_legs = route.get_number_of_legs()
        n_ports = route.get_number_of_ports()

        raw_sea = expectation.get_raw_energy_sea(idx=idx)
        raw_port = expectation.get_raw_energy_port(idx=idx)

        saving_sea = expectation.get_operational_saving_fraction_sea()
        saving_port = expectation.get_operational_saving_fraction_port()

        # Apply operational savings (zero-cost reductions: JIT, weather routing, etc.)
        op_sea = {d: [np.asarray(leg, dtype=float) * (1. - saving_sea[d])
                      for leg in raw_sea[d]]
                  for d in EnergyDemandTypeID}
        op_port = {d: [np.asarray(port, dtype=float) * (1. - saving_port[d])
                       for port in raw_port[d]]
                   for d in EnergyDemandTypePortID}

        # Store operational energy on expectation and profile
        vessel.expectation.set_operational_energy_sea(idx, op_sea)
        vessel.expectation.set_operational_energy_port(idx, op_port)

        vessel.profile.set_operational_energy_sea(
            idx, {d: float(np.sum(op_sea[d])) for d in EnergyDemandTypeID})
        vessel.profile.set_operational_energy_port(
            idx, {d: float(np.sum(op_port[d])) for d in EnergyDemandTypePortID})

        regional_op_sea = convert_to_regional_steps(vessel, op_sea)
        vessel.expectation.set_regional_operational_energy_sea(idx, regional_op_sea)

        # Pre-compute arrays for use in saving/residual calculations
        op_sea_arr = {d: np.asarray(op_sea[d], dtype=float) for d in EnergyDemandTypeID}
        op_port_arr = {d: np.asarray(op_port[d], dtype=float) for d in EnergyDemandTypePortID}

        # Weighted sum of savings across increments + packages
        # Technology savings are now computed relative to operational energy
        total_weight = 0.
        total_saving_sea = {d: np.zeros(n_legs, dtype=float) for d in EnergyDemandTypeID}
        total_saving_port = {d: np.zeros(n_ports, dtype=float) for d in EnergyDemandTypePortID}

        for inc in fleet.increments[v]:
            uptake_i = inc.package_uptake  # shape: (n_packages,)

            for p, package in enumerate(fleet.technology_packages):
                w = float(inc.multiplier) * float(uptake_i[p])
                if w <= 0.:
                    continue

                residual_sea, residual_port = calculate_residual_energy(vessel, package, np.s_[idx])

                # Saving = operational - residual; accumulate w * saving
                for demand, residual in residual_sea.items():
                    total_saving_sea[demand] += w * (op_sea_arr[demand] - np.asarray(residual, dtype=float))

                for demand, residual in residual_port.items():
                    total_saving_port[demand] += w * (op_port_arr[demand] - np.asarray(residual, dtype=float))

                total_weight += w

        # Compute uptake-weighted average shore power capacity
        total_shore_capacity = 0.
        for inc in fleet.increments[v]:
            uptake_i = inc.package_uptake
            for p, package in enumerate(fleet.technology_packages):
                w = float(inc.multiplier) * float(uptake_i[p])
                if w <= 0.:
                    continue
                total_shore_capacity += w * package.shore_power_capacity

        avg_shore_capacity = total_shore_capacity / total_weight if total_weight > 0. else 0.
        vessel.expectation.set_shore_power_capacity(idx, avg_shore_capacity)

        # If there is no effective uptake/weight, leave residual = operational (no technology change)
        if total_weight <= 0.:
            avg_residual_sea = op_sea_arr
            avg_residual_port = op_port_arr
        else:
            inv_w = 1. / total_weight
            avg_residual_sea = {
                d: op_sea_arr[d] - total_saving_sea[d] * inv_w
                for d in EnergyDemandTypeID
            }
            avg_residual_port = {
                d: op_port_arr[d] - total_saving_port[d] * inv_w
                for d in EnergyDemandTypePortID
            }

        # Write results back
        vessel.expectation.set_energy_sea(idx, avg_residual_sea)
        vessel.expectation.set_energy_port(idx, avg_residual_port)

        vessel.profile.set_energy_sea(idx, {d: float(arr.sum()) for d, arr in avg_residual_sea.items()})
        vessel.profile.set_energy_port(idx, {d: float(arr.sum()) for d, arr in avg_residual_port.items()})

        regional_sea = convert_to_regional_steps(vessel, avg_residual_sea)
        vessel.expectation.set_regional_energy_sea(idx, regional_sea)
