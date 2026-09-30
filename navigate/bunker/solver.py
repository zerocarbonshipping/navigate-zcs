# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Solver module -- uses Gurobi if licensed, otherwise HiGHS.

Tries to import gurobipy and verify a valid commercial license.
If Gurobi is available and licensed, uses it directly (with a thin
Model subclass for ConstrName/IISConstr compatibility).
Otherwise, falls back to the HiGHS open-source solver.

The active backend can be overridden via ``set_solver_preference()``
before any Model objects are created. Models and linear expressions are
created through ``create_model()`` and ``create_linear_expression()``, which
dispatch on the active backend; the HiGHS classes, whose interface the
Gurobi objects share, serve as the static types for annotations only, and
are never instantiated or checked against at runtime.

Usage:
    import navigate.bunker.solver as gp

    model = gp.create_model("existing")
"""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, Literal

# ---------------------------------------------------------------------------
# HiGHS backend (always available)
# ---------------------------------------------------------------------------
from navigate.bunker import solver_highs as _highs
from navigate.core.enum_ import SolverBackendID

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.bunker.solver_highs import Constr as Constr
    from navigate.bunker.solver_highs import LinExpr as LinExpr
    from navigate.bunker.solver_highs import Model as Model
    from navigate.bunker.solver_highs import Var as Var

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
            with contextlib.suppress(Exception):
                super().__del__()
            with contextlib.suppress(Exception):
                self._gurobi_env.dispose()


# ---------------------------------------------------------------------------
# Static types
# ---------------------------------------------------------------------------
# gurobipy is untyped, so the HiGHS classes stand for both backends in
# annotations (see the TYPE_CHECKING import above); the Gurobi objects
# provide the same interface but are never checked against these classes
# at runtime.

# constraint senses, spelled as gurobipy spells them for both backends
EQUAL = _highs.EQUAL
LESS_EQUAL = _highs.LESS_EQUAL
GREATER_EQUAL = _highs.GREATER_EQUAL

# ---------------------------------------------------------------------------
# Active backend selection
# ---------------------------------------------------------------------------
# bound by _configure(); the values differ per backend
_active_backend: Literal["gurobi", "highs"]
CONTINUOUS: str
OPTIMAL: int
INFEASIBLE: int
INF_OR_UNBD: int


def _configure(preference):
    """Bind module-level solver names according to *preference*."""
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
                "Gurobi preferred but not available -- falling back to HiGHS solver "
                "backend."
            )

    else:  # AUTOMATIC
        if _GUROBI_AVAILABLE:
            use_gurobi = True
            _logger.info("Gurobi license verified -- using Gurobi solver backend.")
        else:
            _logger.info("Gurobi not available -- using HiGHS solver backend.")

    if use_gurobi:
        CONTINUOUS = _grb.GRB.CONTINUOUS
        OPTIMAL = _grb.GRB.OPTIMAL
        INFEASIBLE = _grb.GRB.INFEASIBLE
        INF_OR_UNBD = _grb.GRB.INF_OR_UNBD
        _active_backend = "gurobi"
    else:
        CONTINUOUS = _highs.CONTINUOUS
        OPTIMAL = _highs.OPTIMAL
        INFEASIBLE = _highs.INFEASIBLE
        INF_OR_UNBD = _highs.INF_OR_UNBD
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


def create_model(name: str) -> Model:
    """
    Create an empty LP model on the active backend.

    Parameters
    ----------
    name
        Name of the model.

    Returns
    -------
    Model
        The new model.
    """
    if _active_backend == "gurobi":
        return _GurobiModel(name)

    return _highs.Model(name)


def create_linear_expression(
    coefficients: Sequence[float] | None = None,
    variables: Sequence[Var] | None = None,
) -> LinExpr:
    """
    Create a linear expression on the active backend.

    Without coefficients and variables the expression is empty.

    Parameters
    ----------
    coefficients
        Coefficient of each term.
    variables
        Variable of each term, aligned with ``coefficients``.

    Returns
    -------
    LinExpr
        The sum of the coefficient-variable products.
    """
    if _active_backend == "gurobi":
        if coefficients is None or variables is None:
            return _grb.LinExpr()

        return _grb.LinExpr(coefficients, variables)

    return _highs.LinExpr(coefficients, variables)


# Initial configuration: auto-detect (preserves original default behaviour).
_configure(SolverBackendID.AUTOMATIC)
