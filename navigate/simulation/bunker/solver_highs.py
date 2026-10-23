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
from typing import TYPE_CHECKING

import highspy
import numpy as np
from highspy import (
    HighsBasisStatus,
    HighsModelStatus,
    HighsStatus,
    IisStatus,
    IisStrategy,
)

from navigate.core.enum_ import SolveStatusID
from navigate.simulation.bunker.solver import Constraint, Variable

if TYPE_CHECKING:
    from navigate.core.general_nodes.bunker_options import BunkerOptions
    from navigate.simulation.bunker.solver import Sense
    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)

# the two solve strategies; interior point solutions keep the fair-share
# iterations stable, simplex warm-starts cheaply from a saved basis
_INTERIOR_POINT = {"solver": "ipm", "run_crossover": "on", "presolve": "on"}
_SIMPLEX = {"solver": "simplex", "run_crossover": "off", "presolve": "off"}

# the IIS and the simplex run before it can take minutes on a large model and only
# delay the error message; a minute is long enough for the models that finish
_IIS_SECONDS = 60.0


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
        tolerance = float(options.solution_tolerance)

        self._highs: highspy.Highs = highspy.Highs()
        self._highs.setOptionValue("output_flag", False)
        self._highs.setOptionValue("threads", int(options.threads))
        self._highs.setOptionValue("primal_feasibility_tolerance", tolerance)
        self._highs.setOptionValue("dual_feasibility_tolerance", tolerance)

        # an IIS found from the LP itself and reduced to an irreducible set; the
        # default light strategy returns no rows at all
        iis_strategy = (
            IisStrategy.kIisStrategyFromLp.value
            | IisStrategy.kIisStrategyIrreducible.value
        )
        self._highs.setOptionValue("iis_strategy", iis_strategy)

        self._highs.setOptionValue("iis_time_limit", _IIS_SECONDS)

        self._num_cols: int = 0
        self._row_senses: list[Sense] = []
        self._row_rhs: list[float] = []
        self._row_names: list[str] = []

        # solution of the last solve
        self._col_values: FloatArray
        self._row_duals: FloatArray

        # the IIS of the last compute_iis, None where HiGHS vouched for none
        self._iis_model: highspy.HighsModel | None = None

        # warm-start state: interior point runs when rows or columns were added
        # since the last solve, a simplex warm start from the saved basis
        # otherwise; removing only changes bounds and so does not count as growth
        self._basis: highspy.HighsBasis | None = None
        self._model_grew: bool = True

        # deferred row-bound, cost and upper-bound changes, applied when the model
        # is next solved
        self._pending_row_bounds: dict[Constraint, tuple[float, float]] = {}
        self._pending_cost: dict[Variable, float] = {}
        self._pending_upper_bound: dict[Variable, float] = {}

        # last-written coefficients, to skip redundant changeCoeff calls
        self._coefficients: dict[tuple[Constraint, Variable], float] = {}

    def add_variable(self, name: str) -> Variable:
        """Add a non-negative continuous variable with a zero cost."""
        variable = Variable(self._num_cols)

        self._highs.addVar(0.0, highspy.kHighsInf)
        self._highs.passColName(variable, _lp_name(name))
        self._num_cols += 1
        self._model_grew = True

        return variable

    def add_constraint(self, sense: Sense, name: str) -> Constraint:
        """Add an empty constraint, ``0 <sense> 0``."""
        constraint = Constraint(len(self._row_names))
        lower_bound, upper_bound = _row_bounds(sense, 0.0)

        self._highs.addRow(lower_bound, upper_bound, 0, [], [])
        self._highs.passRowName(constraint, _lp_name(name))
        self._model_grew = True

        self._row_senses.append(sense)
        self._row_rhs.append(0.0)
        self._row_names.append(name)

        return constraint

    def set_coefficient(
        self, constraint: Constraint, variable: Variable, value: float
    ) -> None:
        """Set the coefficient of a variable in a constraint."""
        key = (constraint, variable)
        value = float(value)
        if self._coefficients.get(key) == value:
            return

        self._coefficients[key] = value
        self._highs.changeCoeff(constraint, variable, value)

    def set_rhs(self, constraint: Constraint, value: float) -> None:
        """Set the right-hand side of a constraint."""
        value = float(value)
        sense = self._row_senses[constraint]

        self._row_rhs[constraint] = value
        self._pending_row_bounds[constraint] = _row_bounds(sense, value)

    def set_cost(self, variable: Variable, value: float) -> None:
        """Set the objective coefficient of a variable."""
        self._pending_cost[variable] = float(value)

    def set_upper_bound(self, variable: Variable, value: float) -> None:
        """
        Set the upper bound of a variable.

        The lower bound stays zero.
        """
        self._pending_upper_bound[variable] = float(value)

    def remove_variable(self, variable: Variable) -> None:
        """
        Remove a variable from the linear program.

        The column stays in place, fixed to zero at zero cost. HiGHS names it after
        its index, so a variable added later may take its name.
        """
        self._highs.changeColBounds(variable, 0.0, 0.0)
        self._highs.changeColCost(variable, 0.0)
        self._highs.passColName(variable, f"removed_{variable}")
        self._pending_cost.pop(variable, None)
        self._pending_upper_bound.pop(variable, None)

    def remove_constraint(self, constraint: Constraint) -> None:
        """
        Remove a constraint from the linear program.

        The row stays in place with infinite bounds, so it always holds. HiGHS names
        it after its index, so a constraint added later may take its name.
        """
        self._highs.changeRowBounds(constraint, -highspy.kHighsInf, highspy.kHighsInf)
        self._highs.passRowName(constraint, f"removed_{constraint}")
        self._pending_row_bounds.pop(constraint, None)

    def solve(self) -> None:
        """
        Solve the linear program and store its solution.

        When rows or columns were added since the last solve, interior point with
        crossover runs, warm-started from the saved basis extended to the new size.
        When only data changed, simplex warm-starts from the saved basis, which needs
        few pivots, and falls back to interior point if it ends non-optimal.
        """
        self._flush_pending()

        if self._model_grew or self._basis is None:
            self._set_warm_start_basis()
            self._set_strategy(_INTERIOR_POINT)
            self._highs.run()
            self._model_grew = False
        else:
            self._set_strategy(_SIMPLEX)
            self._highs.setBasis(self._basis)
            self._highs.run()

            if self._highs.getModelStatus() != HighsModelStatus.kOptimal:
                self._set_strategy(_INTERIOR_POINT)
                self._highs.run()

        try:
            self._basis = self._highs.getBasis()
        except Exception:
            self._basis = None

        solution = self._highs.getSolution()
        self._col_values = np.array(solution.col_value)
        self._row_duals = np.array(solution.row_dual)

    @property
    def status(self) -> SolveStatusID:
        """Status of the last solve."""
        status = self._highs.getModelStatus()

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

    def value(self, variable: Variable) -> float:
        """Return the value of a variable at the last solution."""
        value: float = self._col_values[variable]
        return value

    def dual(self, constraint: Constraint) -> float:
        """Return the dual value of a constraint at the last solution."""
        dual: float = self._row_duals[constraint]
        return dual

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

        # after an interior point run HiGHS only narrows the IIS down to candidate
        # rows, a simplex run lets it prove the irreducible set
        self._set_strategy(_SIMPLEX)
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
        status = self._highs.writeModel(str(path))
        _warn_if_unwritten(status, path)

    def write_iis(self, path: Path) -> None:
        """
        Write the IIS of the last ``compute_iis`` to a file, in LP format.

        Nothing is written where HiGHS vouched for no IIS, or for an empty one.
        HiGHS writes LP format only to a path with the ``.lp`` extension, so the IIS
        is written to one in a temporary directory and moved to the path. A file
        HiGHS cannot write is logged as a warning.
        """
        if self._iis_model is None:
            return

        iis_highs = highspy.Highs()
        iis_highs.setOptionValue("output_flag", False)
        iis_highs.passModel(self._iis_model)

        with tempfile.TemporaryDirectory() as directory:
            lp_path = Path(directory) / "iis.lp"
            status = iis_highs.writeModel(str(lp_path))
            if status != HighsStatus.kError:
                shutil.move(lp_path, path)

        _warn_if_unwritten(status, path)

    def _flush_pending(self) -> None:
        """Apply the deferred row-bound, cost and upper-bound changes."""
        for row, (lower_bound, upper_bound) in self._pending_row_bounds.items():
            self._highs.changeRowBounds(row, lower_bound, upper_bound)
        self._pending_row_bounds.clear()

        if self._pending_cost:
            indices = np.array(list(self._pending_cost), dtype=np.int32)
            costs = np.array(list(self._pending_cost.values()), dtype=np.float64)
            self._highs.changeColsCost(len(indices), indices, costs)
            self._pending_cost.clear()

        if self._pending_upper_bound:
            indices = np.array(list(self._pending_upper_bound), dtype=np.int32)
            lower_bounds = np.zeros(len(indices), dtype=np.float64)
            upper_bounds = np.array(
                list(self._pending_upper_bound.values()), dtype=np.float64
            )
            self._highs.changeColsBounds(
                len(indices), indices, lower_bounds, upper_bounds
            )
            self._pending_upper_bound.clear()

    def _set_warm_start_basis(self) -> None:
        """Set the saved basis, extended to the model's size, to start the next run."""
        if self._basis is None:
            return

        basis = self._basis
        new_cols = self._num_cols - len(basis.col_status)
        new_rows = len(self._row_names) - len(basis.row_status)

        if new_cols > 0 or new_rows > 0:
            extended = highspy.HighsBasis()
            extended.col_status = (
                list(basis.col_status) + [HighsBasisStatus.kLower] * new_cols
            )
            extended.row_status = (
                list(basis.row_status) + [HighsBasisStatus.kBasic] * new_rows
            )
            extended.valid = True
            self._highs.setBasis(extended)
        else:
            basis.valid = True
            self._highs.setBasis(basis)

    def _set_strategy(self, options: dict[str, str]) -> None:
        """Set the options of a solve strategy for the next run."""
        for key, value in options.items():
            self._highs.setOptionValue(key, value)


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
