# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Iterate the bunkering LP until the vessels' shares of the port fuel supply settle."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from numpy.linalg import norm

from navigate.core.enum_ import BunkerScopeID
from navigate.simulation.bunker._constraints.fair_share_fuel import (
    update_fair_share_fuel_constraints,
)
from navigate.simulation.bunker._constraints.fuel_inertia import (
    update_fuel_inertia_constraints,
)
from navigate.simulation.bunker._indices import get_port_name_to_indices
from navigate.simulation.bunker._optimize import optimize

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)


def run_fair_share_solve(alg: BunkerAlgorithm) -> bool:
    """
    Solve the LP, then iterate the fair-share allocations until the solution settles.

    Parameters
    ----------
    alg
        The algorithm instance.

    Returns
    -------
    bool
        Whether the solution converged within the maximum number of iterations.
    """
    _initialize_fair_share_allocation(alg)
    _update_fair_share_constraints(alg)
    optimize(alg)

    released: set[tuple[str, str, str]] = set()
    alg.fair_share_convergence_statistics = {"Non-zero (%)": [], "Norm": [], "Max": []}

    for iteration in range(1, alg.options.fair_share_maximum_iterations + 1):
        previous = {key: alg.model.value(bunker) for key, bunker in alg.bunker.items()}

        _update_fair_share_allocation(alg, previous, released)
        _update_fair_share_constraints(alg)
        optimize(alg)

        change = _calculate_bunker_change(alg, previous)
        _update_convergence_statistics(alg, change)

        if norm(change) < alg.options.fair_share_tolerance:
            return True

        logger.debug("Fair-share bunkering iteration %d did not converge.", iteration)

    return False


def _initialize_fair_share_allocation(alg: BunkerAlgorithm) -> None:
    """
    Allocate each vessel its fair share of every finite port fuel supply it may bunker.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    alg.allocation_fuel = {}

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

        alg.allocation_fuel[key] = _get_fair_share(alg, vessel, port_name, f) * supply


def _update_fair_share_constraints(alg: BunkerAlgorithm) -> None:
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


def _update_fair_share_allocation(
    alg: BunkerAlgorithm,
    previous: dict[tuple[str, int, str], float],
    released: set[tuple[str, str, str]],
) -> None:
    r"""
    Update each vessel's allocation of the port fuel supplies from the previous solve.

    For each port q and fuel f whose supply S is finite, a vessel is bounded while its
    allocation and the magnitude of its fair-share constraint's shadow price exceed
    the solution tolerance and it has not released supply before. A bounded vessel v
    is allocated (port and fuel indices omitted):

        A_v = s_v / (\sum_{u \in B} m_u s_u) * (S - \sum_{u \notin B} m_u b_u)

    where B is the set of bounded vessels, s the fair share, m the vessel multiplier
    and b the fuel mass bunkered at the port, summed over its calls, in the previous
    solve; A_v is zero where the sum over B is within the solution tolerance. An
    unbounded vessel is released, A_v = b_v, where a bounded vessel can take up the
    supply it frees, and stays unbounded from then on.

    Parameters
    ----------
    alg
        The algorithm instance.
    previous
        Bunker solution of the previous solve, in tons.
    released
        Keys of the allocations released so far, extended in place.
    """
    tol = alg.options.solution_tolerance

    # per (vessel, port name, fuel): the fair share of a bounded vessel, and the fuel
    # an unbounded vessel bunkered at the port
    bounded: dict[tuple[str, str, str], float] = {}
    unbounded: dict[tuple[str, str, str], float] = {}

    # per (port name, fuel): the bounded fair shares and the unbounded bunkered fuel,
    # each times its vessel multiplier and summed over the vessels
    shares: dict[tuple[str, str], float] = {}
    consumed: dict[tuple[str, str], float] = {}

    for key in alg.allocation_fuel:
        v, port_name, f = key
        vessel = alg.vessels[v]
        port_fuel = (port_name, f)
        multiplier = alg.multipliers[v]

        in_use = alg.allocation_fuel[key] > tol
        binding = abs(alg.model.dual(alg.fair_share_fuel[key])) > tol

        if key not in released and in_use and binding:
            fair_share = _get_fair_share(alg, vessel, port_name, f)
            bounded[key] = fair_share
            shares[port_fuel] = shares.get(port_fuel, 0.0) + fair_share * multiplier
        else:
            indices = get_port_name_to_indices(vessel.route)[port_name]
            bunkered = sum(previous[v, p, f] for p in indices)
            unbounded[key] = bunkered
            consumed[port_fuel] = consumed.get(port_fuel, 0.0) + bunkered * multiplier

    for key, fair_share in bounded.items():
        _, port_name, f = key
        port = alg.ports[port_name]
        port_fuel = (port_name, f)

        supply = np.float64(port.expectation.get_bunker_supply(f, alg.idx))
        remaining = supply - consumed.get(port_fuel, 0.0)
        total = shares[port_fuel]

        if total > tol:
            alg.allocation_fuel[key] = (fair_share / total) * remaining
        else:
            alg.allocation_fuel[key] = 0.0

    # a vessel releases its allocation only where a bounded vessel can take up the
    # supply it frees; otherwise releasing it would lose the supply
    for key, bunkered in unbounded.items():
        _, port_name, f = key

        if (port_name, f) not in shares:
            continue

        released.add(key)
        alg.allocation_fuel[key] = bunkered


def _calculate_bunker_change(
    alg: BunkerAlgorithm, previous: dict[tuple[str, int, str], float]
) -> FloatArray:
    """
    Return the absolute change of each bunker variable since the previous solve.

    Parameters
    ----------
    alg
        The algorithm instance.
    previous
        Bunker solution of the previous solve, in tons.

    Returns
    -------
    FloatArray
        Absolute change, in tons, in the key order of the bunker variables.
    """
    previous_bunker = [previous[key] for key in alg.bunker]
    bunker = [alg.model.value(bunker) for bunker in alg.bunker.values()]

    return np.abs(np.subtract(bunker, previous_bunker, dtype=np.float64))


def _update_convergence_statistics(alg: BunkerAlgorithm, change: FloatArray) -> None:
    """
    Append the share of changed bunker variables and the norm and maximum change.

    Parameters
    ----------
    alg
        The algorithm instance.
    change
        Absolute change of each bunker variable since the previous solve, in tons.
    """
    non_zero = np.count_nonzero(change >= alg.options.fair_share_tolerance)
    non_zero_fraction = float(non_zero) / float(change.size)

    statistics = alg.fair_share_convergence_statistics
    statistics["Non-zero (%)"].append(int(non_zero_fraction * 100.0))
    statistics["Norm"].append(float(norm(change)))
    statistics["Max"].append(float(np.max(change)))


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
