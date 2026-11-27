# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Solver interface of the bunker algorithm.

The bunker builds, solves and reads its linear program through ``Model``. A solve
returns the solution ``Selection`` (``_selection``) selects among the optimal ones,
by the rules the bunker sets, in further runs of the solver on the program as
``VectorModel`` holds it. The HiGHS and Gurobi adapters implement both protocols;
``solver_backend`` chooses between them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, NamedTuple, NewType, Protocol

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Sequence
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


class Pool(NamedTuple):
    """
    A ``<=`` constraint on a weighted sum of member variables, less an excess variable.

        sum_v n_v x_v - x_e <= b

    The weights n_v are the coefficients of the members in the constraint. The
    excess variable e, non-negative, relaxes the constraint at its cost and stands
    in no other constraint. The constraint is priced, and no constraint but those
    of the pools links two members of one pool. The pools of a model state the
    first rule of its selection, the share of room (``_selection``).
    """

    constraint: Constraint
    excess: Variable
    members: Sequence[Variable]


class MinimizingRule(NamedTuple):
    """
    A preference among the optimal solutions of a model: the least of an expression.

    The terms of the expression add up, so a variable may stand in several of them.
    Their coefficients must be large against the tolerance of the model: after the
    run of the rule, a variable stays free to move where that worsens the
    expression by at most twice that tolerance per unit: once through its own
    reduced cost, once through the constraints held free around it.
    """

    name: str
    terms: Terms


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

    def add_variable(self, name: str, *, free: bool = False) -> Variable:
        """
        Add a continuous variable with a zero cost.

        The variable is non-negative, or without a bound either way where it is free.
        """

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

    def remove_variable(self, variable: Variable) -> None:
        """Remove a variable from the linear program."""

    def remove_constraint(self, constraint: Constraint) -> None:
        """Remove a constraint from the linear program."""

    def set_selection_rules(
        self, pools: Sequence[Pool], minimizing_rules: Sequence[MinimizingRule]
    ) -> None:
        """
        Set the rules a solve selects its values by.

        The first rule is the share of room: the members of the one pool that
        binds each take the same share of their own room. Each minimizing rule
        then narrows the optimal solutions down to those at which its expression
        is least, among those the rules before it left, first rule first.

        The rules hold for every solve until they are set again, which the caller
        does where a pool or a member of one came or went, and where a term of an
        expression came, went or changed its coefficient. The weights of the
        members are read from the constraint of their pool at every solve.
        """

    def solve(self) -> None:
        """
        Solve the linear program and select one of its optimal solutions.

        The values and the duals of the priced constraints are those ``Selection``
        selects, by the rules and the linear program alone. Where the rules tell
        two solutions apart, the choice between them is not the solver's, its
        method's or that of the order the model was built in. Where they do not,
        or a run of the selection does not end optimal, the solver chooses among
        the optimal ones (``_selection``).

        The runs see the costs scaled by a power of two (``_selection``,
        Precision); after them the model holds the costs as set, and ``dual``
        returns duals of those.
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
        the cost has a kink there, the duals of the priced constraints are optimal
        ones that are largest along one direction, in which all their right-hand
        sides move together. Where several are, or the run along that direction
        does not end optimal, the solver chooses among them (``_selection``).
        """

    def binds(self, constraint: Constraint) -> bool:
        """
        Return whether a priced constraint binds at the last solution.

        It binds where its dual is non-zero at the tolerance of the model, which
        applies to the scaled costs, not to ``dual`` (``_selection``, Precision).
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

    def set_basis(self, basis: Basis) -> None:
        """Set the basis the next run starts from, in place of that of the last run."""

    def run(self, simplex: Simplex) -> SolveStatusID:
        """
        Run the solver on the linear program, by a simplex method.

        The run starts from the basis the model holds: that of its last run, or
        the one set since. A change of the program leaves that basis in place.

        The primal run is a run of a rule of a selection, and the dual run its
        direction run. Each takes the smallest tolerance the solver accepts on
        what the selection sets: the primal run the optimality tolerance, on its
        costs, and the dual run the feasibility tolerance, on its right-hand sides.
        The run of a minimizing rule so ends at the least of its expression also
        where two variables' coefficients in it differ by less than the tolerance
        of the model; the solutions it leaves to the next rule are cut at the
        tolerance of the model, not at the run's (``MinimizingRule``). The
        direction run likewise tells apart two priced constraints that bind only
        together where, relaxed in proportion to their sizes, the amounts they
        would allow differ by less than the tolerance of the model.
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
