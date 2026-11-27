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

import numpy as np
from scipy import sparse

from navigate.core.enum_ import SolveStatusID
from navigate.simulation.bunker._selection import Selection
from navigate.simulation.bunker._solver import Program, Variable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from navigate.core.general_nodes.bunker_options import BunkerOptions
    from navigate.simulation.bunker._solver import (
        Constraint,
        MinimizingRule,
        Pool,
        Sense,
        Simplex,
    )
    from navigate.util.types_ import FloatArray, IntArray

try:
    import gurobipy as grb
except Exception:
    _IS_INSTALLED = False
else:
    _IS_INSTALLED = True

# GRB.EQUAL, GRB.LESS_EQUAL and GRB.GREATER_EQUAL, readable without gurobipy
_SENSES: dict[Sense, str] = {"==": "=", "<=": "<", ">=": ">"}

# the VBasis of every column and the CBasis of every row, indexed by handle
type _Basis = tuple[IntArray, IntArray]

# the values of Gurobi's Method parameter that are simplex methods
_METHODS: dict[Simplex, int] = {"primal": 0, "dual": 1}

# the VBasis of a column at its lower bound and the CBasis of a basic row, which a
# column and a row added since the basis was read start a run with
_AT_LOWER = -1
_BASIC = 0


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

        self._selection: Selection[_Basis] = Selection(options.solution_tolerance)

        # the gurobipy columns and rows, indexed by handle, and whether each is
        # still in the model
        self._columns: list[Any] = []
        self._rows: list[Any] = []
        self._column_is_live: list[bool] = []
        self._row_is_live: list[bool] = []

        # the columns and rows in the model with their handles, in the model's
        # order, as of the last solve
        self._live_columns: list[Any]
        self._live_rows: list[Any]
        self._column_handles: IntArray
        self._row_handles: IntArray

        # status of the first run of the last solve; Gurobi resets its own on every
        # change of the model, also those the selection makes and takes back
        self._status: int = grb.GRB.LOADED

    def add_variable(self, name: str, *, free: bool = False) -> Variable:
        """Add a continuous variable with a zero cost, non-negative unless free."""
        variable = Variable(len(self._columns))
        lower = -grb.GRB.INFINITY if free else 0.0
        column = self._model.addVar(lb=lower, vtype=grb.GRB.CONTINUOUS, name=name)

        self._columns.append(column)
        self._column_is_live.append(True)

        return variable

    def add_constraint(
        self, sense: Sense, name: str, *, priced: bool = False
    ) -> Constraint:
        """
        Add an empty constraint, ``0 <sense> 0``.

        Only the dual of a priced constraint can be read after a solve.
        """
        constraint = self._selection.add_constraint(name, priced=priced)
        row = self._model.addLConstr(grb.LinExpr(), _SENSES[sense], 0.0, name=name)

        self._rows.append(row)
        self._row_is_live.append(True)

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

    def remove_variable(self, variable: Variable) -> None:
        """Remove a variable from the linear program."""
        self._model.remove(self._columns[variable])
        self._column_is_live[variable] = False

    def remove_constraint(self, constraint: Constraint) -> None:
        """Remove a constraint from the linear program."""
        self._model.remove(self._rows[constraint])
        self._row_is_live[constraint] = False

    def set_selection_rules(
        self, pools: Sequence[Pool], minimizing_rules: Sequence[MinimizingRule]
    ) -> None:
        """Set the rules a solve selects its values by."""
        self._selection.set_rules(pools, minimizing_rules)

    def solve(self) -> None:
        """
        Solve the linear program and select one of its optimal solutions.

        The selection makes the first run (``_run_first``) and, where it ends
        optimal, its own runs.
        """
        model = self._model
        model.update()

        self._live_columns = model.getVars()
        self._live_rows = model.getConstrs()
        self._column_handles = np.flatnonzero(self._column_is_live)
        self._row_handles = np.flatnonzero(self._row_is_live)

        self._selection.solve(self, self._run_first)

    @property
    def status(self) -> SolveStatusID:
        """Status of the last solve."""
        return _solve_status(self._status)

    def value(self, variable: Variable) -> float:
        """Return the value of a variable at the last solution."""
        return self._selection.value(variable)

    def dual(self, constraint: Constraint) -> float:
        """Return the dual value of a priced constraint at the last solution."""
        return self._selection.dual(constraint)

    def binds(self, constraint: Constraint) -> bool:
        """Return whether a priced constraint binds at the last solution."""
        return self._selection.binds(constraint)

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

    def write_iis(self, path: Path) -> None:
        """
        Write the IIS of the last ``compute_iis`` to a file, in LP format.

        Gurobi writes an IIS to a path with the ``.ilp`` extension.
        """
        self._model.write(str(path))

    def program(self) -> Program:
        """
        Return the costs, bounds and coefficients of the linear program.

        A removed column reads as one fixed at zero without coefficients, and a
        removed row as one without bounds.
        """
        model = self._model
        columns = self._live_columns
        rows = self._live_rows
        inf = np.inf

        costs = self._by_column(model.getAttr("Obj", columns), removed=0.0)
        x_lower = self._by_column(model.getAttr("LB", columns), removed=0.0)
        x_upper = self._by_column(model.getAttr("UB", columns), removed=0.0)

        senses = np.array(model.getAttr("Sense", rows))
        rhs = np.array(model.getAttr("RHS", rows))
        b_lower = self._by_row(np.where(senses == "<", -inf, rhs), removed=-inf)
        b_upper = self._by_row(np.where(senses == ">", inf, rhs), removed=inf)

        entries = model.getA().tocoo()
        row_handles = self._row_handles[entries.row]
        column_handles = self._column_handles[entries.col]
        shape = (len(self._rows), len(self._columns))
        coefficients = sparse.csr_array(
            (entries.data, (row_handles, column_handles)), shape=shape
        )

        return Program(
            c=costs,
            A=coefficients,
            x_lower=x_lower,
            x_upper=x_upper,
            b_lower=b_lower,
            b_upper=b_upper,
        )

    def set_program(self, program: Program) -> None:
        """
        Set the costs and bounds of a program; its coefficients are not set.

        A row without bounds is set as ``<=`` an infinite right-hand side. The
        model is updated, so that what was set is what is read from it.
        """
        model = self._model
        columns = self._live_columns
        rows = self._live_rows

        b_lower = program.b_lower[self._row_handles]
        b_upper = program.b_upper[self._row_handles]
        is_equality = program.is_equality[self._row_handles]
        is_floor = np.isfinite(b_lower) & ~np.isfinite(b_upper)

        senses = np.where(is_equality, "=", np.where(is_floor, ">", "<"))
        rhs = np.where(is_floor, b_lower, b_upper)

        model.setAttr("Obj", columns, program.c[self._column_handles].tolist())
        model.setAttr("LB", columns, program.x_lower[self._column_handles].tolist())
        model.setAttr("UB", columns, program.x_upper[self._column_handles].tolist())
        model.setAttr("Sense", rows, senses.tolist())
        model.setAttr("RHS", rows, rhs.tolist())
        model.update()

    def set_basis(self, basis: _Basis) -> None:
        """
        Set the basis the next run starts from, in place of that of the last run.

        The basis is extended to the columns and rows added since it was read.
        """
        columns, rows = basis
        new_columns = np.full(len(self._columns) - columns.size, _AT_LOWER)
        new_rows = np.full(len(self._rows) - rows.size, _BASIC)

        columns = np.concatenate([columns, new_columns])[self._column_handles]
        rows = np.concatenate([rows, new_rows])[self._row_handles]

        self._model.setAttr("VBasis", self._live_columns, columns.tolist())
        self._model.setAttr("CBasis", self._live_rows, rows.tolist())

    def run(self, simplex: Simplex) -> SolveStatusID:
        """Run Gurobi on the linear program, by a simplex method."""
        params = self._model.Params
        method = params.Method
        feasibility = params.FeasibilityTol
        optimality = params.OptimalityTol

        params.Method = _METHODS[simplex]

        # the smallest tolerance Gurobi accepts, on feasibility and optimality, is
        # 1e-9, taken on what the selection sets (VectorModel.run)
        if simplex == "primal":
            params.OptimalityTol = 1e-9
        else:
            params.FeasibilityTol = 1e-9

        try:
            self._model.optimize()
        finally:
            params.Method = method
            params.FeasibilityTol = feasibility
            params.OptimalityTol = optimality

        return _solve_status(self._model.Status)

    def values(self) -> FloatArray:
        """Return the value of every variable at the solution of the last run."""
        values = self._model.getAttr("X", self._live_columns)
        return self._by_column(values, removed=0.0)

    def duals(self) -> FloatArray:
        """Return the dual of every constraint at the solution of the last run."""
        duals = self._model.getAttr("Pi", self._live_rows)
        return self._by_row(duals, removed=0.0)

    def basis(self) -> _Basis:
        """Return the basis of the last run."""
        model = self._model
        columns = np.full(len(self._columns), _AT_LOWER)
        rows = np.full(len(self._rows), _BASIC)

        columns[self._column_handles] = model.getAttr("VBasis", self._live_columns)
        rows[self._row_handles] = model.getAttr("CBasis", self._live_rows)

        return columns, rows

    def _run_first(self) -> bool:
        """
        Make the first run of a solve and return whether it ended optimal.

        The run starts from the basis of the last solve. When presolve finds the
        model infeasible or unbounded without telling which, the run is made once
        more with dual reductions off, which tells the two apart, and dual
        reductions are switched back on.
        """
        model = self._model
        basis = self._selection.basis

        if basis is not None:
            self.set_basis(basis)

        model.optimize()

        if model.Status == grb.GRB.INF_OR_UNBD:
            params = model.Params
            params.DualReductions = 0

            try:
                model.optimize()
            finally:
                params.DualReductions = 1

        self._status = model.Status

        is_optimal: bool = self._status == grb.GRB.OPTIMAL
        return is_optimal

    def _by_column(self, values: list[float], *, removed: float) -> FloatArray:
        """
        Return the values of the model's columns as a vector indexed by handle.

        Parameters
        ----------
        values
            Value of each column of the model, in the model's order.
        removed
            Value the vector holds at the handle of a removed column.

        Returns
        -------
        FloatArray
            One value per handle.
        """
        by_handle = np.full(len(self._columns), removed)
        by_handle[self._column_handles] = values
        return by_handle

    def _by_row(
        self, values: FloatArray | list[float], *, removed: float
    ) -> FloatArray:
        """
        Return the values of the model's rows as a vector indexed by handle.

        Parameters
        ----------
        values
            Value of each row of the model, in the model's order.
        removed
            Value the vector holds at the handle of a removed row.

        Returns
        -------
        FloatArray
            One value per handle.
        """
        by_handle = np.full(len(self._rows), removed)
        by_handle[self._row_handles] = values
        return by_handle

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self._model.dispose()
        with contextlib.suppress(Exception):
            self._env.dispose()


def _solve_status(status: int) -> SolveStatusID:
    """Return the solve status a Gurobi status code stands for."""
    if status == grb.GRB.OPTIMAL:
        return SolveStatusID.OPTIMAL

    if status == grb.GRB.INFEASIBLE:
        return SolveStatusID.INFEASIBLE

    if status == grb.GRB.UNBOUNDED:
        return SolveStatusID.UNBOUNDED

    if status == grb.GRB.INF_OR_UNBD:
        return SolveStatusID.INFEASIBLE_OR_UNBOUNDED

    return SolveStatusID.OTHER
