# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Iterate the bunkering LP until the vessels' shares of the port fuel supply settle."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from numpy.linalg import norm

from navigate.bunker.constraints.fair_share_fuel import (
    update_fair_share_fuel_constraints,
)
from navigate.bunker.constraints.fuel_inertia import update_fuel_inertia_constraints
from navigate.bunker.optimize import optimize
from navigate.bunker.utils import get_port_name_to_indices
from navigate.core.enum_ import BunkerScopeID

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)


@dataclass
class FairShareSolutions:
    """
    The bunker solutions of consecutive fair-share iterations, in one key order.

    Parameters
    ----------
    keys
        Bunker variable keys, in the order of the arrays.
    previous
        Bunker solution of the previous iteration, tons.
    new
        Bunker solution of the latest iteration, tons.
    difference
        Absolute difference between the two solutions, tons.
    """

    keys: list[tuple]
    previous: FloatArray
    new: FloatArray
    difference: FloatArray


def perform_fair_share_iteration(alg: BunkerAlgorithm) -> bool:
    """
    Perform one iteration of the fair share algorithm.

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

    optimize(alg)

    converged = calculate_fair_share_solution_convergence(alg)

    if converged:
        return converged

    iteration = len(alg.fair_share_convergence_statistics["Norm"])
    logger.debug("Fair-share bunkering iteration %d did not converge.", iteration)

    update_fair_share_solution(alg)

    return False


def run_fair_share_solve(alg: BunkerAlgorithm) -> tuple[int, bool]:
    """
    Run the full fair-share solve loop.

    Initialize, constrain, optimize, then iterate until convergence or the maximum
    iteration limit.

    Parameters
    ----------
    alg
        The algorithm instance.

    Returns
    -------
    tuple[int, bool]
        The number of fair-share iterations performed and whether the solution
        converged.
    """
    initialize_fair_share_allocation(alg)
    update_fair_share_constraints(alg)

    optimize(alg)
    update_fair_share_solution(alg)

    max_iter = alg.options.fair_share_maximum_iterations
    converged = False
    i = 0

    while (not converged) and i < max_iter:
        converged = perform_fair_share_iteration(alg)
        i += 1

    return i, converged


def perform_flexibility_unit_cost_evaluation(alg: BunkerAlgorithm) -> None:
    """
    Evaluate the flexibility unit cost as each regulation's threshold shadow price.

    The unit cost is the cost of carbon, whether that is defined by the price
    ceiling (remedial unit cost) or the cheapest compliant fuel available at
    scale.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    for r, constraint in alg.regulation_threshold_flexibility.items():
        alg.flexible_unit_cost[r] = -constraint.Pi


def initialize_fair_share_allocation(alg: BunkerAlgorithm) -> None:
    """
    Initialize the fair-share allocations and convergence state of a solve.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    alg.fair_share_convergence_statistics = {}

    alg.previous_bunker = {}
    alg.allocation_fuel = {}
    alg.previously_released_fuel = {}

    # the bunker keys may differ from those of the previous solve
    alg.fair_share_solutions = None

    for v, p, f in alg.bunker:
        vessel = alg.vessels[v]
        port = vessel.route.ports[p]

        supply = np.float64(port.expectation.get_bunker_supply(f, alg.idx))

        # an infinite supply has no fair-share constraint: none was defined, or
        # it starts later or was removed
        if not np.isfinite(supply):
            continue

        port_name = port.name
        key = (v, port_name, f)

        # a port the route calls more than once is allocated once
        if key in alg.allocation_fuel:
            continue

        alg.previously_released_fuel[key] = False
        alg.allocation_fuel[key] = _get_fair_share(alg, vessel, port_name, f) * supply

    alg.fair_share_convergence_statistics.setdefault("Non-zero (%)", [])
    alg.fair_share_convergence_statistics.setdefault("Norm", [])
    alg.fair_share_convergence_statistics.setdefault("Max", [])


def update_fair_share_constraints(alg: BunkerAlgorithm) -> None:
    """
    Update the constraints for fair-share allocation of resources.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    for vessel in alg.vessels.values():
        update_fair_share_fuel_constraints(alg, vessel)

        # the inertia constraints follow the fair-share constraints, so they do not
        # clash with the allocations
        update_fuel_inertia_constraints(alg, vessel)


