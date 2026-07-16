# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
HiGHS-backed solver module providing a gurobipy-compatible API.

This module wraps the HiGHS open-source LP solver (via highspy) to provide
the same interface as gurobipy for all features used by the bunker algorithm.
This eliminates the need for a commercial Gurobi license.

Usage:
    import navigate.bunker.solver as gp
    from navigate.bunker.solver import GRB
"""

import highspy
import numpy as np
from highspy import HighsBasisStatus, HighsModelStatus

# ======================================================================================================================
# Constants
# ======================================================================================================================

CONTINUOUS = "continuous"
OPTIMAL = 1
INFEASIBLE = 2
INF_OR_UNBD = 3

_SENSE_EQ = "=="
_SENSE_LE = "<="
_SENSE_GE = ">="

# Map old Gurobi SolverMethodID integer values to HiGHS solver options.
# The optimize() method uses IPM when the model structure grows (addVar/addConstr)
# to produce interior solutions for fair-share stability. Simplex warm-start is
# used for data-only changes (RHS/obj/coeff/bounds). remove() does NOT trigger
# IPM since it only changes bounds (neutralization). Basis extension is used to
# warm-start IPM's crossover phase when the model grows.
_METHOD_MAP = {
    -1: "ipm",      # AUTOMATIC → hybrid IPM/simplex
    3: "ipm",       # NON_DETERMINISTIC (interior point)
    4: "ipm",       # DETERMINISTIC (concurrent in Gurobi → hybrid in HiGHS)
}


# ======================================================================================================================
# GRB namespace (mirrors gurobipy.GRB constants)
# ======================================================================================================================

class _GRB:
    CONTINUOUS = CONTINUOUS
    OPTIMAL = OPTIMAL
    INFEASIBLE = INFEASIBLE
    INF_OR_UNBD = INF_OR_UNBD


GRB = _GRB()


# ======================================================================================================================
# LinExpr
# ======================================================================================================================

class LinExpr:
    """
    A linear expression: sum of (coefficient * variable) pairs plus a constant.

    Mirrors the gurobipy.LinExpr interface for the subset of features used.
    """

    __hash__ = None  # unhashable, like gurobipy LinExpr

    def __init__(self, coefficients=None, variables=None):
        # _terms: list of (coefficient, Var)
        # _constant: float
        if coefficients is not None and variables is not None:
            self._terms = list(zip(coefficients, variables))
            self._constant = 0.0
        else:
            self._terms = []
            self._constant = 0.0

    def _copy(self):
        expr = LinExpr()
        expr._terms = list(self._terms)
        expr._constant = self._constant
        return expr

    # arithmetic --------------------------------------------------------------------------------------------------------
    def __add__(self, other):
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

    def __radd__(self, other):
        if isinstance(other, (int, float)):
            result = self._copy()
            result._constant += other
            return result
        return NotImplemented

    def __sub__(self, other):
        result = self._copy()
        if isinstance(other, LinExpr):
            result._terms.extend((-c, v) for c, v in other._terms)
            result._constant -= other._constant
        elif isinstance(other, Var):
            result._terms.append((-1.0, other))
        elif isinstance(other, (int, float)):
            result._constant -= other
        else:
            return NotImplemented
        return result

    def __rsub__(self, other):
        if isinstance(other, (int, float)):
            result = self.__neg__()
            result._constant += other
            return result
        return NotImplemented

    def __mul__(self, scalar):
        if isinstance(scalar, (int, float)):
            result = LinExpr()
            result._terms = [(c * scalar, v) for c, v in self._terms]
            result._constant = self._constant * scalar
            return result
        return NotImplemented

    def __rmul__(self, scalar):
        return self.__mul__(scalar)

    def __neg__(self):
        result = LinExpr()
        result._terms = [(-c, v) for c, v in self._terms]
        result._constant = -self._constant
        return result

    # comparison operators (create TempConstr) --------------------------------------------------------------------------
    def __eq__(self, other):
        if isinstance(other, (int, float)):
            return TempConstr(self, _SENSE_EQ, float(other))
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, (int, float)):
            return TempConstr(self, _SENSE_LE, float(other))
        if isinstance(other, LinExpr):
            return TempConstr(self - other, _SENSE_LE, 0.0)
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, (int, float)):
            return TempConstr(self, _SENSE_GE, float(other))
        if isinstance(other, LinExpr):
            return TempConstr(self - other, _SENSE_GE, 0.0)
        return NotImplemented

    # evaluation --------------------------------------------------------------------------------------------------------
    def getValue(self):
        """Evaluate the expression using current solution values."""
        return sum(c * v.X for c, v in self._terms) + self._constant


# ======================================================================================================================
# TempConstr
# ======================================================================================================================

class TempConstr:
    """Temporary constraint object created by comparison operators, passed to Model.addConstr()."""

    def __init__(self, lhs, sense, rhs):
        self.lhs = lhs        # LinExpr
        self.sense = sense     # "==", "<=", ">="
        self.rhs = rhs         # float


# ======================================================================================================================
# Var
# ======================================================================================================================

class Var:
    """
    Wrapper around a HiGHS column (variable).

    Mirrors gurobipy.Var for the subset of features used.
    """

    def __init__(self, model, col):
        self._model = model    # Model instance (for accessing HiGHS and solution)
        self._col = col        # column index in HiGHS

    # solution value ----------------------------------------------------------------------------------------------------
    @property
    def X(self):
        """Primal solution value."""
        return self._model._col_values[self._col]

    # objective coefficient ---------------------------------------------------------------------------------------------
    @property
    def Obj(self):
        return self._model._col_costs[self._col]

    @Obj.setter
    def Obj(self, value):
        value = float(value)
        self._model._col_costs[self._col] = value
        self._model._pending_obj[self._col] = value

    # arithmetic (return LinExpr) ---------------------------------------------------------------------------------------
    def _to_expr(self, coeff=1.0):
        expr = LinExpr()
        expr._terms = [(coeff, self)]
        return expr

    def __add__(self, other):
        return self._to_expr().__add__(other)

    def __radd__(self, other):
        if isinstance(other, (int, float)):
            expr = self._to_expr()
            expr._constant += other
            return expr
        if isinstance(other, LinExpr):
            return other.__add__(self)
        return NotImplemented

    def __sub__(self, other):
        return self._to_expr().__sub__(other)

    def __rsub__(self, other):
        if isinstance(other, (int, float)):
            expr = self._to_expr(-1.0)
            expr._constant += other
            return expr
        if isinstance(other, LinExpr):
            return other.__sub__(self)
        return NotImplemented

    def __mul__(self, scalar):
        if isinstance(scalar, (int, float)):
            return self._to_expr(float(scalar))
        return NotImplemented

    def __rmul__(self, scalar):
        return self.__mul__(scalar)

    def __neg__(self):
        return self._to_expr(-1.0)

    # comparison operators (create TempConstr via LinExpr) ---------------------------------------------------------------
    def __le__(self, other):
        return self._to_expr().__le__(other)

    def __ge__(self, other):
        return self._to_expr().__ge__(other)

    def __eq__(self, other):
        # Only support constraint creation (comparison with numbers)
        if isinstance(other, (int, float)):
            return self._to_expr().__eq__(other)
        # For identity comparison (used in dict lookups etc.), fall back to object identity
        return NotImplemented

    def __hash__(self):
        return id(self)


# ======================================================================================================================
# Constr
# ======================================================================================================================

class Constr:
    """
    Wrapper around a HiGHS row (constraint).

    Mirrors gurobipy.Constr for the subset of features used.
    """

    def __init__(self, model, row, sense, rhs_value, name=""):
        self._model = model
        self._row = row
        self._sense = sense       # "==", "<=", ">="
        self._rhs_value = rhs_value
        self._name = name

    # RHS write (lowercase, as used in gurobipy) ------------------------------------------------------------------------
    @property
    def rhs(self):
        return self._rhs_value

    @rhs.setter
    def rhs(self, value):
        value = float(value)
        self._rhs_value = value
        if self._sense == _SENSE_EQ:
            self._model._pending_rhs[self._row] = (value, value)
        elif self._sense == _SENSE_LE:
            self._model._pending_rhs[self._row] = (-highspy.kHighsInf, value)
        elif self._sense == _SENSE_GE:
            self._model._pending_rhs[self._row] = (value, highspy.kHighsInf)

    # RHS read (uppercase, as used in gurobipy) -------------------------------------------------------------------------
    @property
    def RHS(self):
        return self._rhs_value

    # dual value --------------------------------------------------------------------------------------------------------
    @property
    def Pi(self):
        """Shadow price (dual value)."""
        return self._model._row_duals[self._row]

    # sensitivity analysis (ranging) ------------------------------------------------------------------------------------
    @property
    def SARHSLow(self):
        """Lower bound of the RHS sensitivity range."""
        self._model._ensure_ranging()
        return self._model._ranging_rhs_low[self._row]

    @property
    def SARHSUp(self):
        """Upper bound of the RHS sensitivity range."""
        self._model._ensure_ranging()
        return self._model._ranging_rhs_up[self._row]


# ======================================================================================================================
# Params
# ======================================================================================================================

class Params:
    """
    Proxy for HiGHS solver options, using Gurobi parameter names.
    """

    def __init__(self, highs):
        self._highs = highs
        self._dual_reductions = 1

    @property
    def OutputFlag(self):
        return self._output_flag

    @OutputFlag.setter
    def OutputFlag(self, value):
        self._output_flag = value
        self._highs.setOptionValue("output_flag", bool(value))

    @property
    def Method(self):
        return self._method

    @Method.setter
    def Method(self, value):
        self._method = value
        # Store the mapped solver — optimize() will apply it dynamically
        # based on whether warm-starting is possible.
        self._solver = _METHOD_MAP.get(value, "ipm")

    @property
    def Threads(self):
        return self._threads

    @Threads.setter
    def Threads(self, value):
        self._threads = value
        # HiGHS uses 0 for automatic, same as Gurobi
        self._highs.setOptionValue("threads", int(value))

    @property
    def FeasibilityTol(self):
        return self._feasibility_tol

    @FeasibilityTol.setter
    def FeasibilityTol(self, value):
        self._feasibility_tol = value
        self._highs.setOptionValue("primal_feasibility_tolerance", float(value))

    @property
    def OptimalityTol(self):
        return self._optimality_tol

    @OptimalityTol.setter
    def OptimalityTol(self, value):
        self._optimality_tol = value
        self._highs.setOptionValue("dual_feasibility_tolerance", float(value))

    @property
    def DualReductions(self):
        return self._dual_reductions

    @DualReductions.setter
    def DualReductions(self, value):
        # No direct HiGHS equivalent. HiGHS handles infeasible/unbounded
        # detection differently. Stored for compatibility but not applied.
        self._dual_reductions = value


# ======================================================================================================================
# Model
# ======================================================================================================================

class Model:
    """
    HiGHS-backed LP model with a gurobipy-compatible interface.

    Provides the same API as gurobipy.Model for all features used by
    the bunker algorithm: addVar, addConstr, chgCoeff, remove, optimize,
    computeIIS, write, and solution/dual/ranging access.
    """

    def __init__(self, name=""):
        self._highs = highspy.Highs()
        self._highs.setOptionValue("output_flag", False)

        self._num_cols = 0
        self._num_rows = 0

        # Track constraint metadata
        self._constr_names = []       # row index -> name
        self._constr_objects = []     # row index -> Constr object

        # Track removed items (neutralized, not deleted)
        self._removed_cols = set()
        self._removed_rows = set()

        # Solution storage (populated after optimize())
        self._col_values = None       # primal solution
        self._row_duals = None        # dual values

        # Ranging (computed lazily after optimize())
        self._ranging_computed = False
        self._ranging_rhs_low = None
        self._ranging_rhs_up = None

        # IIS storage
        self._iis_row_flags = None

        # Warm-start state. IPM is used when the model structure has grown
        # (new variables/constraints added via addVar/addConstr). Simplex
        # warm-start is used for all other solves (RHS/coeff/bound changes).
        # remove() does NOT trigger IPM since it only changes bounds.
        self._basis = None
        self._model_grew = True  # True = new rows/cols since last solve

        # Cached objective coefficients (avoids expensive getCol() calls)
        self._col_costs = []

        # Deferred update buffers (flushed as batch calls at optimize())
        self._pending_rhs = {}  # row_index -> (lb, ub)
        self._pending_obj = {}  # col_index -> value

        # Last-written coefficients (skip redundant changeCoeff calls)
        self._coeff_values = {}  # (row, col) -> value

        # Recycled constraint pool (neutralized rows available for reuse via recycleConstr)
        self._recycled_rows = []
        self._row_coeffs = {}  # row_index -> set of col_indices with non-zero coeffs

        # Params proxy
        self.Params = Params(self._highs)

    # ------------------------------------------------------------------------------------------------------------------
    # Variable management
    # ------------------------------------------------------------------------------------------------------------------
    def addVar(self, vtype=CONTINUOUS, name=""):
        """Add a non-negative continuous variable."""
        col = self._num_cols
        self._highs.addVar(0.0, highspy.kHighsInf)
        self._num_cols += 1
        self._col_costs.append(0.0)
        self._model_grew = True
        return Var(self, col)

    # ------------------------------------------------------------------------------------------------------------------
    # Constraint management
    # ------------------------------------------------------------------------------------------------------------------
    def addConstr(self, constr: TempConstr, name: str = ""):
        """
        Add a constraint to the model.

        Parameters
        ----------
        constr
            A temporary constraint created by a comparison operator on LinExpr or Var.
        name
            Constraint name.

        Returns
        -------
        Constr
        """
        row = self._num_rows

        lhs = constr.lhs
        sense = constr.sense
        rhs = constr.rhs

        # Separate the constant from the LHS and move it to the RHS
        adjusted_rhs = rhs - lhs._constant

        # Extract sparse row data
        indices = []
        values = []
        for coeff, var in lhs._terms:
            indices.append(var._col)
            values.append(coeff)

        # Set row bounds based on sense
        if sense == _SENSE_EQ:
            lb = adjusted_rhs
            ub = adjusted_rhs
        elif sense == _SENSE_LE:
            lb = -highspy.kHighsInf
            ub = adjusted_rhs
        elif sense == _SENSE_GE:
            lb = adjusted_rhs
            ub = highspy.kHighsInf
        else:
            raise ValueError(f"Unknown constraint sense: {sense}")

        self._highs.addRow(lb, ub, len(indices), indices, values)
        self._num_rows += 1
        self._model_grew = True

        # Track non-zero coefficients for this row (used by recycleConstr)
        if indices:
            self._row_coeffs[row] = set(indices)

        constr_obj = Constr(self, row, sense, adjusted_rhs, name)
        self._constr_names.append(name)
        self._constr_objects.append(constr_obj)

        return constr_obj

    # ------------------------------------------------------------------------------------------------------------------
    # Coefficient modification
    # ------------------------------------------------------------------------------------------------------------------
    def chgCoeff(self, constr, var, value):
        """Change a single coefficient in the constraint matrix."""
        row = constr._row
        col = var._col
        key = (row, col)
        value = float(value)
        if self._coeff_values.get(key) == value:
            return
        self._coeff_values[key] = value
        self._highs.changeCoeff(row, col, value)

        # Track non-zero columns per row (used by recycleConstr)
        if value != 0.0:
            row_set = self._row_coeffs.get(row)
            if row_set is None:
                self._row_coeffs[row] = {col}
            else:
                row_set.add(col)
        else:
            row_set = self._row_coeffs.get(row)
            if row_set is not None:
                row_set.discard(col)

    # ------------------------------------------------------------------------------------------------------------------
    # Removal (neutralization)
    # ------------------------------------------------------------------------------------------------------------------
    def remove(self, item):
        """
        Neutralize a variable or constraint.

        Variables: bounds set to [0, 0], objective to 0 — forced to zero.
        Constraints: bounds set to [-inf, inf] — always satisfied.
        """
        if isinstance(item, Var):
            self._removed_cols.add(item._col)
            self._highs.changeColBounds(item._col, 0.0, 0.0)
            self._highs.changeColCost(item._col, 0.0)
            self._col_costs[item._col] = 0.0
            self._pending_obj.pop(item._col, None)
        elif isinstance(item, Constr):
            self._removed_rows.add(item._row)
            self._recycled_rows.append(item._row)
            self._highs.changeRowBounds(item._row, -highspy.kHighsInf, highspy.kHighsInf)
            self._pending_rhs.pop(item._row, None)
        else:
            raise TypeError(f"Cannot remove object of type {type(item)}")

    # ------------------------------------------------------------------------------------------------------------------
    # Constraint recycling
    # ------------------------------------------------------------------------------------------------------------------
    def recycleConstr(self, constr: TempConstr, name: str = "", mark_grew: bool = True):
        """
        Reuse a neutralized row slot for a new constraint.

        If no recycled rows are available, falls back to addConstr().

        Parameters
        ----------
        constr
            A temporary constraint created by a comparison operator.
        name
            Constraint name.
        mark_grew
            If True, mark the model as having grown (triggers IPM on next solve).

        Returns
        -------
        Constr
        """
        if not self._recycled_rows:
            return self.addConstr(constr, name=name)

        row = self._recycled_rows.pop()
        self._removed_rows.discard(row)

        lhs = constr.lhs
        sense = constr.sense
        rhs = constr.rhs

        adjusted_rhs = rhs - lhs._constant

        # Zero out all old coefficients on this row
        old_cols = self._row_coeffs.get(row)
        if old_cols:
            changeCoeff = self._highs.changeCoeff
            for col in old_cols:
                changeCoeff(row, col, 0.0)
                self._coeff_values.pop((row, col), None)
            old_cols.clear()

        # Write new coefficients
        new_cols = set()
        changeCoeff = self._highs.changeCoeff
        for coeff, var in lhs._terms:
            col = var._col
            changeCoeff(row, col, coeff)
            self._coeff_values[(row, col)] = coeff
            new_cols.add(col)

        if new_cols:
            self._row_coeffs[row] = new_cols

        # Set row bounds based on sense
        if sense == _SENSE_EQ:
            lb = adjusted_rhs
            ub = adjusted_rhs
        elif sense == _SENSE_LE:
            lb = -highspy.kHighsInf
            ub = adjusted_rhs
        elif sense == _SENSE_GE:
            lb = adjusted_rhs
            ub = highspy.kHighsInf
        else:
            raise ValueError(f"Unknown constraint sense: {sense}")

        self._highs.changeRowBounds(row, lb, ub)

        if mark_grew:
            self._model_grew = True
            # Set recycled row to kBasic (matches addConstr behavior)
            if self._basis is not None:
                try:
                    self._basis.row_status[row] = HighsBasisStatus.kBasic
                except (IndexError, AttributeError):
                    pass

        constr_obj = Constr(self, row, sense, adjusted_rhs, name)
        self._constr_names[row] = name
        self._constr_objects[row] = constr_obj

        return constr_obj

    # ------------------------------------------------------------------------------------------------------------------
    # Solve
    # ------------------------------------------------------------------------------------------------------------------
    def _flush_pending(self):
        """Flush deferred RHS and Obj changes as batch HiGHS calls."""
        if self._pending_rhs:
            rows = list(self._pending_rhs.keys())
            bounds = list(self._pending_rhs.values())
            n = len(rows)
            indices = np.array(rows, dtype=np.int32)
            lb = np.array([b[0] for b in bounds], dtype=np.float64)
            ub = np.array([b[1] for b in bounds], dtype=np.float64)
            self._highs.changeRowsBounds(n, indices, lb, ub)
            self._pending_rhs.clear()

        if self._pending_obj:
            cols = list(self._pending_obj.keys())
            vals = list(self._pending_obj.values())
            n = len(cols)
            indices = np.array(cols, dtype=np.int32)
            values = np.array(vals, dtype=np.float64)
            self._highs.changeColsCost(n, indices, values)
            self._pending_obj.clear()

    def optimize(self):
        """
        Solve the LP and store the solution.

        Strategy:
        - When model has grown (addVar/addConstr called): IPM with crossover.
          Uses basis extension to warm-start IPM's crossover phase. This
          produces interior solutions needed for fair-share stability.
        - When only RHS/obj/coeff/bounds changed (fair-share iterations,
          remove): simplex with warm-start from previous basis. Very fast
          since only a few pivots are needed.
        - Automatic IPM fallback if simplex returns non-optimal.
        """
        self._ranging_computed = False
        self._ranging_rhs_low = None
        self._ranging_rhs_up = None

        # Flush deferred RHS and objective changes as batch calls
        self._flush_pending()

        if self._model_grew or self._basis is None:
            # Model structure changed — use IPM for interior solution.
            # If we have a prior basis, extend it for crossover warm-start.
            if self._basis is not None:
                basis = self._basis
                old_cols = len(basis.col_status)
                old_rows = len(basis.row_status)
                if old_cols < self._num_cols or old_rows < self._num_rows:
                    ext = highspy.HighsBasis()
                    ext.col_status = list(basis.col_status) + [HighsBasisStatus.kLower] * (self._num_cols - old_cols)
                    ext.row_status = list(basis.row_status) + [HighsBasisStatus.kBasic] * (self._num_rows - old_rows)
                    ext.valid = True
                    self._highs.setBasis(ext)
                else:
                    # Sizes match — set basis directly
                    basis.valid = True
                    self._highs.setBasis(basis)

            self._highs.setOptionValue("solver", "ipm")
            self._highs.setOptionValue("run_crossover", "on")
            self._highs.setOptionValue("presolve", "on")
            self._highs.run()
            self._model_grew = False
        else:
            # Only data changed — simplex warm-start (fast).
            self._highs.setOptionValue("solver", "simplex")
            self._highs.setOptionValue("run_crossover", "off")
            self._highs.setOptionValue("presolve", "off")
            self._highs.setBasis(self._basis)
            self._highs.run()

            # Safety net: if simplex returns non-optimal, fall back to IPM.
            if self._highs.getModelStatus() != HighsModelStatus.kOptimal:
                self._highs.setOptionValue("solver", "ipm")
                self._highs.setOptionValue("run_crossover", "on")
                self._highs.setOptionValue("presolve", "on")
                self._highs.run()

        # Save basis for next warm-start
        try:
            self._basis = self._highs.getBasis()
        except Exception:
            self._basis = None

        # Extract solution as numpy arrays
        sol = self._highs.getSolution()
        self._col_values = np.array(sol.col_value)
        self._row_duals = np.array(sol.row_dual)

    # ------------------------------------------------------------------------------------------------------------------
    # Solution status
    # ------------------------------------------------------------------------------------------------------------------
    @property
    def Status(self):
        """Map HiGHS model status to wrapper constants."""
        status = self._highs.getModelStatus()

        if status == HighsModelStatus.kOptimal:
            return OPTIMAL

        if status == HighsModelStatus.kInfeasible:
            return INFEASIBLE

        if status in (HighsModelStatus.kUnbounded,
                      HighsModelStatus.kUnboundedOrInfeasible):
            return INF_OR_UNBD

        # For other statuses (e.g. not set, error), treat as infeasible/unbounded
        return INF_OR_UNBD

    # ------------------------------------------------------------------------------------------------------------------
    # Ranging (sensitivity analysis)
    # ------------------------------------------------------------------------------------------------------------------
    def _ensure_ranging(self):
        """Compute ranging if not already done since last optimize()."""
        if self._ranging_computed:
            return

        try:
            status, ranging_info = self._highs.getRanging()

            self._ranging_rhs_low = np.array(ranging_info.row_bound_dn.value_)
            self._ranging_rhs_up = np.array(ranging_info.row_bound_up.value_)
        except Exception:
            self._ranging_rhs_low = np.full(self._num_rows, float('nan'))
            self._ranging_rhs_up = np.full(self._num_rows, float('nan'))

        self._ranging_computed = True

    # ------------------------------------------------------------------------------------------------------------------
    # IIS (Irreducible Infeasible Subset)
    # ------------------------------------------------------------------------------------------------------------------
    def computeIIS(self):
        """Compute the Irreducible Infeasible Subset."""
        self._iis_row_flags = [False] * self._num_rows

        try:
            _, iis = self._highs.getIis()
            iis_row_indices = set(iis.row_index_)

            for i in range(self._num_rows):
                self._iis_row_flags[i] = (i in iis_row_indices)

        except Exception:
            # Fallback: mark all non-removed constraints as potentially in IIS
            for i in range(self._num_rows):
                self._iis_row_flags[i] = (i not in self._removed_rows)

    @property
    def IISConstr(self):
        """List of booleans indicating which constraints are in the IIS."""
        if self._iis_row_flags is None:
            return [False] * self._num_rows
        return list(self._iis_row_flags)

    @property
    def ConstrName(self):
        """List of constraint names."""
        return list(self._constr_names)

    # ------------------------------------------------------------------------------------------------------------------
    # Model export
    # ------------------------------------------------------------------------------------------------------------------
    def write(self, filename):
        """Write the model to a file (LP or MPS format, determined by extension)."""
        self._highs.writeModel(filename)


# ======================================================================================================================
# tupledict (compatibility alias)
# ======================================================================================================================

def tupledict():
    """Return a plain dict. The code only uses standard dict operations on tupledict instances."""
    return dict()
