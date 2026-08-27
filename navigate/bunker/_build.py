# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Get-or-create helpers for the incremental build of the LP model: variables and
constraints are added on first use and reused by the builders on later builds.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

import navigate.bunker.solver as gp


def add_variable(alg: BunkerAlgorithm, container: dict[tuple | str, gp.Var], key: tuple | str, name: str) -> None:
    """
    Add a continuous variable under a key, unless one already exists there.

    Parameters
    ----------
    alg
        The algorithm instance.
    container
        Variable dict of one family on the algorithm (e.g. ``alg.bunker``).
    key
        Key of the variable within the family.
    name
        Base name of the variable family; the key elements are appended
        underscore-separated to name a new variable.
    """

    if key in container:
        return

    container[key] = alg.model.addVar(vtype=gp.GRB.CONTINUOUS, name=_full_name(name, key))


def get_constraint(alg: BunkerAlgorithm, container: dict[tuple, gp.Constr], key: tuple,
                   sense: Literal["==", "<=", ">="], name: str) -> gp.Constr:
    """
    Return the constraint stored under a key, creating an empty one if absent.

    A new constraint starts as ``0 <sense> 0``; the caller must set its rhs (where it is
    not the fixed zero) and re-apply every coefficient via ``model.chgCoeff`` on every build,
    new or reused -- re-applying is what lets a variable created after the constraint
    (e.g. a fuel that later becomes bunkerable at a port) join the row.

    Parameters
    ----------
    alg
        The algorithm instance.
    container
        Constraint dict of one family on the algorithm (e.g. ``alg.tank_capacity``).
    key
        Key of the constraint within the family.
    sense
        One of "==", "<=", ">=".
    name
        Base name of the constraint family; the key elements are appended
        underscore-separated to name a new constraint.

    Returns
    -------
    The existing or newly created constraint.
    """

    if key in container:
        return container[key]

    full_name = _full_name(name, key)

    if sense == "==":
        constraint = alg.model.addConstr(gp.LinExpr() == 0., name=full_name)
    elif sense == "<=":
        constraint = alg.model.addConstr(gp.LinExpr() <= 0., name=full_name)
    elif sense == ">=":
        constraint = alg.model.addConstr(gp.LinExpr() >= 0., name=full_name)
    else:
        raise ValueError("Unknown constraint sense '{}'.".format(sense))

    container[key] = constraint
    return constraint


def _full_name(name: str, key: tuple | str) -> str:
    """
    Name of an LP model element: the key elements appended underscore-separated
    to the family name.

    Parameters
    ----------
    name
        Base name of the element family.
    key
        Key of the element within the family; a scalar key is a single element.

    Returns
    -------
    The family name and key elements joined by underscores.
    """

    if not isinstance(key, tuple):
        key = (key,)

    return "_".join((name, *map(str, key)))
