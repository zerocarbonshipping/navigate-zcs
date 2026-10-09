# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
HiGHS backend of the solver facade, mirroring the gurobipy API the bunker uses.

Consumers reach it through the facade in ``navigate.simulation.bunker.solver``,
never directly.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import highspy
import numpy as np
from highspy import HighsBasisStatus, HighsModelStatus

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.util.types_ import FloatArray

CONTINUOUS = "continuous"
OPTIMAL = 1
INFEASIBLE = 2
INF_OR_UNBD = 3

# constraint senses, spelled as gurobipy's GRB.EQUAL, GRB.LESS_EQUAL and
# GRB.GREATER_EQUAL
EQUAL = "="
LESS_EQUAL = "<"
GREATER_EQUAL = ">"


class LinExpr:
    """
    A sum of coefficient-variable products plus a constant, mirroring gurobipy.LinExpr.

    The expression has terms only when both ``coefficients`` and ``variables`` are
    given; with either one missing, it is empty.

    Parameters
    ----------
    coefficients
        Coefficient of each term, aligned with ``variables``.
    variables
        Variable of each term, aligned with ``coefficients``.
    """

    def __init__(
        self,
        coefficients: Sequence[float] | None = None,
        variables: Sequence[Var] | None = None,
    ) -> None:
        self._terms: list[tuple[float, Var]] = []
        self._constant: float = 0.0
        if coefficients is not None and variables is not None:
            self._terms = list(zip(coefficients, variables, strict=True))

    def _copy(self) -> LinExpr:
        expression = LinExpr()
        expression._terms = list(self._terms)
        expression._constant = self._constant
        return expression

    def __add__(self, other: LinExpr | Var | float) -> LinExpr:
        result = self._copy()
        if isinstance(other, LinExpr):
            result._terms.extend(other._terms)
            result._constant += other._constant
        elif isinstance(other, Var):
            result._terms.append((1.0, other))
        elif isinstance(other, (int, float)):
            result._constant += other
        else:
            return NotImplemented
        return result

    def __radd__(self, other: float) -> LinExpr:
        if isinstance(other, (int, float)):
            result = self._copy()
            result._constant += other
            return result
        return NotImplemented

    def __sub__(self, other: LinExpr | Var | float) -> LinExpr:
        result = self._copy()
        if isinstance(other, LinExpr):
            result._terms.extend(
                (-coefficient, variable) for coefficient, variable in other._terms
            )
            result._constant -= other._constant
        elif isinstance(other, Var):
            result._terms.append((-1.0, other))
        elif isinstance(other, (int, float)):
            result._constant -= other
        else:
            return NotImplemented
        return result

    def __rsub__(self, other: float) -> LinExpr:
        if isinstance(other, (int, float)):
            result = self.__neg__()
            result._constant += other
            return result
        return NotImplemented

    def __mul__(self, scalar: float) -> LinExpr:
        if isinstance(scalar, (int, float)):
            result = LinExpr()
            result._terms = [
                (coefficient * scalar, variable)
                for coefficient, variable in self._terms
            ]
            result._constant = self._constant * scalar
            return result
        return NotImplemented

    def __rmul__(self, scalar: float) -> LinExpr:
        return self.__mul__(scalar)

    def __neg__(self) -> LinExpr:
        result = LinExpr()
        result._terms = [
            (-coefficient, variable) for coefficient, variable in self._terms
        ]
        result._constant = -self._constant
        return result

    def __le__(self, other: LinExpr | float) -> TempConstr:
        if isinstance(other, (int, float)):
            return TempConstr(self, LESS_EQUAL, float(other))
        if isinstance(other, LinExpr):
            return TempConstr(self - other, LESS_EQUAL, 0.0)
        return NotImplemented

    def __ge__(self, other: LinExpr | float) -> TempConstr:
        if isinstance(other, (int, float)):
            return TempConstr(self, GREATER_EQUAL, float(other))
        if isinstance(other, LinExpr):
            return TempConstr(self - other, GREATER_EQUAL, 0.0)
        return NotImplemented

    def getValue(self) -> float:
        """
        Evaluate the expression at the last solution.

        Returns
        -------
        float
            The expression's value.
        """
        return (
            sum(coefficient * variable.X for coefficient, variable in self._terms)
            + self._constant
        )


