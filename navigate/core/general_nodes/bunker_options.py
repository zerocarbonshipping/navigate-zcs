# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the BunkerOptions general node, the settings of the bunker algorithm."""

from __future__ import annotations

from navigate.core import assign_id, assign_integer, assign_value
from navigate.core.enum_ import SolverBackendID, SolverMethodID
from navigate.core.general_nodes._general_node import _GeneralNode


class BunkerOptions(_GeneralNode):
    """Hold the solver settings of the bunker algorithm."""

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
    def set_solver(self, solver: str) -> None:
        """Set the solver backend for the bunker algorithm."""
        self.solver = assign_id(solver, SolverBackendID)

    def set_solver_method(self, solver_method: str) -> None:
        """Set the LP solver method of the bunker algorithm."""
        self.solver_method = assign_id(solver_method, SolverMethodID)

    def set_solution_tolerance(self, solution_tolerance: float) -> None:
        """Set the solution tolerance of the bunker algorithm."""
        self.solution_tolerance = assign_value(
            solution_tolerance, lower=0, inclusive_lower=False, allow_expression=False
        )

    def set_threads(self, threads: float) -> None:
        """Set the number of threads used by the LP solver in the bunker algorithm."""
        self.threads = assign_integer(threads, lower=0)

    def set_fair_share_maximum_iterations(
        self, fair_share_maximum_iterations: float
    ) -> None:
        """Set the maximum iterations of the fair-share sequential LP."""
        self.fair_share_maximum_iterations = assign_integer(
            fair_share_maximum_iterations, lower=1
        )

    def set_fair_share_tolerance(self, fair_share_tolerance: float) -> None:
        """Set the fair-share tolerance of the bunker algorithm."""
        self.fair_share_tolerance = assign_value(
            fair_share_tolerance,
            lower=0.0,
            inclusive_lower=False,
            allow_expression=False,
        )