def update_fair_share_allocation(alg: BunkerAlgorithm) -> None:
    """
    Update each vessel's bunker fuel allocation by port using the fair-share principle.

    Uses a two-pass approach:

    Pass 1: Classify each vessel-port-fuel as bounded (wants more fuel) or unbounded
            (has surplus), and accumulate consumed supply by released vessels and total
            fair share of bounded vessels.

    Pass 2: For bounded vessels, distribute remaining supply (total supply minus
            consumed by released) proportionally by fair share. For released vessels,
            tighten allocation to actual consumption.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    tol = alg.options.solution_tolerance
    port_name_to_indices = {
        v: get_port_name_to_indices(vessel.route) for v, vessel in alg.vessels.items()
    }

    # supply consumed by the unbounded vessels, and fair share times multiplier
    # summed over the bounded vessels, per (port name, fuel)
    consumed_by_unbounded: dict[tuple[str, str], float] = {}
    bounded_fair_share: dict[tuple[str, str], float] = {}

    # per (vessel, port name, fuel)
    is_bounded: dict[tuple[str, str, str], bool] = {}
    previous_bunker: dict[tuple[str, str, str], float] = {}

    for v, port_name, f in alg.allocation_fuel:
        vessel = alg.vessels[v]
        key_vpf = (v, port_name, f)
        key_pf = (port_name, f)

        port_indices = port_name_to_indices[v][port_name]
        previous_bunker[key_vpf] = sum(
            alg.previous_bunker[(v, p, f)] for p in port_indices
        )

        # a vessel is bounded when it holds a non-zero share of the supply, wants
        # more of it (a non-zero shadow price) and has not released part of its
        # fair share before
        constraint = alg.fair_share_fuel[key_vpf]
        in_use = alg.allocation_fuel[key_vpf] > tol
        attractive = abs(constraint.Pi) > tol
        previously_released = alg.previously_released_fuel[key_vpf]
        is_bounded[key_vpf] = (not previously_released) and in_use and attractive

        if is_bounded[key_vpf]:
            fair_share = _get_fair_share(alg, vessel, port_name, f)
            bounded_fair_share.setdefault(key_pf, 0.0)
            bounded_fair_share[key_pf] += fair_share * alg.multipliers[v]
        else:
            consumed_by_unbounded.setdefault(key_pf, 0.0)
            consumed_by_unbounded[key_pf] += (
                previous_bunker[key_vpf] * alg.multipliers[v]
            )

    for v, port_name, f in alg.allocation_fuel:
        vessel = alg.vessels[v]
        port = alg.ports[port_name]
        key_vpf = (v, port_name, f)
        key_pf = (port_name, f)

        if is_bounded[key_vpf]:
            fair_share = _get_fair_share(alg, vessel, port_name, f)

            supply = np.float64(port.expectation.get_bunker_supply(f, alg.idx))
            remaining_supply = supply - consumed_by_unbounded.get(key_pf, 0.0)

            total_bounded = bounded_fair_share[key_pf]
            if total_bounded > tol:
                alg.allocation_fuel[key_vpf] = (
                    fair_share / total_bounded
                ) * remaining_supply
            else:
                alg.allocation_fuel[key_vpf] = 0.0

        elif key_pf in bounded_fair_share:
            # a released allocation is tightened only where a bounded vessel can
            # absorb the freed supply; otherwise releasing it would lose the supply
            alg.previously_released_fuel[key_vpf] = True
            alg.allocation_fuel[key_vpf] = previous_bunker[key_vpf]


def update_fair_share_solution(alg: BunkerAlgorithm) -> None:
    """
    Store the bunker solution as the previous one of the next iteration.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    alg.previous_bunker = {key: bunker.X for key, bunker in alg.bunker.items()}

    solutions = alg.fair_share_solutions
    if solutions is not None:
        for i, key in enumerate(solutions.keys):
            solutions.previous[i] = alg.previous_bunker[key]


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
    tol = alg.options.fair_share_tolerance

    solutions = alg.fair_share_solutions
    if solutions is None:
        keys = list(bunker.keys())
        n = len(keys)
        solutions = FairShareSolutions(keys, np.empty(n), np.empty(n), np.empty(n))
        for i, key in enumerate(keys):
            solutions.previous[i] = alg.previous_bunker[key]
        alg.fair_share_solutions = solutions

    difference = solutions.difference

    for i, key in enumerate(solutions.keys):
        solutions.new[i] = bunker[key].X

    np.subtract(solutions.previous, solutions.new, out=difference)
    np.abs(difference, out=difference)

    non_zero = np.count_nonzero(difference >= tol)
    non_zero_fraction = float(non_zero) / float(difference.size)

    norm_ = norm(difference)
    converged = bool(norm_ < tol)

    statistics = alg.fair_share_convergence_statistics
    statistics["Non-zero (%)"].append(int(non_zero_fraction * 100.0))
    statistics["Norm"].append(float(norm_))
    statistics["Max"].append(float(np.max(difference)))

    return converged


def _get_fair_share(
    alg: BunkerAlgorithm, vessel: Vessel, port_name: str, fuel_name: str
) -> float:
    """
    Return a vessel's fair share of a port's fuel supply in the algorithm's scope.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel holding the fair share.
    port_name
        Name of the port supplying the fuel.
    fuel_name
        Name of the fuel.

    Returns
    -------
    float
        Fraction of the port's supply of the fuel.
    """
    if alg.scope == BunkerScopeID.EXISTING:
        return vessel.expectation.get_fair_share_fuel_existing(port_name, fuel_name)

    return np.float64(
        vessel.expectation.get_fair_share_fuel_expected(port_name, fuel_name, alg.idx)
    )
