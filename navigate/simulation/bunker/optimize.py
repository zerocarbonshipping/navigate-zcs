# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Solve the bunkering LP and act on a solve that did not end optimal."""

from __future__ import annotations

import timeit
from typing import TYPE_CHECKING

import navigate.simulation.bunker.solver as gp
from navigate.core.enum_ import BunkerScopeID
from navigate.exceptions import InfeasibleLPError

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def optimize(alg: BunkerAlgorithm) -> None:
    """
    Optimize the built model and check the feasibility of the solution.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    start = timeit.default_timer()

    alg.model.optimize()
    check_solution(alg)

    end = timeit.default_timer()
    alg.solve_time += end - start


def check_solution(alg: BunkerAlgorithm) -> None:
    """
    Check the solution of the LP model after a solve.

    An infeasible model raises, after its IIS is computed and the model and its
    limiting constraints are written as LP files to the output directory. A model
    reported infeasible or unbounded is solved again with dual reductions off and
    checked again; every other status returns without raising. On Gurobi, a re-solve
    that reports the model unbounded therefore returns as well. The HiGHS backend
    reports every status but optimal and infeasible as infeasible or unbounded and
    does not apply the dual-reductions switch, so such a model is solved again to the
    same status until the recursion limit is reached.

    Parameters
    ----------
    alg
        The algorithm instance.

    Raises
    ------
    InfeasibleLPError
        If the model is infeasible.
    """
    # dual reductions go back on after a solve that switched them off
    alg.model.Params.DualReductions = 1

    status = alg.model.Status

    if status == gp.OPTIMAL:
        return

    if status == gp.INFEASIBLE:
        alg.model.computeIIS()
        iis = [
            alg.model.ConstrName[i]
            for i, infeasible in enumerate(alg.model.IISConstr)
            if infeasible
        ]

        alg.model.write(str(alg.output_directory / "bunkering_infeasible.ilp"))
        alg.model.write(str(alg.output_directory / "bunkering_infeasible.lp"))

        scope = "existing" if alg.scope == BunkerScopeID.EXISTING else "expected"
        raise InfeasibleLPError(
            f"Optimal bunkering was infeasible for {scope} bunkering"
            f" due to the IIS limiting constraint: {', '.join(iis)}."
        )

    if status == gp.INF_OR_UNBD:
        alg.model.Params.DualReductions = 0
        optimize(alg)
