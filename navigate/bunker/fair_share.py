# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

import logging

import numpy as np
from numpy.linalg import norm

from navigate.bunker.constraints.fair_share_fuel import update_fair_share_fuel_constraints
from navigate.bunker.constraints.fuel_inertia import update_fuel_inertia_constraints
from navigate.bunker.optimize import optimize
from navigate.bunker.utils import get_port_name_to_indices
from navigate.core.enum_ import BunkerScopeID

logger = logging.getLogger(__name__)


def perform_fair_share_iteration(alg: BunkerAlgorithm) -> bool:
    """
    Performs one iteration of the fair share algorithm.

    Parameters
    ----------
    alg
        The algorithm instance.

    Returns
    -------
    bool
        True if the fair share solution has converged, False otherwise.
    """

    update_fair_share_allocation(alg)
    update_fair_share_constraints(alg)

    # solve the updated model
    optimize(alg)

    converged = calculate_fair_share_solution_convergence(alg)

    if converged:
        return converged

    iteration = len(alg.fair_share_convergence_statistics['Norm'])
    logger.debug("Fair-share bunkering iteration %d did not converge.", iteration)

    update_fair_share_solution(alg)

    return False


def run_fair_share_solve(alg: BunkerAlgorithm) -> tuple[int, bool]:
    """
    Run the full fair-share solve loop: initialize, constrain, optimize,
    then iterate until convergence or the maximum iteration limit.

    Parameters
    ----------
    alg
        The algorithm instance.

    Returns
    -------
    tuple[int, bool]
        The number of fair-share iterations performed and whether the solution converged.
    """

    initialize_fair_share_allocation(alg)
    update_fair_share_constraints(alg)

    optimize(alg)
    update_fair_share_solution(alg)

    max_iter = alg.options.get_fair_share_maximum_iterations()
    converged = False
    i = 0

    while (not converged) and i < max_iter:
        converged = perform_fair_share_iteration(alg)
        i += 1

    return i, converged


def perform_flexibility_unit_cost_evaluation(alg: BunkerAlgorithm) -> None:
    """
    The flexibility unit cost is given by the cost of carbon, whether that is defined by the price ceiling
    (remedial unit cost) or the cheapest compliant fuel available at scale. This value is defined by the
    shadow price of the threshold constraint.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    for r, constraint in alg.regulation_threshold_flexibility.items():
        alg.flexible_unit_cost[r] = -constraint.Pi


def initialize_fair_share_allocation(alg: BunkerAlgorithm) -> None:
    """
    Initializes fair-share allocation variables and containers.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    # initialize the container for
    # fair-share convergence statistics
    alg.fair_share_convergence_statistics = {}

    # reset fair-share containers previous time-step
    alg.previous_bunker = {}
    alg.allocation_fuel = {}
    alg.previously_released_fuel = {}

    # reset pre-allocated convergence arrays (keys may have changed)
    alg.fair_share_bunker_keys = None
    alg.fair_share_solution_previous = None
    alg.fair_share_solution_new = None
    alg.fair_share_difference = None

    # allocate new initial fair-share
    for (v, p, f) in alg.bunker:

        vessel = alg.vessels[v]
        port = vessel.route.ports[p]

        supply = port.expectation.get_bunker_supply(f, alg.idx)

        # no constraint has been defined,
        # or it has been defined at a late
        # date or has been removed later
        if not np.isfinite(supply):
            continue

        port_name = port.get_name()
        key = (v, port_name, f)

        # if the port is a duplicate for that route,
        # it only needs to be defined once
        if key in alg.allocation_fuel:
            continue

        if alg.scope == BunkerScopeID.EXISTING:
            fair_share = vessel.expectation.get_fair_share_fuel_existing(port_name, f)
        else:
            fair_share = vessel.expectation.get_fair_share_fuel_expected(port_name, f, alg.idx)

        alg.previously_released_fuel[key] = False
        alg.allocation_fuel[key] = fair_share * supply

    # initialize fair-share convergence statistics
    alg.fair_share_convergence_statistics.setdefault('Non-zero (%)', [])
    alg.fair_share_convergence_statistics.setdefault('Norm', [])
    alg.fair_share_convergence_statistics.setdefault('Max', [])


