# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Solver interface of the bunker algorithm.

The bunker builds, solves and reads its linear program through ``Model``. The HiGHS
and Gurobi adapters implement it; ``solver_backend`` chooses between them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NewType, Protocol

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.core.enum_ import SolveStatusID

# a column or row of a model, read and written only through that model
Variable = NewType("Variable", int)
Constraint = NewType("Constraint", int)

type Sense = Literal["==", "<=", ">="]

# a linear expression: each variable with its coefficient
type Terms = list[tuple[Variable, float]]


class Model(Protocol):
    """A linear program the bunker builds incrementally, solves and reads."""

    def add_variable(self, name: str) -> Variable:
        """Add a non-negative continuous variable with a zero cost."""

    def add_constraint(self, sense: Sense, name: str) -> Constraint:
        """Add an empty constraint, ``0 <sense> 0``."""

    def set_coefficient(
        self, constraint: Constraint, variable: Variable, value: float
    ) -> None:
        """Set the coefficient of a variable in a constraint."""

    def set_rhs(self, constraint: Constraint, value: float) -> None:
        """Set the right-hand side of a constraint."""

    def set_cost(self, variable: Variable, value: float) -> None:
        """Set the objective coefficient of a variable."""

    def set_upper_bound(self, variable: Variable, value: float) -> None:
        """Set the upper bound of a variable."""

    def remove_variable(self, variable: Variable) -> None:
        """Remove a variable from the linear program."""

    def remove_constraint(self, constraint: Constraint) -> None:
        """Remove a constraint from the linear program."""

    def solve(self) -> None:
        """Solve the linear program."""

    @property
    def status(self) -> SolveStatusID:
        """Status of the last solve."""

    def value(self, variable: Variable) -> float:
        """Return the value of a variable at the last solution."""

    def dual(self, constraint: Constraint) -> float:
        """Return the dual value of a constraint at the last solution."""

    def rhs(self, constraint: Constraint) -> float:
        """Return the right-hand side of a constraint."""

    def compute_iis(self) -> list[str]:
        """
        Return the names of the constraints in an irreducible infeasible subset.

        The list is empty where the solver identifies none.
        """

    def write(self, path: Path) -> None:
        """Write the model to a file, in the format its extension names."""


def evaluate(model: Model, terms: Terms) -> float:
    """
    Evaluate a sum of variable-coefficient terms at the last solution.

    Parameters
    ----------
    model
        The model the variables belong to.
    terms
        Each variable with its coefficient.

    Returns
    -------
    float
        The sum of the coefficient-value products.
    """
    return sum(coefficient * model.value(variable) for variable, coefficient in terms)
