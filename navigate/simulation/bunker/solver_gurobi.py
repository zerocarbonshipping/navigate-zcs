# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Gurobi adapter of the bunker solver interface, and the Gurobi licence check.

``select_backend()`` and ``create_model()`` in
``navigate.simulation.bunker.solver_backend`` use them. gurobipy is optional and
untyped (mypy.ini skips it), so its objects are ``Any`` here.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from navigate.core.enum_ import SolveStatusID
from navigate.simulation.bunker.solver import Constraint, Variable

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.core.general_nodes.bunker_options import BunkerOptions
    from navigate.simulation.bunker.solver import Sense

try:
    import gurobipy as grb
except Exception:
    _IS_INSTALLED = False
else:
    _IS_INSTALLED = True

# GRB.EQUAL, GRB.LESS_EQUAL and GRB.GREATER_EQUAL, readable without gurobipy
_SENSES: dict[Sense, str] = {"==": "=", "<=": "<", ">=": ">"}


def is_gurobi_licensed() -> bool:
    """
    Return whether gurobipy is installed and licensed.

    gurobipy installs without a licence, and starting an environment is the only
    reliable check.

    Returns
    -------
    bool
        True if a Gurobi environment starts.
    """
    if not _IS_INSTALLED:
        return False

    try:
        env = _start_environment()
        env.dispose()
    except Exception:
        return False

    return True


def _start_environment() -> Any:
    """Return a started Gurobi environment that prints nothing, not even the banner."""
    env = grb.Env(empty=True)
    env.setParam("OutputFlag", 0)
    env.start()
    return env


class GurobiModel:
    """
    A linear program solved by Gurobi.

    Parameters
    ----------
    name
        Name of the model.
    options
        Settings of the bunker algorithm.
    """

    def __init__(self, name: str, options: BunkerOptions) -> None:
        self._env: Any = _start_environment()

        self._model: Any = grb.Model(name, env=self._env)
        params = self._model.Params
        params.Method = options.solver_method.value
        params.Threads = options.threads
        params.FeasibilityTol = options.solution_tolerance
        params.OptimalityTol = options.solution_tolerance

        # the gurobipy columns and rows, indexed by handle
        self._columns: list[Any] = []
        self._rows: list[Any] = []

    def add_variable(self, name: str) -> Variable:
        """Add a non-negative continuous variable with a zero cost."""
        variable = Variable(len(self._columns))
        column = self._model.addVar(vtype=grb.GRB.CONTINUOUS, name=name)

        self._columns.append(column)

        return variable

    def add_constraint(self, sense: Sense, name: str) -> Constraint:
        """Add an empty constraint, ``0 <sense> 0``."""
        constraint = Constraint(len(self._rows))
        row = self._model.addLConstr(grb.LinExpr(), _SENSES[sense], 0.0, name=name)

        self._rows.append(row)

        return constraint

    def set_coefficient(
        self, constraint: Constraint, variable: Variable, value: float
    ) -> None:
        """Set the coefficient of a variable in a constraint."""
        row = self._rows[constraint]
        column = self._columns[variable]
        self._model.chgCoeff(row, column, value)

    def set_rhs(self, constraint: Constraint, value: float) -> None:
        """Set the right-hand side of a constraint."""
        self._rows[constraint].RHS = value

    def set_cost(self, variable: Variable, value: float) -> None:
        """Set the objective coefficient of a variable."""
        self._columns[variable].Obj = value

    def set_upper_bound(self, variable: Variable, value: float) -> None:
        """Set the upper bound of a variable."""
        self._columns[variable].UB = value

    def remove_variable(self, variable: Variable) -> None:
        """Remove a variable from the linear program."""
        self._model.remove(self._columns[variable])

    def remove_constraint(self, constraint: Constraint) -> None:
        """Remove a constraint from the linear program."""
        self._model.remove(self._rows[constraint])

    def solve(self) -> None:
        """
        Solve the linear program.

        When presolve finds the model infeasible or unbounded without telling which,
        the model is solved once more with dual reductions off, which tells the two
        apart, and dual reductions are switched back on.
        """
        self._model.optimize()

        if self._model.Status == grb.GRB.INF_OR_UNBD:
            params = self._model.Params
            params.DualReductions = 0

            try:
                self._model.optimize()
            finally:
                params.DualReductions = 1

    @property
    def status(self) -> SolveStatusID:
        """Status of the last solve."""
        status = self._model.Status

        if status == grb.GRB.OPTIMAL:
            return SolveStatusID.OPTIMAL

        if status == grb.GRB.INFEASIBLE:
            return SolveStatusID.INFEASIBLE

        if status == grb.GRB.UNBOUNDED:
            return SolveStatusID.UNBOUNDED

        if status == grb.GRB.INF_OR_UNBD:
            return SolveStatusID.INFEASIBLE_OR_UNBOUNDED

        return SolveStatusID.OTHER

    def value(self, variable: Variable) -> float:
        """Return the value of a variable at the last solution."""
        value: float = self._columns[variable].X
        return value

    def dual(self, constraint: Constraint) -> float:
        """Return the dual value of a constraint at the last solution."""
        dual: float = self._rows[constraint].Pi
        return dual

    def rhs(self, constraint: Constraint) -> float:
        """Return the right-hand side of a constraint."""
        rhs: float = self._rows[constraint].RHS
        return rhs

    def compute_iis(self) -> list[str]:
        """Return the names of the constraints in an irreducible infeasible subset."""
        self._model.computeIIS()
        rows = self._model.getConstrs()
        return [row.ConstrName for row in rows if row.IISConstr]

    def write(self, path: Path) -> None:
        """Write the model to a file, in the format its extension names."""
        self._model.write(str(path))

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._model.dispose()
        with contextlib.suppress(Exception):
            self._env.dispose()