class TempConstr:
    """A pending ``lhs <sense> rhs`` from a comparison, passed to Model.addConstr."""

    def __init__(self, lhs: LinExpr, sense: str, rhs: float) -> None:
        self.lhs: LinExpr = lhs
        self.sense: str = sense
        self.rhs: float = rhs


class Var:
    """A HiGHS column, mirroring gurobipy.Var."""

    def __init__(self, model: Model, col: int) -> None:
        self._model: Model = model
        self._col: int = col

    @property
    def X(self) -> float:
        """Primal solution value at the last solve."""
        value: float = self._model._col_values[self._col]
        return value

    @property
    def Obj(self) -> float:
        """Objective coefficient."""
        return self._model._col_costs[self._col]

    @Obj.setter
    def Obj(self, value: float) -> None:
        value = float(value)
        self._model._col_costs[self._col] = value
        self._model._pending_obj[self._col] = value

    @property
    def UB(self) -> float:
        """Upper bound; the lower bound is always zero."""
        return self._model._col_upper_bounds[self._col]

    @UB.setter
    def UB(self, value: float) -> None:
        value = float(value)
        self._model._col_upper_bounds[self._col] = value
        self._model._pending_ub[self._col] = value

    def _as_expression(self, coefficient: float = 1.0) -> LinExpr:
        expression = LinExpr()
        expression._terms = [(coefficient, self)]
        return expression

    def __add__(self, other: LinExpr | Var | float) -> LinExpr:
        return self._as_expression().__add__(other)

    def __radd__(self, other: float) -> LinExpr:
        if isinstance(other, (int, float)):
            expression = self._as_expression()
            expression._constant += other
            return expression
        return NotImplemented

    def __sub__(self, other: LinExpr | Var | float) -> LinExpr:
        return self._as_expression().__sub__(other)

    def __rsub__(self, other: float) -> LinExpr:
        if isinstance(other, (int, float)):
            expression = self._as_expression(-1.0)
            expression._constant += other
            return expression
        return NotImplemented

    def __mul__(self, scalar: float) -> LinExpr:
        if isinstance(scalar, (int, float)):
            return self._as_expression(float(scalar))
        return NotImplemented

    def __rmul__(self, scalar: float) -> LinExpr:
        return self.__mul__(scalar)

    def __neg__(self) -> LinExpr:
        return self._as_expression(-1.0)

    def __le__(self, other: LinExpr | float) -> TempConstr:
        return self._as_expression().__le__(other)

    def __ge__(self, other: LinExpr | float) -> TempConstr:
        return self._as_expression().__ge__(other)


class Constr:
    """A HiGHS row, mirroring gurobipy.Constr."""

    def __init__(self, model: Model, row: int, sense: str, rhs_value: float) -> None:
        self._model: Model = model
        self._row: int = row
        self._sense: str = sense
        self._rhs_value: float = rhs_value

    @property
    def rhs(self) -> float:
        """Right-hand side, written in gurobipy's lowercase spelling."""
        return self._rhs_value

    @rhs.setter
    def rhs(self, value: float) -> None:
        value = float(value)
        self._rhs_value = value
        if self._sense == EQUAL:
            self._model._pending_rhs[self._row] = (value, value)
        elif self._sense == LESS_EQUAL:
            self._model._pending_rhs[self._row] = (-highspy.kHighsInf, value)
        elif self._sense == GREATER_EQUAL:
            self._model._pending_rhs[self._row] = (value, highspy.kHighsInf)

    @property
    def RHS(self) -> float:
        """Right-hand side, read in gurobipy's uppercase spelling."""
        return self._rhs_value

    @property
    def Pi(self) -> float:
        """Shadow price (dual value) at the last solve."""
        value: float = self._model._row_duals[self._row]
        return value


