# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import timeit
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

import navigate.bunker.solver as gp
from navigate.core.enum_ import BunkerScopeID
from navigate.exceptions import InfeasibleLPError


def optimize(alg: BunkerAlgorithm) -> None:
    """
    Optimize the built model and check the feasibility of the solution.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    start = timeit.default_timer()

    alg.model.optimize()
    check_solution(alg)

    end = timeit.default_timer()
    alg.solve_time += end - start


def check_solution(alg: BunkerAlgorithm) -> None:
    """
    Checks the solution of the LP model after a call to 'model.optimize'.
    If the model is infeasible, the IIS is calculated and an LP file with the limiting constraints are exported.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    # set the dual reductions to 1,
    # in case it was previously set 0
    # due to an infeasible or unbounded error
    alg.model.Params.DualReductions = 1

    status = alg.model.Status

    if status == gp.GRB.OPTIMAL:
        return

    elif status == gp.GRB.INFEASIBLE:

        alg.model.computeIIS()
        iis = [alg.model.ConstrName[i] for i, infeasible in enumerate(alg.model.IISConstr) if infeasible]

        directory = alg.output_directory or ''
        alg.model.write(os.path.join(directory, "bunkering_infeasible.ilp"))
        alg.model.write(os.path.join(directory, "bunkering_infeasible.lp"))

        # error message for fleet bunkering
        scope = 'existing' if alg.scope == BunkerScopeID.EXISTING else 'expected'
        raise InfeasibleLPError("Optimal bunkering was infeasible for {} bunkering"
                                " due to the IIS limiting constraint: {}.".format(scope, ', '.join(iis)))

    elif status == gp.GRB.INF_OR_UNBD:

        # set the dual reduction parameter to 0 and reoptimize to get a more conclusive result
        alg.model.Params.DualReductions = 0
        optimize(alg)


def write_binding_lp(m: object, filename: str = "binding.lp", tol: float = 1e-6) -> None:
    """
    Export binding constraints from solved model to LP file (for debugging).

    Parameters
    ----------
    m
        Solved LP model.
    filename
        Output file name.
    tol
        Tolerance for considering a constraint binding.
    """

    if m.SolCount == 0:
        raise RuntimeError("No solution available.")

    # New model
    rm = gp.Model("binding_subset")
    rm.Params.OutputFlag = 0

    # Copy variables
    xmap = {}
    for v in m.getVars():
        xmap[v.VarName] = rm.addVar(
            lb=v.LB, ub=v.UB, vtype=v.VType, name=v.VarName
        )
    rm.update()

    # Copy objective
    obj = gp.LinExpr()
    for v in m.getVars():
        coef = v.Obj
        if coef != 0.0:
            obj += coef * xmap[v.VarName]
    rm.setObjective(obj, m.ModelSense)

    # Add only binding linear constraints
    for c in m.getConstrs():
        if abs(c.Slack) > tol:
            continue

        row = m.getRow(c)  # linear expression for this constraint
        expr = gp.LinExpr()
        for i in range(row.size()):
            v = row.getVar(i)
            expr += row.getCoeff(i) * xmap[v.VarName]

        # Recreate with same sense/RHS
        if c.Sense == gp.GRB.LESS_EQUAL:
            rm.addConstr(expr <= c.RHS, name=c.ConstrName)
        elif c.Sense == gp.GRB.GREATER_EQUAL:
            rm.addConstr(expr >= c.RHS, name=c.ConstrName)
        else:
            rm.addConstr(expr == c.RHS, name=c.ConstrName)

    rm.update()
    rm.write(filename)
