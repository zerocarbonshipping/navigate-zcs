# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Provide get-or-create helpers for the incremental LP model build.

Variables and constraints are added on first use and reused by the builders on
later builds.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import EnergyDemandID

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.nodes.route import Route
    from navigate.simulation.bunker._solver import Constraint, Sense, Variable
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm

# a part of an LP element's key: a node name, a stop index or an energy demand type
type _KeyPart = str | int | EnergyDemandID

# the key of an LP element within its family: a single name, or the parts the element
# spans, led by the vessel name where the element is a vessel's
type _ElementKey = str | tuple[_KeyPart, ...]
type VesselKey = tuple[str, *tuple[_KeyPart, ...]]


def add_variable[K: _ElementKey](
    alg: BunkerAlgorithm,
    container: dict[K, Variable],
    key: K,
    name: str,
    route: Route | None = None,
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
        Name of the variable family, which with the key names a new variable.
    route
        Route whose stops the integers in the key index; None for a key that holds
        no stop.
    """
    if key in container:
        return

    container[key] = alg.model.add_variable(_full_name(name, key, route))


def get_constraint[K: _ElementKey](
    alg: BunkerAlgorithm,
    container: dict[K, Constraint],
    key: K,
    sense: Sense,
    name: str,
    route: Route | None = None,
    *,
    priced: bool = False,
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
        Name of the constraint family, which with the key names a new constraint.
    route
        Route whose stops the integers in the key index; None for a key that holds
        no stop.
    priced
        Whether the bunker reads the constraint's dual; only a priced constraint's
        dual is selected by a solve and can be read.

    Returns
    -------
    Constraint
        The existing or newly created constraint.
    """
    if key in container:
        return container[key]

    full_name = _full_name(name, key, route)
    constraint = alg.model.add_constraint(sense, full_name, priced=priced)
    container[key] = constraint
    return constraint


def _full_name(name: str, key: _ElementKey, route: Route | None) -> str:
    """
    Return the name of an LP model element, as ``bunker("vessel","port",0,"fuel")``.

    Distinct elements get distinct names, as a solve selects among equally good
    solutions by the names of the variables. A node name is therefore quoted: it may
    hold any character but a double quote, also the one that separates the parts.

    A stop is named by its port and call number (``Route.get_stop_labels``), not by
    its index, so that the solution selected does not follow the order the route
    lists its ports in.

    Parameters
    ----------
    name
        Name of the element family.
    key
        Key of the element within the family; a scalar key is a single part.
    route
        Route whose stops the integers in the key index; None for a key that holds
        no stop.

    Returns
    -------
    str
        The family name, then the key parts in parentheses, separated by commas.
    """
    if not isinstance(key, tuple):
        key = (key,)

    stop_labels = () if route is None else route.get_stop_labels()
    parts = ",".join(_format_key_part(part, stop_labels) for part in key)

    return f"{name}({parts})"


def _format_key_part(part: _KeyPart, stop_labels: Sequence[tuple[str, int]]) -> str:
    """
    Return a key part as it stands in a name.

    A node name is quoted and an energy demand type bare. A stop index is two parts,
    the port name and the call number of its label in ``stop_labels``.
    """
    if isinstance(part, str):
        return f'"{part}"'

    if isinstance(part, EnergyDemandID):
        return part.name

    port_name, call = stop_labels[part]

    return f'"{port_name}",{call}'
