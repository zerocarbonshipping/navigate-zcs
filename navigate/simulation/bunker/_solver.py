# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Solver interface of the bunker algorithm.

The bunker builds, solves and reads its linear program through ``Model``. A solve
returns the solution ``Selection`` (``_selection``) selects among the optimal ones,
by further runs of the solver on the program as ``VectorModel`` holds it. The HiGHS
and Gurobi adapters implement both protocols; ``solver_backend`` chooses between
them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, NewType, Protocol

import numpy as np

if TYPE_CHECKING:
    from pathlib import Path

    from scipy import sparse

    from navigate.core.enum_ import SolveStatusID
    from navigate.util.types_ import BoolArray, FloatArray

# a column or row of a model, read and written only through that model
Variable = NewType("Variable", int)
Constraint = NewType("Constraint", int)

type Sense = Literal["==", "<=", ">="]

# a linear expression: each variable with its coefficient
type Terms = list[tuple[Variable, float]]

type Simplex = Literal["primal", "dual"]


@dataclass(frozen=True)
class Program:
    """
    A linear program in whole vectors, indexed by the handles of its model.

        min c'x   s.t.   b_lower <= A x <= b_upper,   x_lower <= x <= x_upper

    A constraint has its right-hand side as the one finite bound of its sense, or as
    both where it is an equality. A removed variable is fixed at zero and a removed
    constraint has no finite bound.
    """

    c: FloatArray
    A: sparse.csr_array
    x_lower: FloatArray
    x_upper: FloatArray
    b_lower: FloatArray
    b_upper: FloatArray

    @property
    def b(self) -> FloatArray:
        """Right-hand side of each constraint, infinite where it has no finite bound."""
        return np.where(np.isfinite(self.b_upper), self.b_upper, self.b_lower)

    @property
    def is_equality(self) -> BoolArray:
        """Whether each constraint is an equality."""
        is_equality: BoolArray = self.b_lower == self.b_upper
        return is_equality


class Model(Protocol):
    """A linear program the bunker builds incrementally, solves and reads."""

    def add_variable(self, name: str) -> Variable:
        """Add a non-negative continuous variable with a zero cost."""

    def add_constraint(
        self, sense: Sense, name: str, *, priced: bool = False
    ) -> Constraint:
        """
        Add an empty constraint, ``0 <sense> 0``.

        Only the dual of a priced constraint can be read after a solve.
        """

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
        """
        Solve the linear program and select one of its optimal solutions.

        The values and the duals of the priced constraints are those ``Selection``
        selects, by the linear program alone and not by the solver, its method or
        the order the model was built in. Where a run of the selection does not
        end optimal or cannot tell two solutions apart, the solver chooses among
        the optimal ones in its place (``_selection``).
        """

    @property
    def status(self) -> SolveStatusID:
        """Status of the last solve."""

    def value(self, variable: Variable) -> float:
        """Return the value of a variable at the last solution."""

    def dual(self, constraint: Constraint) -> float:
        """
        Return the dual value of a priced constraint at the last solution.

        It is a change of the total cost per unit its right-hand side rises by. Where
        the cost has a kink there, the duals of the priced constraints are the
        optimal ones that are largest along one direction, in which all their
        right-hand sides move together. Where the run along that direction does
        not end optimal, those of the constraints with a zero right-hand side, or
        all of them, are optimal ones the solver chose (``_selection``).
        """

    def rhs(self, constraint: Constraint) -> float:
        """Return the right-hand side of a constraint."""

    def compute_iis(self) -> list[str]:
        """
        Return the names of the constraints in an irreducible infeasible subset.

        The list is empty where the solver identifies none.
        """

    def write(self, path: Path) -> None:
        """Write the model to a file, in the format its extension names."""

    def write_iis(self, path: Path) -> None:
        """Write the IIS of the last ``compute_iis`` to a file, in LP format."""


class VectorModel[Basis](Protocol):
    """The linear program of a model in whole vectors, as a selection runs it."""

    def program(self) -> Program:
        """Return the costs, bounds and coefficients of the linear program."""

    def set_program(self, program: Program) -> None:
        """Set the costs and bounds of a program; its coefficients are not set."""

    def run(self, simplex: Simplex, basis: Basis) -> SolveStatusID:
        """
        Run the solver on the linear program, by a simplex method from a basis.

        The primal run is a selection's keyed run and the dual run its direction
        run. Two keys may differ by less than the tolerance of the model, so each
        takes the smallest tolerance the solver accepts on what its keys set: the
        primal run the optimality tolerance, as its keys are the costs, and the
        dual run the feasibility tolerance, as its keys scale the right-hand sides.
        """

    def values(self) -> FloatArray:
        """Return the value of every variable at the solution of the last run."""

    def duals(self) -> FloatArray:
        """Return the dual of every constraint at the solution of the last run."""

    def basis(self) -> Basis:
        """Return the basis of the last run."""


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