class Params:
    """HiGHS solver options under the gurobipy parameter names the bunker sets."""

    def __init__(self, highs: highspy.Highs) -> None:
        self._highs: highspy.Highs = highs
        self._output_flag: int
        self._method: int
        self._threads: int
        self._feasibility_tolerance: float
        self._optimality_tolerance: float
        self._dual_reductions: int = 1

    @property
    def OutputFlag(self) -> int:
        """Whether the solver logs to the console, 0 or 1."""
        return self._output_flag

    @OutputFlag.setter
    def OutputFlag(self, value: int) -> None:
        self._output_flag = value
        self._highs.setOptionValue("output_flag", bool(value))

    @property
    def Method(self) -> int:
        """Gurobi method ID; HiGHS chooses its method per solve and does not read it."""
        return self._method

    @Method.setter
    def Method(self, value: int) -> None:
        self._method = value

    @property
    def Threads(self) -> int:
        """Number of solver threads, 0 for automatic in both solvers."""
        return self._threads

    @Threads.setter
    def Threads(self, value: int) -> None:
        self._threads = value
        self._highs.setOptionValue("threads", int(value))

    @property
    def FeasibilityTol(self) -> float:
        """Primal feasibility tolerance."""
        return self._feasibility_tolerance

    @FeasibilityTol.setter
    def FeasibilityTol(self, value: float) -> None:
        self._feasibility_tolerance = value
        self._highs.setOptionValue("primal_feasibility_tolerance", float(value))

    @property
    def OptimalityTol(self) -> float:
        """Dual feasibility tolerance."""
        return self._optimality_tolerance

    @OptimalityTol.setter
    def OptimalityTol(self, value: float) -> None:
        self._optimality_tolerance = value
        self._highs.setOptionValue("dual_feasibility_tolerance", float(value))

    @property
    def DualReductions(self) -> int:
        """Gurobi dual-reductions switch, 0 or 1; HiGHS has no equivalent."""
        return self._dual_reductions

    @DualReductions.setter
    def DualReductions(self, value: int) -> None:
        self._dual_reductions = value


