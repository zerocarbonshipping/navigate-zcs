# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Provide get-or-create helpers for the incremental LP model build.

Variables and constraints are added on first use and reused by the builders on
later builds.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.core.enum_ import EnergyDemandID
    from navigate.simulation.bunker._solver import Constraint, Sense, Variable
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm

# the key of an LP element within its family: a single name, or the node names,
# route indices and energy demand type the element spans
type _ElementKey = str | tuple[str | int | EnergyDemandID, ...]


def add_variable[K: _ElementKey](
    alg: BunkerAlgorithm,
    container: dict[K, Variable],
    key: K,
    name: str,
) -> None:
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

    container[key] = alg.model.add_variable(_full_name(name, key))


def get_constraint[K: _ElementKey](
    alg: BunkerAlgorithm,
    container: dict[K, Constraint],
    key: K,
    sense: Sense,
    name: str,
) -> Constraint:
    """
    Return the constraint stored under a key, creating an empty one if absent.

    A new constraint starts as ``0 <sense> 0``; the caller must set its rhs (where it is
    not the fixed zero) and re-apply every coefficient via ``model.set_coefficient`` on
    every build, new or reused -- re-applying is what lets a variable created after the
    constraint (e.g. a fuel that later becomes bunkerable at a port) join the row.
    A variable that leaves the row must be written at zero, not skipped.

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
    Constraint
        The existing or newly created constraint.
    """
    if key in container:
        return container[key]

    constraint = alg.model.add_constraint(sense, _full_name(name, key))
    container[key] = constraint
    return constraint


def _full_name(name: str, key: _ElementKey) -> str:
    """
    Return the name of an LP model element.

    The key elements are appended underscore-separated to the family name.

    Parameters
    ----------
    name
        Base name of the element family.
    key
        Key of the element within the family; a scalar key is a single element.

    Returns
    -------
    str
        The family name and key elements joined by underscores.
    """
    if not isinstance(key, tuple):
        key = (key,)

    return "_".join((name, *map(str, key)))
