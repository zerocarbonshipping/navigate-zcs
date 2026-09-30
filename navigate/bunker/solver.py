# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Solver facade of the bunker algorithm: Gurobi when licensed, HiGHS otherwise.

Whether gurobipy is installed and licensed is checked at import;
``set_solver_preference()`` picks the backend before any model is created.
Models and linear expressions are created through ``create_model()`` and
``create_linear_expression()``, which dispatch on the active backend. gurobipy is
untyped, so the HiGHS classes, whose interface the Gurobi objects share, serve as
the static types for both; they are imported for annotations only, never
instantiated or checked against at runtime.

Usage:
    import navigate.bunker.solver as gp

    model = gp.create_model("existing")
"""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, Literal

from navigate.bunker import solver_highs as _highs
from navigate.core.enum_ import SolverBackendID

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.bunker.solver_highs import Constr as Constr
    from navigate.bunker.solver_highs import LinExpr as LinExpr
    from navigate.bunker.solver_highs import Model as Model
    from navigate.bunker.solver_highs import Var as Var

_logger = logging.getLogger(__name__)

_GUROBI_AVAILABLE = False

try:
    import gurobipy as _grb

    # gurobipy installs without a license, and starting an environment is the
    # only reliable license check; an empty environment keeps the banner off
    # stdout
    _test_env = _grb.Env(empty=True)
    _test_env.setParam("OutputFlag", 0)
    _test_env.start()
    _test_env.dispose()
    del _test_env
    _GUROBI_AVAILABLE = True

except Exception:
    # gurobipy is missing or unlicensed
    pass


if _GUROBI_AVAILABLE:

    class _GurobiModel(_grb.Model):
        """A gurobipy model with model-level ConstrName and IISConstr lists."""

        def __init__(self, name: str) -> None:
            self._gurobi_env: _grb.Env = _grb.Env(empty=True)
            self._gurobi_env.setParam("OutputFlag", 0)
            self._gurobi_env.start()
            super().__init__(name, env=self._gurobi_env)

        @property
        def ConstrName(self) -> list[str]:
            """Name of each constraint, in model order."""
            return [c.ConstrName for c in self.getConstrs()]

        @property
        def IISConstr(self) -> list[bool]:
            """Whether each constraint is in the IIS, in model order."""
            return [bool(c.IISConstr) for c in self.getConstrs()]

        def __del__(self) -> None:
            with contextlib.suppress(Exception):
                super().__del__()
            with contextlib.suppress(Exception):
                self._gurobi_env.dispose()


# constraint senses, spelled as gurobipy spells them for both backends
EQUAL = _highs.EQUAL
LESS_EQUAL = _highs.LESS_EQUAL
GREATER_EQUAL = _highs.GREATER_EQUAL

# bound by _configure(); the values differ per backend
_active_backend: Literal["gurobi", "highs"]
CONTINUOUS: str
OPTIMAL: int
INFEASIBLE: int
INF_OR_UNBD: int


def _configure(preference: SolverBackendID) -> None:
    """Bind the module-level solver names to the backend *preference* selects."""
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

    else:
        # automatic
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


def set_solver_preference(preference: SolverBackendID) -> None:
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
            expression: LinExpr = _grb.LinExpr()
        else:
            expression = _grb.LinExpr(coefficients, variables)
        return expression

    return _highs.LinExpr(coefficients, variables)


# automatic detection holds until a deck sets a preference
_configure(SolverBackendID.AUTOMATIC)
