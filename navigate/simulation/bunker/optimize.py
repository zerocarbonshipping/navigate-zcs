# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Solve the bunkering LP and act on a solve that did not end optimal."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID, SolveStatusID, TimingID
from navigate.exceptions import InfeasibleLPError, LPSolveError
from navigate.util import timed

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


@timed(TimingID.LP_SOLVE)
def optimize(alg: BunkerAlgorithm) -> None:
    """
    Optimize the built model and check the feasibility of the solution.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    alg.model.solve()
    check_solution(alg)


def check_solution(alg: BunkerAlgorithm) -> None:
    """
    Check that the last solve of the LP model found an optimal solution.

    An infeasible model raises after its IIS is computed and the model and its
    limiting constraints are written as LP files to the output directory. Every
    other status but optimal raises with the reason the solve ended.

    Parameters
    ----------
    alg
        The algorithm instance.

    Raises
    ------
    InfeasibleLPError
        If the model is infeasible.
    LPSolveError
        If the solve ended without an optimal solution for another reason.
    """
    status = alg.model.status

    if status == SolveStatusID.OPTIMAL:
        return

    if status == SolveStatusID.INFEASIBLE:
        iis = alg.model.compute_iis()

        alg.model.write(alg.output_directory / "bunkering_infeasible.ilp")
        alg.model.write(alg.output_directory / "bunkering_infeasible.lp")

        scope = "existing" if alg.scope == BunkerScopeID.EXISTING else "expected"
        raise InfeasibleLPError(
            f"Optimal bunkering was infeasible for {scope} bunkering"
            f" due to the IIS limiting constraint: {', '.join(iis)}."
        )

    reason = {
        SolveStatusID.UNBOUNDED: "the LP is unbounded",
        SolveStatusID.INFEASIBLE_OR_UNBOUNDED: "the LP is infeasible or unbounded",
        SolveStatusID.OTHER: "the solver stopped without an optimal solution",
    }[status]

    scope = alg.scope.name.lower()
    raise LPSolveError(f"Optimal bunkering failed for {scope} bunkering: {reason}.")