class Model:
    """
    A HiGHS linear program, mirroring the gurobipy.Model interface the bunker uses.

    Parameters
    ----------
    name
        Model name, accepted as gurobipy accepts it; the HiGHS model stays unnamed.
    """

    def __init__(self, name: str = "") -> None:
        self._highs: highspy.Highs = highspy.Highs()
        self._highs.setOptionValue("output_flag", False)

        self._num_cols: int = 0
        self._num_rows: int = 0
        self._constr_names: list[str] = []

        # removed rows are neutralized, not deleted; recycleConstr reuses them,
        # zeroing the non-zero columns tracked per row
        self._removed_rows: set[int] = set()
        self._recycled_rows: list[int] = []
        self._row_coeffs: dict[int, set[int]] = {}

        # solution of the last solve
        self._col_values: FloatArray
        self._row_duals: FloatArray
        self._iis_row_flags: list[bool] | None = None

        # warm-start state: interior point runs when rows or columns were added
        # since the last solve, a simplex warm start from the saved basis
        # otherwise; remove() only changes bounds and so does not count as growth
        self._basis: highspy.HighsBasis | None = None
        self._model_grew: bool = True

        # cached objective coefficients spare expensive getCol() calls
        self._col_costs: list[float] = []

        # cached column upper bounds; every column has lower bound 0
        self._col_upper_bounds: list[float] = []

        # deferred right-hand side, objective and upper-bound changes, applied
        # when the model is next solved
        self._pending_rhs: dict[int, tuple[float, float]] = {}
        self._pending_obj: dict[int, float] = {}
        self._pending_ub: dict[int, float] = {}

        # last-written coefficients, to skip redundant changeCoeff calls
        self._coeff_values: dict[tuple[int, int], float] = {}

        self.Params: Params = Params(self._highs)

    def addVar(self, vtype: str = CONTINUOUS, name: str = "") -> Var:
        """
        Add a non-negative continuous variable with a zero objective coefficient.

        Parameters
        ----------
        vtype
            Variable type, accepted as gurobipy accepts it; every variable is
            continuous.
        name
            Variable name, accepted as gurobipy accepts it; HiGHS columns stay unnamed.

        Returns
        -------
        Var
            The new variable.
        """
        col = self._num_cols
        self._highs.addVar(0.0, highspy.kHighsInf)
        self._num_cols += 1
        self._col_costs.append(0.0)
        self._col_upper_bounds.append(highspy.kHighsInf)
        self._model_grew = True
        return Var(self, col)

    def addConstr(self, constr: TempConstr, name: str = "") -> Constr:
        """
        Add a constraint built by a comparison operator.

        Parameters
        ----------
        constr
            The comparison of a LinExpr or Var.
        name
            Constraint name.

        Returns
        -------
        Constr
            The new constraint.
        """
        return self._add_row(constr.lhs, constr.sense, constr.rhs, name)

    def addLConstr(
        self, lhs: LinExpr, sense: str, rhs: float, name: str = ""
    ) -> Constr:
        """
        Add a linear constraint given by its sides and sense.

        Parameters
        ----------
        lhs
            Left-hand side expression.
        sense
            One of EQUAL, LESS_EQUAL or GREATER_EQUAL.
        rhs
            Right-hand side constant.
        name
            Constraint name.

        Returns
        -------
        Constr
            The new constraint.
        """
        return self._add_row(lhs, sense, rhs, name)

    def _add_row(self, lhs: LinExpr, sense: str, rhs: float, name: str) -> Constr:
        """Append a row for ``lhs <sense> rhs`` and return its constraint."""
        row = self._num_rows

        # the constant of the left-hand side moves to the right-hand side
        adjusted_rhs = rhs - lhs._constant

        indices = []
        values = []
        for coefficient, variable in lhs._terms:
            indices.append(variable._col)
            values.append(coefficient)

        if sense == EQUAL:
            lower_bound = adjusted_rhs
            upper_bound = adjusted_rhs
        elif sense == LESS_EQUAL:
            lower_bound = -highspy.kHighsInf
            upper_bound = adjusted_rhs
        elif sense == GREATER_EQUAL:
            lower_bound = adjusted_rhs
            upper_bound = highspy.kHighsInf
        else:
            raise ValueError(f"Unknown constraint sense: {sense}")

        self._highs.addRow(lower_bound, upper_bound, len(indices), indices, values)
        self._num_rows += 1
        self._model_grew = True

        if indices:
            self._row_coeffs[row] = set(indices)

        self._constr_names.append(name)

        return Constr(self, row, sense, adjusted_rhs)

    def chgCoeff(self, constr: Constr, var: Var, value: float) -> None:
        """
        Change one coefficient of the constraint matrix.

        Parameters
        ----------
        constr
            Constraint whose row holds the coefficient.
        var
            Variable whose column holds the coefficient.
        value
            New coefficient.
        """
        row = constr._row
        col = var._col
        key = (row, col)
        value = float(value)
        if self._coeff_values.get(key) == value:
            return

        self._coeff_values[key] = value
        self._highs.changeCoeff(row, col, value)

        if value != 0.0:
            row_cols = self._row_coeffs.get(row)
            if row_cols is None:
                self._row_coeffs[row] = {col}
            else:
                row_cols.add(col)
        else:
            row_cols = self._row_coeffs.get(row)
            if row_cols is not None:
                row_cols.discard(col)

    def remove(self, item: Var | Constr) -> None:
        """
        Neutralize a variable or constraint, keeping its column or row in place.

        A variable is fixed to zero at zero cost; a constraint gets infinite bounds, so
        it always holds, and its row becomes available to recycleConstr.

        Parameters
        ----------
        item
            The variable or constraint to neutralize.
        """
        if isinstance(item, Var):
            self._highs.changeColBounds(item._col, 0.0, 0.0)
            self._highs.changeColCost(item._col, 0.0)
            self._col_costs[item._col] = 0.0
            self._col_upper_bounds[item._col] = 0.0
            self._pending_obj.pop(item._col, None)
            self._pending_ub.pop(item._col, None)
            return

        self._removed_rows.add(item._row)
        self._recycled_rows.append(item._row)
        self._highs.changeRowBounds(item._row, -highspy.kHighsInf, highspy.kHighsInf)
        self._pending_rhs.pop(item._row, None)

    def recycleConstr(
        self, constr: TempConstr, name: str = "", mark_grew: bool = True
    ) -> Constr:
        """
        Reuse the row of a removed constraint for a new one.

        Without a removed row to reuse, the constraint is added as a new row.

        Parameters
        ----------
        constr
            The comparison of a LinExpr or Var.
        name
            Constraint name.
        mark_grew
            Whether the next solve treats the model as grown and runs interior point.

        Returns
        -------
        Constr
            The new constraint.
        """
        if not self._recycled_rows:
            return self.addConstr(constr, name=name)

        row = self._recycled_rows.pop()
        self._removed_rows.discard(row)

        lhs = constr.lhs
        sense = constr.sense
        rhs = constr.rhs

        adjusted_rhs = rhs - lhs._constant

        change_coefficient = self._highs.changeCoeff

        old_cols = self._row_coeffs.get(row)
        if old_cols:
            for col in old_cols:
                change_coefficient(row, col, 0.0)
                self._coeff_values.pop((row, col), None)
            old_cols.clear()

        new_cols = set()
        for coefficient, variable in lhs._terms:
            col = variable._col
            change_coefficient(row, col, coefficient)
            self._coeff_values[(row, col)] = coefficient
            new_cols.add(col)

        if new_cols:
            self._row_coeffs[row] = new_cols

        if sense == EQUAL:
            lower_bound = adjusted_rhs
            upper_bound = adjusted_rhs
        elif sense == LESS_EQUAL:
            lower_bound = -highspy.kHighsInf
            upper_bound = adjusted_rhs
        elif sense == GREATER_EQUAL:
            lower_bound = adjusted_rhs
            upper_bound = highspy.kHighsInf
        else:
            raise ValueError(f"Unknown constraint sense: {sense}")

        self._highs.changeRowBounds(row, lower_bound, upper_bound)

        if mark_grew:
            self._model_grew = True
            # a recycled row enters the basis as a new row does
            if self._basis is not None:
                with contextlib.suppress(IndexError, AttributeError):
                    self._basis.row_status[row] = HighsBasisStatus.kBasic

        self._constr_names[row] = name

        return Constr(self, row, sense, adjusted_rhs)

    def _flush_pending(self) -> None:
        """Apply the deferred right-hand side, objective and upper-bound changes."""
        for row, (lower_bound, upper_bound) in self._pending_rhs.items():
            self._highs.changeRowBounds(row, lower_bound, upper_bound)
        self._pending_rhs.clear()

        if self._pending_obj:
            cols = list(self._pending_obj.keys())
            costs = list(self._pending_obj.values())
            indices = np.array(cols, dtype=np.int32)
            values = np.array(costs, dtype=np.float64)
            self._highs.changeColsCost(len(cols), indices, values)
            self._pending_obj.clear()

        if self._pending_ub:
            cols = list(self._pending_ub.keys())
            indices = np.array(cols, dtype=np.int32)
            lower_bounds = np.zeros(len(cols), dtype=np.float64)
            upper_bounds = np.array(list(self._pending_ub.values()), dtype=np.float64)
            self._highs.changeColsBounds(len(cols), indices, lower_bounds, upper_bounds)
            self._pending_ub.clear()

    def optimize(self) -> None:
        """
        Solve the linear program and store its solution.

        When rows or columns were added since the last solve, interior point with
        crossover runs, warm-started from the saved basis extended to the new size;
        its interior solutions keep the fair-share iterations stable. When only data
        changed, simplex warm-starts from the saved basis, which needs few pivots,
        and falls back to interior point if it ends non-optimal.
        """
        self._flush_pending()

        if self._model_grew or self._basis is None:
            if self._basis is not None:
                basis = self._basis
                old_cols = len(basis.col_status)
                old_rows = len(basis.row_status)
                if old_cols < self._num_cols or old_rows < self._num_rows:
                    extended = highspy.HighsBasis()
                    extended.col_status = list(basis.col_status) + [
                        HighsBasisStatus.kLower
                    ] * (self._num_cols - old_cols)
                    extended.row_status = list(basis.row_status) + [
                        HighsBasisStatus.kBasic
                    ] * (self._num_rows - old_rows)
                    extended.valid = True
                    self._highs.setBasis(extended)
                else:
                    basis.valid = True
                    self._highs.setBasis(basis)

            self._highs.setOptionValue("solver", "ipm")
            self._highs.setOptionValue("run_crossover", "on")
            self._highs.setOptionValue("presolve", "on")
            self._highs.run()
            self._model_grew = False
        else:
            self._highs.setOptionValue("solver", "simplex")
            self._highs.setOptionValue("run_crossover", "off")
            self._highs.setOptionValue("presolve", "off")
            self._highs.setBasis(self._basis)
            self._highs.run()

            if self._highs.getModelStatus() != HighsModelStatus.kOptimal:
                self._highs.setOptionValue("solver", "ipm")
                self._highs.setOptionValue("run_crossover", "on")
                self._highs.setOptionValue("presolve", "on")
                self._highs.run()

        try:
            self._basis = self._highs.getBasis()
        except Exception:
            self._basis = None

        solution = self._highs.getSolution()
        self._col_values = np.array(solution.col_value)
        self._row_duals = np.array(solution.row_dual)

    @property
    def Status(self) -> int:
        """Status of the last solve as OPTIMAL, INFEASIBLE or INF_OR_UNBD."""
        status = self._highs.getModelStatus()

        if status == HighsModelStatus.kOptimal:
            return OPTIMAL

        if status == HighsModelStatus.kInfeasible:
            return INFEASIBLE

        # every other status, such as unbounded, an error or a reached limit
        return INF_OR_UNBD

    def computeIIS(self) -> None:
        """
        Compute an irreducible infeasible subset of the constraints.

        Where HiGHS cannot compute one, every constraint not removed counts as a
        member.
        """
        try:
            _, iis = self._highs.getIis()
            iis_rows = set(iis.row_index_)
            self._iis_row_flags = [row in iis_rows for row in range(self._num_rows)]
        except Exception:
            self._iis_row_flags = [
                row not in self._removed_rows for row in range(self._num_rows)
            ]

    @property
    def IISConstr(self) -> list[bool]:
        """Whether each constraint is in the IIS, all False before computeIIS()."""
        if self._iis_row_flags is None:
            return [False] * self._num_rows
        return list(self._iis_row_flags)

    @property
    def ConstrName(self) -> list[str]:
        """Name of each constraint, in row order."""
        return list(self._constr_names)

    def write(self, filename: str) -> None:
        """
        Write the model to a file, in the format its extension names (LP or MPS).

        Parameters
        ----------
        filename
            Path of the file.
        """
        self._highs.writeModel(filename)
