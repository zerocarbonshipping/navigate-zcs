# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from navigate.core import assign_id, assign_integer, assign_value
from navigate.core.enum_ import SolverBackendID, SolverMethodID
from navigate.core.general_nodes._general_node import _GeneralNode


class BunkerOptions(_GeneralNode):
    def __init__(self) -> None:
        super().__init__()

        # external variables -----------------------------------------------------------
        self.solver: SolverBackendID = SolverBackendID.AUTOMATIC
        self.solver_method: SolverMethodID = SolverMethodID.DETERMINISTIC
        self.solution_tolerance: float = 1e-6
        self.threads: int = 0

        # fair-share
        self.fair_share_maximum_iterations: int = 50
        self.fair_share_tolerance: float = 1e-1

    # external methods (DSL attributes) ------------------------------------------------
    def set_solver(self, solver: str):
        """
        Set the solver backend for the bunker algorithm.

        Examples
        --------
        - AUTOMATIC
        - GUROBI
        - HIGHS

        Parameters
        ----------
        solver
            Solver backend. AUTOMATIC tries Gurobi first, falling back to HiGHS.
            GUROBI selects Gurobi (falls back to HiGHS if no license).
            HIGHS skips Gurobi and uses HiGHS directly.
        """
        self.solver = assign_id(solver, SolverBackendID)

    def set_solver_method(self, solver_method: str):
        """
        Set the LP solver method of the bunker algorithm.

        Examples
        --------
        - AUTOMATIC
        - DETERMINISTIC
        - NON_DETERMINISTIC

        Parameters
        ----------
        solver_method
            LP solver method used by HiGHS to solve LP's in the bunker algorithm.
        """
        self.solver_method = assign_id(solver_method, SolverMethodID)

    def set_solution_tolerance(self, solution_tolerance: float):
        """
        Set the solution tolerance of the bunker algorithm.

        This value has no impact on computational time. It is only used to avoid
        round-off errors in solution.

        Examples
        --------
        - 1e-6

        Parameters
        ----------
        solution_tolerance
            Tolerance used when transferring the BunkerAlgorithm solutions to profiles.
        """
        self.solution_tolerance = assign_value(
            solution_tolerance, lower=0, inclusive_lower=False
        )

    def set_threads(self, threads: float):
        """
        Set the number of threads used by the LP solver in the bunker algorithm.

        Notice that '0' corresponds to automatic thread selection.

        Examples
        --------
        - 2

        Parameters
        ----------
        threads
            Threads used by the LP solver in the bunker algorithm.
        """
        self.threads = assign_integer(threads, lower=0)

    def set_fair_share_maximum_iterations(self, fair_share_maximum_iterations: int):
        """
        Set the maximum iterations of the bunker algorithm's fair-share sequential LP.

        Examples
        --------
        - 50

        Parameters
        ----------
        fair_share_maximum_iterations
            Maximum iterations allowed for the sequential LP of the bunker algorithm.
        """
        self.fair_share_maximum_iterations = int(
            assign_value(fair_share_maximum_iterations, lower=1)
        )

    def set_fair_share_tolerance(self, fair_share_tolerance: float):
        """
        Set the fair-share tolerance of the bunker algorithm.

        Examples
        --------
        - 1e-1

        Parameters
        ----------
        fair_share_tolerance
            Tolerance used when checking convergence of fair-share bunker solution.
        """
        self.fair_share_tolerance = assign_value(
            fair_share_tolerance, lower=0.0, inclusive_lower=False
        )
