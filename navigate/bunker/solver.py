# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Solver module -- uses Gurobi if licensed, otherwise HiGHS.

Tries to import gurobipy and verify a valid commercial license.
If Gurobi is available and licensed, uses it directly (with a thin
Model subclass for ConstrName/IISConstr compatibility).
Otherwise, falls back to the HiGHS open-source solver.

The active backend can be overridden via ``set_solver_preference()``
before any Model objects are created.

Usage:
    import navigate.bunker.solver as gp
    from navigate.bunker.solver import GRB
"""

import logging

# ---------------------------------------------------------------------------
# HiGHS backend (always available)
# ---------------------------------------------------------------------------
from navigate.bunker.solver_highs import CONTINUOUS as _highs_CONTINUOUS
from navigate.bunker.solver_highs import GRB as _highs_GRB
from navigate.bunker.solver_highs import INF_OR_UNBD as _highs_INF_OR_UNBD
from navigate.bunker.solver_highs import INFEASIBLE as _highs_INFEASIBLE
from navigate.bunker.solver_highs import OPTIMAL as _highs_OPTIMAL
from navigate.bunker.solver_highs import Constr as _highs_Constr
from navigate.bunker.solver_highs import LinExpr as _highs_LinExpr
from navigate.bunker.solver_highs import Model as _highs_Model
from navigate.bunker.solver_highs import Var as _highs_Var
from navigate.bunker.solver_highs import tupledict as _highs_tupledict
from navigate.core.enum_ import SolverBackendID

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Detect Gurobi availability at import time (does NOT choose the backend yet)
# ---------------------------------------------------------------------------
_GUROBI_AVAILABLE = False

try:
    import gurobipy as _grb

    # gurobipy can be pip-installed without a license.
    # Creating an Env and starting it is the only reliable license check.
    # empty=True suppresses the Gurobi banner on stdout.
    _test_env = _grb.Env(empty=True)
    _test_env.setParam("OutputFlag", 0)
    _test_env.start()
    _test_env.dispose()
    del _test_env
    _GUROBI_AVAILABLE = True

except ImportError:
    pass

except Exception:
    pass


# ---------------------------------------------------------------------------
# Gurobi backend (only if licensed)
# ---------------------------------------------------------------------------
if _GUROBI_AVAILABLE:

    _grb_GRB = _grb.GRB
    _grb_LinExpr = _grb.LinExpr
    _grb_Constr = _grb.Constr
    _grb_Var = _grb.Var
    _grb_CONTINUOUS = _grb_GRB.CONTINUOUS
    _grb_OPTIMAL = _grb_GRB.OPTIMAL
    _grb_INFEASIBLE = _grb_GRB.INFEASIBLE
    _grb_INF_OR_UNBD = _grb_GRB.INF_OR_UNBD

    def _grb_tupledict():
        """Return a gurobipy tupledict."""
        return _grb.tupledict()

    class _GurobiModel(_grb.Model):
        """Thin subclass adding model-level ConstrName/IISConstr lists."""

        def __init__(self, name=""):
            self._gurobi_env = _grb.Env(empty=True)
            self._gurobi_env.setParam("OutputFlag", 0)
            self._gurobi_env.start()
            super().__init__(name, env=self._gurobi_env)

        @property
        def ConstrName(self):
            """List of constraint names (all constraints in model order)."""
            return [c.ConstrName for c in self.getConstrs()]

        @property
        def IISConstr(self):
            """List of booleans for IIS membership (all constraints in model order)."""
            return [bool(c.IISConstr) for c in self.getConstrs()]

        def __del__(self):
            try:
                super().__del__()
            except Exception:
                pass
            try:
                self._gurobi_env.dispose()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Active backend selection
# ---------------------------------------------------------------------------
_active_backend = None          # "gurobi" or "highs", set by _configure()

# Module-level names that consumers import.  Initialised by _configure().
GRB = None
LinExpr = None
Constr = None
Var = None
Model = None
tupledict = None
CONTINUOUS = None
OPTIMAL = None
INFEASIBLE = None
INF_OR_UNBD = None


def _configure(preference):
    """Bind module-level solver names according to *preference*."""
    global GRB, LinExpr, Constr, Var, Model, tupledict
    global CONTINUOUS, OPTIMAL, INFEASIBLE, INF_OR_UNBD
    global _active_backend

    use_gurobi = False

    if preference == SolverBackendID.HIGHS:
        _logger.info("HiGHS solver backend selected by user preference.")

    elif preference == SolverBackendID.GUROBI:
        if _GUROBI_AVAILABLE:
            use_gurobi = True
            _logger.info("Gurobi solver backend selected by user preference.")
        else:
            _logger.warning(
                "Gurobi preferred but not available -- falling back to HiGHS solver backend."
            )

    else:  # AUTOMATIC
        if _GUROBI_AVAILABLE:
            use_gurobi = True
            _logger.info("Gurobi license verified -- using Gurobi solver backend.")
        else:
            _logger.info("Gurobi not available -- using HiGHS solver backend.")

    if use_gurobi:
        GRB = _grb_GRB
        LinExpr = _grb_LinExpr
        Constr = _grb_Constr
        Var = _grb_Var
        Model = _GurobiModel
        tupledict = _grb_tupledict
        CONTINUOUS = _grb_CONTINUOUS
        OPTIMAL = _grb_OPTIMAL
        INFEASIBLE = _grb_INFEASIBLE
        INF_OR_UNBD = _grb_INF_OR_UNBD
        _active_backend = "gurobi"
    else:
        GRB = _highs_GRB
        LinExpr = _highs_LinExpr
        Constr = _highs_Constr
        Var = _highs_Var
        Model = _highs_Model
        tupledict = _highs_tupledict
        CONTINUOUS = _highs_CONTINUOUS
        OPTIMAL = _highs_OPTIMAL
        INFEASIBLE = _highs_INFEASIBLE
        INF_OR_UNBD = _highs_INF_OR_UNBD
        _active_backend = "highs"


def set_solver_preference(preference: SolverBackendID):
    """
    Reconfigure the solver backend.

    Must be called **before** any ``Model`` objects are created.

    Parameters
    ----------
    preference
        AUTOMATIC (default), GUROBI, or HIGHS.
    """
    _configure(preference)


def get_active_backend():
    """Return ``\"gurobi\"`` or ``\"highs\"`` for the currently active backend."""
    return _active_backend


# Initial configuration: auto-detect (preserves original default behaviour).
_configure(SolverBackendID.AUTOMATIC)
