# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the BunkerOptions general node, the solver and fair-share settings."""

from __future__ import annotations

from navigate.core import (
    SECTION_DEFINE,
    assign_id,
    assign_integer,
    assign_value,
    deck_attribute,
)
from navigate.core.enum_ import SolverBackendID, SolverMethodID
from navigate.core.general_nodes.general_node import GeneralNode
from navigate.core.node_type import BUNKER_OPTIONS


class BunkerOptions(GeneralNode):
    """Hold the settings of the LP solver and of the fair-share iteration."""

    type = BUNKER_OPTIONS

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
    @deck_attribute(SECTION_DEFINE)
    def set_solver(self, value: str) -> None:
        """Set the solver backend."""
        self.solver = assign_id(value, SolverBackendID)

    @deck_attribute(SECTION_DEFINE)
    def set_solver_method(self, value: str) -> None:
        """Set the LP solver method."""
        self.solver_method = assign_id(value, SolverMethodID)

    @deck_attribute(SECTION_DEFINE)
    def set_solution_tolerance(self, value: float) -> None:
        """Set the solution tolerance."""
        self.solution_tolerance = assign_value(
            value, lower=0.0, inclusive_lower=False, allow_expression=False
        )

    @deck_attribute(SECTION_DEFINE)
    def set_threads(self, value: float) -> None:
        """Set the number of threads of the LP solver."""
        self.threads = assign_integer(value, lower=0)

    @deck_attribute(SECTION_DEFINE)
    def set_fair_share_maximum_iterations(self, value: float) -> None:
        """Set the maximum number of fair-share iterations."""
        self.fair_share_maximum_iterations = assign_integer(value, lower=1)

    @deck_attribute(SECTION_DEFINE)
    def set_fair_share_tolerance(self, value: float) -> None:
        """Set the fair-share tolerance."""
        self.fair_share_tolerance = assign_value(
            value, lower=0.0, inclusive_lower=False, allow_expression=False
        )