def update_fair_share_constraints(alg: BunkerAlgorithm) -> None:
    """
    Updates the constraints for fair-share allocation of resources.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    for vessel in alg.vessels.values():

        # limit the individual fuel availability
        # of a vessel to its fair-share of the total
        update_fair_share_fuel_constraints(alg, vessel)

        # define vessel level inertia.
        # It has to be defined after
        # fair-share in order not to
        # clash with allocations
        update_fuel_inertia_constraints(alg, vessel)


def update_fair_share_allocation(alg: BunkerAlgorithm) -> None:
    """
    Updates the allocation of bunker fuel for each vessel at specific ports according to the
    fair-share principle. Uses a two-pass approach:

    Pass 1: Classify each vessel-port-fuel as bounded (wants more fuel) or unbounded (has surplus),
            and accumulate consumed supply by released vessels and total fair share of bounded vessels.

    Pass 2: For bounded vessels, distribute remaining supply (total supply minus consumed by released)
            proportionally by fair share. For released vessels, tighten allocation to actual consumption.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    tol = alg.options.get_solution_tolerance()
    port_name_to_indices = {v: get_port_name_to_indices(vessel.route) for v, vessel in alg.vessels.items()}

    consumed_by_unbounded = {}  # (port_name, f), total consumed supply by unbounded vessels
    bounded_fair_share = {}     # (port_name, f), sum of fair_share * multiplier for bounded vessels
    is_bounded = {}             # (v, port_name, f), bool
    previous_bunker = {}        # (v, port_name, f), float, previous consumption across port indices

    # ----- pass 1: classify and aggregate -----
    for (v, port_name, f) in alg.allocation_fuel:

        vessel = alg.vessels[v]
        port = alg.ports[port_name]
        key_vpf = (v, port_name, f)
        key_pf = (port_name, f)

        # find all port indices that correspond to the given port
        port_indices = port_name_to_indices[v][port_name]
        previous_bunker[key_vpf] = sum(alg.previous_bunker[(v, p, f)] for p in port_indices)

        # the vessel is considered bounded if it has
        # a non-zero share of the supply, has a demand
        # for additional supply (non-zero shadow price)
        # and has not previously released a part of
        # its fair-share
        constraint = alg.fair_share_fuel[key_vpf]
        in_use = alg.allocation_fuel[key_vpf] > tol
        attractive = abs(constraint.Pi) > tol
        previously_released = alg.previously_released_fuel[key_vpf]
        is_bounded[key_vpf] = (not previously_released) and in_use and attractive

        if is_bounded[key_vpf]:

            if alg.scope == BunkerScopeID.EXPECTED:
                fair_share = vessel.expectation.get_fair_share_fuel_expected(port_name, f, alg.idx)
            else:
                fair_share = vessel.expectation.get_fair_share_fuel_existing(port_name, f)

            # add up the total fraction of fair-share
            # in use by bounded vessels
            bounded_fair_share.setdefault(key_pf, 0.)
            bounded_fair_share[key_pf] += fair_share * alg.multipliers[v]
        else:

            # add up the total consumption of the supply
            # by unbounded vessels, that are using a
            # partial amount of their supply
            consumed_by_unbounded.setdefault(key_pf, 0.)
            consumed_by_unbounded[key_pf] += previous_bunker[key_vpf] * alg.multipliers[v]

    # ----- pass 2: update allocations -----
    for (v, port_name, f) in alg.allocation_fuel:

        vessel = alg.vessels[v]
        port = alg.ports[port_name]
        key_vpf = (v, port_name, f)
        key_pf = (port_name, f)

        if is_bounded[key_vpf]:

            if alg.scope == BunkerScopeID.EXPECTED:
                fair_share = vessel.expectation.get_fair_share_fuel_expected(port_name, f, alg.idx)
            else:
                fair_share = vessel.expectation.get_fair_share_fuel_existing(port_name, f)

            # calculate the residual supply not
            # in use by the unbounded vessels
            supply = port.expectation.get_bunker_supply(f, alg.idx)
            remaining_supply = supply - consumed_by_unbounded.get(key_pf, 0.)

            # redistrbute the unused supply
            # to those that are bounded
            total_bounded = bounded_fair_share[key_pf]
            if total_bounded > tol:
                alg.allocation_fuel[key_vpf] = (fair_share / total_bounded) * remaining_supply
            else:
                alg.allocation_fuel[key_vpf] = 0.

        else:

            # only tighten allocation when there are
            # bounded vessels that can absorb the freed
            # supply. If no vessel is bounded for this
            # port-fuel, releasing would lose supply
            # with no one to redistribute it to.
            if key_pf in bounded_fair_share:
                alg.previously_released_fuel[key_vpf] = True
                alg.allocation_fuel[key_vpf] = previous_bunker[key_vpf]


def update_fair_share_solution(alg: BunkerAlgorithm) -> None:
    """
    Updates the fair share solution values for the internal state.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    alg.previous_bunker = {key: bunker.X for key, bunker in alg.bunker.items()}

    # update pre-allocated arrays for convergence check
    if alg.fair_share_bunker_keys is not None:
        solution_previous = alg.fair_share_solution_previous
        for i, key in enumerate(alg.fair_share_bunker_keys):
            solution_previous[i] = alg.previous_bunker[key]


def calculate_fair_share_solution_convergence(alg: BunkerAlgorithm) -> bool:
    """
    Calculate the convergence of the fair share solution.

    Parameters
    ----------
    alg
        The algorithm instance.

    Returns
    -------
    bool
        True if the solution has sufficiently converged, otherwise False.
    """

    bunker = alg.bunker
    tol = alg.options.get_fair_share_tolerance()

    # lazy initialization of pre-allocated arrays
    if alg.fair_share_bunker_keys is None:
        alg.fair_share_bunker_keys = list(bunker.keys())
        n = len(alg.fair_share_bunker_keys)
        alg.fair_share_solution_previous = np.empty(n)
        alg.fair_share_solution_new = np.empty(n)
        alg.fair_share_difference = np.empty(n)
        for i, key in enumerate(alg.fair_share_bunker_keys):
            alg.fair_share_solution_previous[i] = alg.previous_bunker[key]

    solution_previous = alg.fair_share_solution_previous
    solution_new = alg.fair_share_solution_new
    difference = alg.fair_share_difference

    for i, key in enumerate(alg.fair_share_bunker_keys):
        solution_new[i] = bunker[key].X

    np.subtract(solution_previous, solution_new, out=difference)
    np.abs(difference, out=difference)

    # calculate the fraction of non-zeros
    non_zero = np.count_nonzero(difference >= tol)
    non_zero_fraction = float(non_zero) / float(difference.size)

    # calculate convergence criteria
    norm_ = norm(difference)
    converged = norm_ < tol

    # calculate additional statistics
    alg.fair_share_convergence_statistics['Non-zero (%)'].append(int(non_zero_fraction * 100.))
    alg.fair_share_convergence_statistics['Norm'].append(float(norm_))
    alg.fair_share_convergence_statistics['Max'].append(float(np.max(difference)))

    return converged
