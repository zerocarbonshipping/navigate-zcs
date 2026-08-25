# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Helpers shared by the constraint builders in this package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

import navigate.bunker.solver as gp


def get_constraint(alg: BunkerAlgorithm, container: dict[tuple, gp.Constr], key: tuple,
                   sense: Literal["==", "<=", ">="], name: str) -> gp.Constr:
    """
    Return the constraint stored under a key, creating an empty one if absent.

    A new constraint starts as ``0 <sense> 0``; the caller must set its rhs (where it is
    not the fixed zero) and re-apply every coefficient via ``chgCoeff`` on every build,
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

    full_name = "_".join((name, *map(str, key)))

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
