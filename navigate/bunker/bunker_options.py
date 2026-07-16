# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core import GeneralNode, assign_id, assign_integer, assign_value
from navigate.core.enum_ import SolverBackendID, SolverMethodID


class BunkerOptions(GeneralNode):
    def __init__(self):
        super().__init__()

        self._solver = None                         # enum, solver backend (AUTOMATIC, GUROBI, HIGHS)
        self._solver_method = None                  # enum, LP solver method
        self._solution_tolerance = None             # float, the tolerance of the solution
        self._threads = None                        # int, the number of threads used for LP solves

        # fair-share
        self._fair_share_maximum_iterations = None      # int, maximum number of fair-share iterations
        self._fair_share_tolerance = None               # float, the tolerance of the fair-share convergence

    # external attributes set through the input deck -------------------------------------------------------------------
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

        self._solver = assign_id(solver, SolverBackendID)

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

        self._solver_method = assign_id(solver_method, SolverMethodID)

    def set_solution_tolerance(self, solution_tolerance: float):
        """
        Set the solution tolerance of the bunker algorithm.

        This value has no impact on computational time. It is only used to avoid round-off errors in solution.

        Examples
        --------
        - 1e-6

        Parameters
        ----------
        solution_tolerance
            Tolerance used when transferring the BunkerAlgorithm solutions to profiles.
        """

        self._solution_tolerance = assign_value(solution_tolerance, lower=0, inclusive_lower=False)

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

        self._threads = assign_integer(threads, lower=0)

    def set_fair_share_maximum_iterations(self, fair_share_maximum_iterations: int):
        """
        Set the maximum iterations of the fair-share sequential LP of the bunker algorithm.

        Examples
        --------
        - 50

        Parameters
        ----------
        fair_share_maximum_iterations
            Maximum iterations allowed for the sequential LP of the bunker algorithm.
        """

        self._fair_share_maximum_iterations = int(assign_value(fair_share_maximum_iterations, lower=1))

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

        self._fair_share_tolerance = assign_value(fair_share_tolerance, lower=0., inclusive_lower=False)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):

        if self._solver is None:
            self._solver = SolverBackendID.AUTOMATIC

        if self._solver_method is None:
            self._solver_method = SolverMethodID.DETERMINISTIC

        if self._solution_tolerance is None:
            self._solution_tolerance = 1e-6

        if self._threads is None:
            self._threads = 0

        if self._fair_share_maximum_iterations is None:
            self._fair_share_maximum_iterations = 50

        if self._fair_share_tolerance is None:
            self._fair_share_tolerance = 1e-1

    def get_solver(self):
        return self._solver

    def get_solver_method(self):
        return self._solver_method

    def get_solution_tolerance(self):
        return self._solution_tolerance

    def get_threads(self):
        return self._threads

    def get_fair_share_maximum_iterations(self):
        return self._fair_share_maximum_iterations

    def get_fair_share_tolerance(self):
        return self._fair_share_tolerance
