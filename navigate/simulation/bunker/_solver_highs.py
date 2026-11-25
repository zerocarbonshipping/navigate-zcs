# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
HiGHS adapter of the bunker solver interface.

``create_model()`` in ``navigate.simulation.bunker.solver_backend`` builds it.
"""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import highspy
import numpy as np
from highspy import (
    HighsModelStatus,
    HighsStatus,
    IisStatus,
    IisStrategy,
)
from scipy import sparse

from navigate.core.enum_ import SolveStatusID
from navigate.simulation.bunker._selection import Selection
from navigate.simulation.bunker._solver import Program, Variable

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.general_nodes.bunker_options import BunkerOptions
    from navigate.simulation.bunker._solver import (
        Constraint,
        MinimizingRule,
        Pool,
        Sense,
        Simplex,
    )
    from navigate.util.types_ import FloatArray, IntArray

logger = logging.getLogger(__name__)

_PRIMAL = highspy.simplex_constants.kSimplexStrategyPrimal.value
_DUAL = highspy.simplex_constants.kSimplexStrategyDual.value


class _Strategy(NamedTuple):
    """The options of HiGHS that differ between two runs, as one run takes them."""

    solver: str = "simplex"
    simplex_strategy: int = _DUAL
    presolve: str = "off"
    run_crossover: str = "off"
    cost_perturbation: float = 1.0
    smallest_feasibility_tolerance: bool = False
    smallest_optimality_tolerance: bool = False


# the strategies of a solve's first run: interior point needs no basis, so it runs
# on a model that grew; dual simplex starts from the basis of the last solve, in
# few pivots. Dual simplex is also the run before an IIS.
_INTERIOR_POINT = _Strategy(solver="ipm", presolve="on", run_crossover="on")
_DUAL_SIMPLEX = _Strategy()

# the strategies of the selection's runs: the runs of the rules are primal, the
# direction run is dual, and each takes the smallest tolerance on what the
# selection sets (VectorModel.run). The direction run starts from duals
# that its costs make feasible, which a perturbation of the costs would undo, and
# a perturbed run ends without a status once in some hundred solves.
_STRATEGIES: dict[Simplex, _Strategy] = {
    "primal": _Strategy(simplex_strategy=_PRIMAL, smallest_optimality_tolerance=True),
    "dual": _Strategy(cost_perturbation=0.0, smallest_feasibility_tolerance=True),
}

# the IIS and the simplex run before it can take minutes on a large model and only
# delay the error message; a minute is long enough for the models that finish
_IIS_SECONDS = 60.0


class _Highs(highspy.Highs):
    """HiGHS with its change of many row bounds declared."""

    # highspy has the method, and the stubs of the pinned 1.15.1 leave it out
    if TYPE_CHECKING:

        def changeRowsBounds(
            self,
            num_rows: int,
            rows: IntArray,
            lower_bounds: FloatArray,
            upper_bounds: FloatArray,
        ) -> HighsStatus: ...


class HighsModel:
    """
    A linear program solved by HiGHS.

    Parameters
    ----------
    name
        Unused; highspy has no call to name the model.
    options
        Settings of the bunker algorithm; HiGHS chooses its method per solve and
        does not read the solver method.
    """

    def __init__(self, name: str, options: BunkerOptions) -> None:
        tolerance = options.solution_tolerance

        self._highs: _Highs = _Highs()
        self._highs.setOptionValue("output_flag", False)
        self._highs.setOptionValue("threads", options.threads)

        # the feasibility and optimality tolerance of a run, unless its strategy
        # takes the smallest
        self._tolerance: float = tolerance

        # an IIS found from the LP itself and reduced to an irreducible set; the
        # default light strategy returns no rows at all
        iis_strategy = (
            IisStrategy.kIisStrategyFromLp.value
            | IisStrategy.kIisStrategyIrreducible.value
        )
        self._highs.setOptionValue("iis_strategy", iis_strategy)

        self._highs.setOptionValue("iis_time_limit", _IIS_SECONDS)

        self._selection: Selection[highspy.HighsBasis] = Selection(tolerance)

        self._row_senses: list[Sense] = []
        self._row_rhs: list[float] = []

        # the names of the columns and rows, passed to HiGHS only where it reads
        # them, into an IIS or a file: HiGHS copies the names it holds in every run
        self._column_names: list[str] = []
        self._row_names: list[str] = []

        # the last-written coefficients of each row, to skip redundant changeCoeff
        # calls
        self._row_coefficients: list[dict[Variable, float]] = []

        # the coefficients as last read from HiGHS, None once any changed
        self._coefficients: sparse.csr_array | None = None

        # the costs and bounds HiGHS holds while a selection runs, as last read or
        # set, to pass it only those that change
        self._program: Program

        # status of the first run of the last solve; HiGHS resets its own on every
        # change of the model, also those the selection makes and takes back
        self._status: HighsModelStatus = HighsModelStatus.kNotset

        # the IIS of the last compute_iis, None where HiGHS vouched for none
        self._iis_model: highspy.HighsModel | None = None

        # whether rows or columns were added since the last solve; removing only
        # changes bounds and so does not count as growth
        self._model_grew: bool = True

        # deferred row-bound, cost and upper-bound changes, applied when the model
        # is next solved
        self._pending_row_bounds: dict[Constraint, tuple[float, float]] = {}
        self._pending_cost: dict[Variable, float] = {}
        self._pending_upper_bound: dict[Variable, float] = {}

    def add_variable(self, name: str, *, free: bool = False) -> Variable:
        """Add a continuous variable with a zero cost, non-negative unless free."""
        variable = Variable(len(self._column_names))
        lower_bound = -highspy.kHighsInf if free else 0.0

        self._highs.addVar(lower_bound, highspy.kHighsInf)
        self._model_grew = True
        self._coefficients = None

        self._column_names.append(name)

        return variable

    def add_constraint(
        self, sense: Sense, name: str, *, priced: bool = False
    ) -> Constraint:
        """
        Add an empty constraint, ``0 <sense> 0``.

        Only the dual of a priced constraint can be read after a solve.
        """
        constraint = self._selection.add_constraint(name, priced=priced)
        lower_bound, upper_bound = _row_bounds(sense, 0.0)

        self._highs.addRow(lower_bound, upper_bound, 0, [], [])
        self._model_grew = True
        self._coefficients = None

        self._row_senses.append(sense)
        self._row_rhs.append(0.0)
        self._row_names.append(name)
        self._row_coefficients.append({})

        return constraint

    def set_coefficient(
        self, constraint: Constraint, variable: Variable, value: float
    ) -> None:
        """Set the coefficient of a variable in a constraint."""
        coefficients = self._row_coefficients[constraint]
        if coefficients.get(variable) == value:
            return

        coefficients[variable] = value
        self._highs.changeCoeff(constraint, variable, value)
        self._coefficients = None

    def set_rhs(self, constraint: Constraint, value: float) -> None:
        """Set the right-hand side of a constraint."""
        sense = self._row_senses[constraint]

        self._row_rhs[constraint] = value
        self._pending_row_bounds[constraint] = _row_bounds(sense, value)

    def set_cost(self, variable: Variable, value: float) -> None:
        """Set the objective coefficient of a variable."""
        self._pending_cost[variable] = value

    def set_upper_bound(self, variable: Variable, value: float) -> None:
        """
        Set the upper bound of a non-negative variable.

        HiGHS takes both bounds at once, and the lower one is set to zero.
        """
        self._pending_upper_bound[variable] = value

    def remove_variable(self, variable: Variable) -> None:
        """
        Remove a variable from the linear program.

        The column stays in place, fixed to zero at zero cost. It is named after
        its index, so a variable added later may take its name.
        """
        self._highs.changeColBounds(variable, 0.0, 0.0)
        self._highs.changeColCost(variable, 0.0)
        self._column_names[variable] = f"removed_{variable}"

        self._pending_cost.pop(variable, None)
        self._pending_upper_bound.pop(variable, None)

    def remove_constraint(self, constraint: Constraint) -> None:
        """
        Remove a constraint from the linear program.

        The row stays in place with infinite bounds, so it always holds. It is named
        after its index, so a constraint added later may take its name.
        """
        self._highs.changeRowBounds(constraint, -highspy.kHighsInf, highspy.kHighsInf)
        self._row_names[constraint] = f"removed_{constraint}"
        self._pending_row_bounds.pop(constraint, None)

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
        self._flush_pending()
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
        return self._row_rhs[constraint]

    def compute_iis(self) -> list[str]:
        """
        Return the names of the constraints in an irreducible infeasible subset.

        The list is empty where HiGHS finds none, or finds an IIS it does not vouch
        for: a status other than ok, an invalid IIS, or a row not known to be in
        conflict, as after a time-out or on a badly scaled model.
        """
        self._iis_model = None

        # the IIS takes its names where HiGHS returns it, not where it is written
        self._pass_names()

        # after an interior point run HiGHS only narrows the IIS down to candidate
        # rows, a simplex run lets it prove the irreducible set
        self._set_strategy(_DUAL_SIMPLEX)
        self._highs.setOptionValue("time_limit", _IIS_SECONDS)
        self._highs.run()
        self._highs.setOptionValue("time_limit", highspy.kHighsInf)

        try:
            status, iis = self._highs.getIis()
        except Exception:
            return []

        if status != HighsStatus.kOk or not iis.valid_:
            return []

        rows = list(iis.row_index_)
        if any(iis.row_status_[row] != IisStatus.kIisStatusInConflict for row in rows):
            return []

        # a simplex re-run that ends optimal leaves a valid IIS with nothing in it
        if rows or iis.col_index_:
            self._iis_model = iis.model_

        return [self._row_names[row] for row in sorted(rows)]

    def write(self, path: Path) -> None:
        """
        Write the model to a file, in the format its extension names.

        A file HiGHS cannot write is logged as a warning.
        """
        self._pass_names()
        status = self._highs.writeModel(str(path))
        _warn_if_unwritten(status, path)

    def write_iis(self, path: Path) -> None:
        """
        Write the IIS of the last ``compute_iis`` to a file, in LP format.

        Nothing is written where HiGHS vouched for no IIS, or for an empty one.
        HiGHS writes LP format only to a path with the ``.lp`` extension, so the IIS
        is written to one in a temporary directory and moved to the path. A file
        HiGHS or the file system cannot write is logged as a warning.
        """
        if self._iis_model is None:
            return

        iis_highs = highspy.Highs()
        iis_highs.setOptionValue("output_flag", False)
        iis_highs.passModel(self._iis_model)

        # a failing file system counts as a failed write, so the infeasibility
        # error still follows
        try:
            with tempfile.TemporaryDirectory() as directory:
                lp_path = Path(directory) / "iis.lp"
                status = iis_highs.writeModel(str(lp_path))
                if status != HighsStatus.kError:
                    shutil.move(lp_path, path)
        except OSError:
            status = HighsStatus.kError

        _warn_if_unwritten(status, path)

    def program(self) -> Program:
        """
        Return the costs, bounds and coefficients of the linear program.

        The coefficients are read from HiGHS only when one changed since they were
        last read, as they are most of what there is to read. The costs and bounds
        are kept, for ``set_program`` to compare with.
        """
        highs = self._highs
        column_count = highs.getNumCol()
        row_count = highs.getNumRow()

        columns = np.arange(column_count, dtype=np.int32)
        rows = np.arange(row_count, dtype=np.int32)

        _, _, costs, x_lower, x_upper, _ = highs.getCols(column_count, columns)
        _, _, b_lower, b_upper, _ = highs.getRows(row_count, rows)

        if self._coefficients is None:
            _, starts, indices, values = highs.getRowsEntries(row_count, rows)
            pointers = np.append(starts, values.size)
            shape = (row_count, column_count)
            self._coefficients = sparse.csr_array(
                (values, indices, pointers), shape=shape
            )

        self._program = Program(
            c=costs,
            A=self._coefficients,
            x_lower=x_lower,
            x_upper=x_upper,
            b_lower=b_lower,
            b_upper=b_upper,
        )

        return self._program

    def set_program(self, program: Program) -> None:
        """
        Set the costs and bounds of a program; its coefficients are not set.

        Only the costs and bounds that differ from those HiGHS holds are passed to
        it: a change of them all takes HiGHS about as long as a run without pivots.
        HiGHS holds those ``program`` read at the start of the solve, or those of
        the program set since: nothing else changes them while a solve runs.
        """
        held = self._program
        highs = self._highs

        c = program.c
        columns = np.flatnonzero(c != held.c)
        highs.changeColsCost(columns.size, columns, c[columns])

        lower, upper = program.x_lower, program.x_upper
        columns = np.flatnonzero((lower != held.x_lower) | (upper != held.x_upper))
        highs.changeColsBounds(columns.size, columns, lower[columns], upper[columns])

        lower, upper = program.b_lower, program.b_upper
        rows = np.flatnonzero((lower != held.b_lower) | (upper != held.b_upper))
        highs.changeRowsBounds(rows.size, rows, lower[rows], upper[rows])

        self._program = program

    def set_basis(self, basis: highspy.HighsBasis) -> None:
        """Set the basis the next run starts from, in place of that of the last run."""
        self._highs.setBasis(basis)

    def run(self, simplex: Simplex) -> SolveStatusID:
        """
        Run HiGHS on the linear program, by a simplex method.

        Where HiGHS ends the run in an error, the run is repeated from no basis.
        HiGHS keeps the scaling of a model from one run to the next, and its dual
        simplex can fail from a basis under the scaling of an earlier state of the
        model.
        """
        self._set_strategy(_STRATEGIES[simplex])
        status = self._highs.run()

        if status == HighsStatus.kError:
            logger.debug("A HiGHS run of the bunkering LP ended in an error; repeated.")
            self._highs.clearSolver()
            self._highs.run()

        return _solve_status(self._highs.getModelStatus())

    def values(self) -> FloatArray:
        """Return the value of every variable at the solution of the last run."""
        solution = self._highs.getSolution()
        return np.array(solution.col_value)

    def duals(self) -> FloatArray:
        """Return the dual of every constraint at the solution of the last run."""
        solution = self._highs.getSolution()
        return np.array(solution.row_dual)

    def basis(self) -> highspy.HighsBasis:
        """Return the basis of the last run."""
        return self._highs.getBasis()

    def _run_first(self) -> bool:
        """
        Make the first run of a solve and return whether it ended optimal.

        When rows or columns were added since the last solve, the run is interior
        point with crossover. When only data changed, it is dual simplex from the
        basis of the last solve, which needs few pivots, and interior point after
        it where it ends non-optimal.
        """
        basis = self._selection.basis

        if self._model_grew or basis is None:
            self._set_strategy(_INTERIOR_POINT)
            self._highs.run()
            self._model_grew = False
        else:
            self._set_strategy(_DUAL_SIMPLEX)
            self.set_basis(basis)
            self._highs.run()

            if self._highs.getModelStatus() != HighsModelStatus.kOptimal:
                self._set_strategy(_INTERIOR_POINT)
                self._highs.run()

        self._status = self._highs.getModelStatus()

        return self._status == HighsModelStatus.kOptimal

    def _pass_names(self) -> None:
        """Pass HiGHS the column and row names, which an IIS and a file take from it."""
        highs = self._highs

        for column, name in enumerate(self._column_names):
            highs.passColName(column, _lp_name(name))

        for row, name in enumerate(self._row_names):
            highs.passRowName(row, _lp_name(name))

    def _flush_pending(self) -> None:
        """Apply the deferred row-bound, cost and upper-bound changes."""
        if self._pending_row_bounds:
            pending = self._pending_row_bounds
            count = len(pending)
            indices = np.array(list(pending), dtype=np.int32)
            bounds = np.array(list(pending.values()), dtype=np.float64)
            lower_bounds = bounds[:, 0]
            upper_bounds = bounds[:, 1]
            self._highs.changeRowsBounds(count, indices, lower_bounds, upper_bounds)
            pending.clear()

        if self._pending_cost:
            pending = self._pending_cost
            count = len(pending)
            indices = np.array(list(pending), dtype=np.int32)
            costs = np.array(list(pending.values()), dtype=np.float64)
            self._highs.changeColsCost(count, indices, costs)
            pending.clear()

        if self._pending_upper_bound:
            pending = self._pending_upper_bound
            count = len(pending)
            indices = np.array(list(pending), dtype=np.int32)
            lower_bounds = np.zeros(count, dtype=np.float64)
            upper_bounds = np.array(list(pending.values()), dtype=np.float64)
            self._highs.changeColsBounds(count, indices, lower_bounds, upper_bounds)
            pending.clear()

    def _set_strategy(self, strategy: _Strategy) -> None:
        """Set every option of a strategy, so that the next run inherits none."""
        highs = self._highs
        perturbation = strategy.cost_perturbation

        # the smallest tolerance HiGHS accepts, on feasibility and optimality, is 1e-10
        tolerance = self._tolerance
        feasibility = 1e-10 if strategy.smallest_feasibility_tolerance else tolerance
        optimality = 1e-10 if strategy.smallest_optimality_tolerance else tolerance

        highs.setOptionValue("solver", strategy.solver)
        highs.setOptionValue("presolve", strategy.presolve)
        highs.setOptionValue("run_crossover", strategy.run_crossover)
        highs.setOptionValue("simplex_strategy", strategy.simplex_strategy)
        highs.setOptionValue("primal_feasibility_tolerance", feasibility)
        highs.setOptionValue("dual_feasibility_tolerance", optimality)
        highs.setOptionValue("dual_simplex_cost_perturbation_multiplier", perturbation)


def _solve_status(status: HighsModelStatus) -> SolveStatusID:
    """Return the solve status a HiGHS model status stands for."""
    if status == HighsModelStatus.kOptimal:
        return SolveStatusID.OPTIMAL

    if status == HighsModelStatus.kInfeasible:
        return SolveStatusID.INFEASIBLE

    if status == HighsModelStatus.kUnbounded:
        return SolveStatusID.UNBOUNDED

    if status == HighsModelStatus.kUnboundedOrInfeasible:
        return SolveStatusID.INFEASIBLE_OR_UNBOUNDED

    # every other status, such as a reached limit or a solver error
    return SolveStatusID.OTHER


def _lp_name(name: str) -> str:
    """
    Return a name with each character an LP file cannot hold replaced by an underscore.

    The HiGHS LP writer drops every row name once one holds another character, or
    two rows share a name, and every column name likewise. The characters are those
    of ``kLegalLpFileColRowNameChar`` in HiGHS, without its two curly quotes.
    """
    return re.sub(r'[^A-Za-z0-9.!"#$%&(),;?@_{}~]', "_", name)


def _warn_if_unwritten(status: HighsStatus, path: Path) -> None:
    """Log a warning naming a file that HiGHS returned an error for writing."""
    if status == HighsStatus.kError:
        logger.warning("HiGHS could not write %s.", path)


def _row_bounds(sense: Sense, rhs: float) -> tuple[float, float]:
    """
    Return the row bounds of a constraint with a sense and right-hand side.

    Parameters
    ----------
    sense
        One of "==", "<=", ">=".
    rhs
        Right-hand side.

    Returns
    -------
    tuple[float, float]
        Lower and upper bound of the row.
    """
    if sense == "==":
        return rhs, rhs

    if sense == "<=":
        return -highspy.kHighsInf, rhs

    return rhs, highspy.kHighsInf
