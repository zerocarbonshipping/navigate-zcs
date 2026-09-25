# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Validation of the values a deck assigns, shared by every DSL setter.

A value failing its attribute's requirements raises a ValueError carrying only
a partial message; the parser catches it and completes it with the deck
location and the attribute assigned to.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Protocol

import numpy as np

from navigate.core.expression import Expression
from navigate.core.node import Node
from navigate.core.node_type import (
    CALCULATOR_TYPES,
    AcceptedNodeTypes,
    is_calculator,
)
from navigate.core.scalar import Scalar
from navigate.core.table_data import TableData
from navigate.core.wrap import Assignment
from navigate.util import (
    ROUND_OFF,
    TOLERANCE,
    key_name,
    list_is_unique,
    name_contains_wildcards,
    retrieve_keys,
    unique_list,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence, Sized

_BOOL_ID = {"FALSE": False, "TRUE": True}
_BOUND_ID = {"-INF": -np.inf, "INF": np.inf}

# an exact length, or a lower and an upper bound either of which may be open
type ListLength = int | tuple[int | None, int | None] | None

# kind words for the values a setter can be handed; a value of no kind listed
# here is echoed in the error instead, as its own text is what identifies it.
# 'bool' precedes 'int' because it is a subclass of it, and the first match wins
_VALUE_KINDS = (
    (Expression, "expression"),
    ((list, tuple), "list"),
    (TableData, "table"),
    ((float, Scalar), "scalar"),
    (np.datetime64, "date"),
    (bool, "boolean"),
    (int, "integer"),
)


class _CommandDict[K, V](Protocol):
    """
    Command-written dictionary, as the command helpers use it.

    Its values are only written, never read, so a dictionary whose values are
    wider than V passes: one keeping None for an entry left unassigned takes
    an assigned V all the same, which a 'dict[K, V]' parameter would refuse.
    """

    def __iter__(self) -> Iterator[K]: ...

    def __len__(self) -> int: ...

    def __setitem__(self, key: K, value: V, /) -> None: ...


def assign_integer(
    assignment: float,
    lower: float = -np.inf,
    upper: float = np.inf,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
) -> int:
    """
    Validate an integer assignment against bounds and return it as int.

    Parameters
    ----------
    assignment
        The value passed to the setter.
    lower
        Lower bound.
    upper
        Upper bound.
    inclusive_lower
        Lower bound is inclusive.
    inclusive_upper
        Upper bound is inclusive.

    Returns
    -------
    int
        The value that was passed, as an int, so a setter assigns what it
        validated.
    """
    _check_scalar(
        assignment,
        lower=lower,
        upper=upper,
        inclusive_lower=inclusive_lower,
        inclusive_upper=inclusive_upper,
    )

    value = round(assignment)

    if abs(value - assignment) >= TOLERANCE:
        raise ValueError(f"only allows assignment of integers, but got {assignment}")

    return value


def assign_value[T: Assignment](
    assignment: T,
    scalar: bool = True,
    type_: AcceptedNodeTypes = None,
    lower: float = -np.inf,
    upper: float = np.inf,
    *,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
    expression: bool = True,
) -> T:
    """
    Check whether a value assigned to an attribute satisfies its requirements.

    Only applicable to attributes requiring a single value, not lists. A setter
    passing scalar=False must pass a non-empty type_; that is an implementation
    requirement, so it goes unchecked.

    Parameters
    ----------
    assignment
        The value passed to the setter.
    scalar
        Whether the setter accepts scalars.
    type_
        The node type(s) the attribute accepts a reference to.
    lower
        Lower bound.
    upper
        Upper bound.
    inclusive_lower
        Lower bound is inclusive.
    inclusive_upper
        Upper bound is inclusive.
    expression
        Whether the setter accepts expressions; one is accepted only where the
        setter also accepts scalars or a calculator type, as only those are
        evaluated.

    Returns
    -------
    Assignment
        The value that was passed, so a setter assigns what it validated.
    """
    if isinstance(assignment, Expression):
        if not (expression and _evaluates(scalar, type_)):
            raise ValueError(_failed_value_message(assignment, scalar, type_))

        assignment.set_allowed_types(type_)
        assignment.set_internal_bounds(lower, upper)
    elif scalar and isinstance(assignment, (float, Scalar)):
        _check_scalar(
            assignment,
            lower=lower,
            upper=upper,
            inclusive_lower=inclusive_lower,
            inclusive_upper=inclusive_upper,
        )
    elif isinstance(assignment, Node) and _accepts_reference(assignment, type_):
        # a calculator answers a getter with a value of its own, so it is the
        # only reference kind the attribute bounds have anything to clip
        if is_calculator(assignment):
            assignment.set_internal_bounds(lower, upper)
    else:
        raise ValueError(_failed_value_message(assignment, scalar, type_))

    return assignment


def assign_list[T: Assignment](
    assignment: list[T],
    length: ListLength = None,
    unique: bool = False,
    scalar: bool = True,
    type_: AcceptedNodeTypes = None,
    lower: float = -np.inf,
    upper: float = np.inf,
    *,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
    expression: bool = True,
) -> list[T]:
    """
    Check whether a value assigned to an attribute satisfies its requirements.

    Only applicable to attributes requiring a list of values.

    Parameters
    ----------
    assignment
        List of values passed to the setter.
    length
        Exact length the list should have or lower and upper bound. Any falsy
        length makes no check, ``0`` as well as ``None``.
    unique
        Whether all entries in the list must be unique.
    scalar
        Whether the setter accepts scalars.
    type_
        The node type(s) the attribute accepts a reference to.
    lower
        Lower bound.
    upper
        Upper bound.
    inclusive_lower
        Lower bound is inclusive.
    inclusive_upper
        Upper bound is inclusive.
    expression
        Whether the setter accepts expressions; one is accepted only where the
        setter also accepts scalars or a calculator type, as only those are
        evaluated.

    Returns
    -------
    list[Assignment]
        The list that was passed, so a setter assigns what it validated.
    """
    _check_list_length(assignment, length)

    if unique:
        _check_list_is_unique(assignment)

    for value in assignment:
        assign_value(
            value,
            scalar,
            type_,
            lower,
            upper,
            inclusive_lower=inclusive_lower,
            inclusive_upper=inclusive_upper,
            expression=expression,
        )

    return assignment


def assign_boolean(assignment: str) -> bool:
    """
    Check whether the value assigned to a boolean attribute is a boolean keyword.

    Parameters
    ----------
    assignment
        Value passed to the setter.

    Returns
    -------
    bool
        Value of the keyword.
    """
    if not isinstance(assignment, str):
        raise ValueError(_only_allows("TRUE or FALSE", assignment))

    try:
        return _BOOL_ID[assignment]
    except KeyError:
        raise ValueError(_only_allows("TRUE or FALSE", assignment)) from None


def assign_date(assignment: object) -> np.datetime64:
    """
    Check whether the value assigned to a date attribute is a date.

    Parameters
    ----------
    assignment
        Value passed to the setter.

    Returns
    -------
    np.datetime64
        The date that was passed, so a setter assigns what it validated.
    """
    if isinstance(assignment, np.datetime64):
        return assignment

    raise ValueError(_only_allows("dates", assignment))


def assign_bound(assignment: float | str) -> float:
    """
    Check whether a bound assignment is a scalar or an infinity keyword.

    Parameters
    ----------
    assignment
        Value passed to the setter.

    Returns
    -------
    float
        The scalar itself, or the value of the keyword.
    """
    if isinstance(assignment, float):
        return assign_value(assignment)

    if not isinstance(assignment, str):
        raise ValueError(_only_allows("scalars, -INF or INF", assignment))

    try:
        return _BOUND_ID[assignment]
    except KeyError:
        raise ValueError(_only_allows("scalars, -INF or INF", assignment)) from None


def assign_id[E: Enum](assignment: str, id_enum: type[E]) -> E:
    """
    Check whether the assigned ID satisfies the requirements of that attribute.

    Parameters
    ----------
    assignment
        Value passed to the setter.
    id_enum
        Enum class the assigned name is looked up in.

    Returns
    -------
    Enum
        The member the assigned ID names, so a setter assigns what it validated.
    """
    if not isinstance(assignment, str):
        raise ValueError(_only_allows("IDs", assignment))

    try:
        return id_enum[assignment]
    except KeyError:
        if name_contains_wildcards(assignment):
            raise ValueError(
                f"does not accept ID '{assignment}' — wildcards are not supported "
                "for this command"
            ) from None

        raise ValueError(f"does not accept ID '{assignment}'") from None


def assign_member[E: Enum](assignment: str, members: tuple[E, ...]) -> E:
    """
    Check whether the ID assigned to an attribute is one the attribute accepts.

    For an attribute holding a subset of an enum: only the members passed in
    are accepted.

    Parameters
    ----------
    assignment
        Value passed to the setter.
    members
        The enum members the attribute accepts.

    Returns
    -------
    Enum
        The member the assigned ID names, so a setter assigns what it validated.
    """
    if not isinstance(assignment, str):
        raise ValueError(_only_allows("IDs", assignment))

    for member in members:
        if member.name == assignment:
            return member

    raise ValueError(_only_allows(_member_names(members), assignment))


def expand_id_wildcard[E: Enum](
    pattern: str, domain: type[E] | tuple[E, ...]
) -> list[E]:
    """
    Expand a wildcard pattern against the member names of a domain.

    Parameters
    ----------
    pattern
        Glob-style pattern (e.g. ``"M*"``), matched against each member's ``.name``.
    domain
        Enum class, or tuple of its members, the pattern may match.

    Returns
    -------
    list[Enum]
        Matching enum members.
    """
    members = tuple(domain)
    by_name = {member.name: member for member in members}

    try:
        names = retrieve_keys(pattern, list(by_name))
    except KeyError:
        raise ValueError(
            f"wildcard '{pattern}' did not match any of {_member_names(members)}"
        ) from None

    return [by_name[name] for name in names]


def assign_id_list[E: Enum](
    assignment: list[str],
    id_enum: type[E],
    length: ListLength = None,
) -> list[E]:
    """
    Check whether an assigned ID satisfies an attribute's requirements.

    Only applicable to attributes requiring a list of values. Supports wildcard
    patterns which are expanded before the length check.

    Parameters
    ----------
    assignment
        List of values passed to the setter.
    id_enum
        Enum class the assigned name is looked up in.
    length
        Exact length the list should have or lower and upper bound. Any falsy
        length makes no check, ``0`` as well as ``None``.

    Returns
    -------
    list[Enum]
        The members the assigned IDs name, with wildcards expanded.
    """
    expanded = []
    for value in assignment:
        if isinstance(value, str) and name_contains_wildcards(value):
            expanded.extend(expand_id_wildcard(value, id_enum))
        else:
            expanded.append(assign_id(value, id_enum))

    _check_list_length(expanded, length)
    return expanded


def assign_fraction_list(fractions: list[float]) -> tuple[list[float], bool]:
    """
    Check whether a value assigned to an attribute satisfies its requirements.

    Only applicable to attributes requiring a list of values summing to 1.
    Entries are floated first, so a list written as integers is rescaled the
    same way as its float spelling.

    Parameters
    ----------
    fractions
        List of fractions passed to the setter.

    Returns
    -------
    tuple[list[float], bool]
        The fractions, rescaled to sum to 1, and whether they were rescaled by
        more than one percent.
    """
    _check_fraction_list(fractions)

    fractions = [float(fraction) for fraction in fractions]

    rescaled = False
    total = round(sum(fractions), ROUND_OFF)

    if fractions and (total != 1.0) and (total > 0.0):
        fractions = [fraction / total for fraction in fractions]
        rescaled = abs(total - 1) > 0.01

    return assign_list(fractions, lower=0.0, upper=1.0), rescaled


def command_assignment_to_dict[K: str | Enum, V: Assignment](
    key: K | str,
    assignment: V,
    assignment_dict: _CommandDict[K, V],
    scalar: bool = True,
    type_: AcceptedNodeTypes = None,
    lower: float = -np.inf,
    upper: float = np.inf,
    *,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
    expression: bool = True,
) -> None:
    """
    Assign a validated value to each dict entry matching a key pattern.

    Parameters
    ----------
    key
        Name of node, possibly including wildcards.
    assignment
        Value assigned to every matched entry, a float already wrapped in
        a Scalar by the setter.
    assignment_dict
        The dictionary being assigned to.
    scalar
        Whether the setter accepts scalars.
    type_
        The node type(s) the attribute accepts a reference to.
    lower
        Lower bound.
    upper
        Upper bound.
    inclusive_lower
        Lower bound is inclusive.
    inclusive_upper
        Upper bound is inclusive.
    expression
        Whether the setter accepts expressions; one is accepted only where the
        setter also accepts scalars or a calculator type, as only those are
        evaluated.
    """
    keys = retrieve_keys(key, assignment_dict)

    # every matched key holds the same object: a Scalar answers a getter and
    # carries no per-key state, and a node or an expression was always shared
    value = assign_value(
        assignment,
        scalar,
        type_,
        lower,
        upper,
        inclusive_lower=inclusive_lower,
        inclusive_upper=inclusive_upper,
        expression=expression,
    )

    for key_ in keys:
        assignment_dict[key_] = value


def command_assignment_to_tuple_dict[K1: str | Enum, K2: str | Enum, V: Assignment](
    key: tuple[K1 | str, K2 | str],
    assignment: V,
    assignment_dict: _CommandDict[tuple[K1, K2], V],
    scalar: bool = True,
    type_: AcceptedNodeTypes = None,
    lower: float = -np.inf,
    upper: float = np.inf,
    *,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
    expression: bool = True,
) -> None:
    """
    Assign a validated value to dict entries keyed by matching tuples.

    Parameters
    ----------
    key
        Tuple of node names, possibly including wildcards.
    assignment
        Value assigned to every matched entry, a float already wrapped in
        a Scalar by the setter.
    assignment_dict
        The dictionary being assigned to.
    scalar
        Whether the setter accepts scalars.
    type_
        The node type(s) the attribute accepts a reference to.
    lower
        Lower bound.
    upper
        Upper bound.
    inclusive_lower
        Lower bound is inclusive.
    inclusive_upper
        Upper bound is inclusive.
    expression
        Whether the setter accepts expressions; one is accepted only where the
        setter also accepts scalars or a calculator type, as only those are
        evaluated.
    """
    if not assignment_dict:
        raise KeyError(", ".join(key_name(key_part) for key_part in key))

    columns = zip(*assignment_dict, strict=True)
    keys = [
        retrieve_keys(key_part, unique_list(existing_keys))
        for key_part, existing_keys in zip(key, columns, strict=True)
    ]

    keys1, keys2 = keys
    value = assign_value(
        assignment,
        scalar,
        type_,
        lower,
        upper,
        inclusive_lower=inclusive_lower,
        inclusive_upper=inclusive_upper,
        expression=expression,
    )

    for key1 in keys1:
        for key2 in keys2:
            assignment_dict[(key1, key2)] = value


def command_assignment_to_boolean_dict[K: str | Enum](
    key: K | str,
    assignment: str,
    assignment_dict: dict[K, bool],
    allow_empty: bool = False,
) -> None:
    """
    Assign a boolean value to dict keys matching a key pattern.

    Parameters
    ----------
    key
        Key to assignment_dict. May include wildcards.
    assignment
        Boolean value TRUE or FALSE.
    assignment_dict
        Dict to assign the boolean value to.
    allow_empty
        Whether no matches are allowed for wildcards.
    """
    value = assign_boolean(assignment)

    try:
        names = retrieve_keys(key, assignment_dict)
    except KeyError:
        if allow_empty and isinstance(key, str) and name_contains_wildcards(key):
            # wildcards in a shared include are written against whatever the
            # deck defines, so a pattern that matches nothing is not an error
            return

        raise KeyError(key) from None

    for name in names:
        assignment_dict[name] = value


def _accepts_reference(node: Node, type_: AcceptedNodeTypes) -> bool:
    """
    Check whether an attribute accepting 'type_' accepts a reference to a node.

    Parameters
    ----------
    node
        The node the deck named.
    type_
        The node type(s) the attribute accepts a reference to.

    Returns
    -------
    bool
        Whether the node is of a type the attribute allows.
    """
    if type_ is None:
        return False

    if isinstance(type_, tuple):
        return node.type in type_

    return node.is_type(type_)


def _evaluates(scalar: bool, type_: AcceptedNodeTypes) -> bool:
    """
    Check whether an attribute reads its value through a getter.

    Only such an attribute evaluates an expression; one holding a node
    reference reads the node itself.

    Parameters
    ----------
    scalar
        Whether the setter accepts scalars.
    type_
        The node type(s) the attribute accepts a reference to.

    Returns
    -------
    bool
        Whether the attribute accepts scalars or a calculator type.
    """
    if scalar:
        return True

    if type_ is None:
        return False

    types = type_ if isinstance(type_, tuple) else (type_,)
    return any(accepted in CALCULATOR_TYPES for accepted in types)


def _failed_value_message(
    assignment: object, scalar: bool, type_: AcceptedNodeTypes
) -> str:
    """
    Build the error message for a value an attribute does not accept.

    Parameters
    ----------
    assignment
        The value passed to the setter.
    scalar
        Whether the setter accepts scalars.
    type_
        The node type(s) the attribute accepts a reference to.

    Returns
    -------
    str
        Error message of a failed error check.
    """
    # a setter accepting no kind at all, and an empty 'type_', are
    # implementation errors rather than deck errors, so neither the empty
    # 'allowed' nor the empty subscript below is handled (see assign_value)
    allowed = []
    if scalar:
        allowed.append("scalars")
    if type_ is not None:
        if isinstance(type_, str):
            allowed.append(f"nodes of type {type_}")
        else:
            allowed.append(
                "nodes of type {} or {}".format(", ".join(type_[:-1]), type_[-1])
            )

    if len(allowed) == 1:
        joined = allowed[0]
    else:
        joined = ", ".join(allowed[:-1]) + " and " + allowed[-1]

    return _only_allows(joined, assignment)


def _only_allows(allowed: str, assignment: object) -> str:
    """
    Spell the sentence every rejected value is reported with.

    Parameters
    ----------
    allowed
        What the setter accepts, already joined into one phrase.
    assignment
        The value passed to the setter.

    Returns
    -------
    str
        Error message of a failed error check.
    """
    return f"only allows assignment of {allowed}, but got {_value_kind(assignment)}"


def _member_names(members: tuple[Enum, ...]) -> str:
    """
    Spell the members a setter accepts, so both its spellings name the same set.

    Parameters
    ----------
    members
        The enum members the setter accepts.

    Returns
    -------
    str
        The member names, in the order the setter accepts them.
    """
    return ", ".join(member.name for member in members)


def _value_kind(assignment: object) -> str:
    """
    Name the kind of a value, or echo the value when it has no listed kind.

    Parameters
    ----------
    assignment
        The value passed to the setter.

    Returns
    -------
    str
        Kind word of the value, or the value itself.
    """
    for types, kind in _VALUE_KINDS:
        if isinstance(assignment, types):
            return kind

    return str(assignment)


def _check_scalar(
    assignment: float | Scalar,
    lower: float = -np.inf,
    upper: float = np.inf,
    *,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
) -> None:
    """
    Validate that a scalar value satisfies the given bounds.

    Parameters
    ----------
    assignment
        Value being assigned, rejected unless it is a float or a Scalar.
    lower
        Lower bound.
    upper
        Upper bound.
    inclusive_lower
        If True, allow value == lower. If False, require value > lower.
    inclusive_upper
        If True, allow value == upper. If False, require value < upper.

    Raises
    ------
    ValueError
        If the assignment does not satisfy the bounds.
    """
    if isinstance(assignment, float):
        value = assignment
    elif isinstance(assignment, Scalar):
        value = assignment.get()
    else:
        raise ValueError(f"requires a scalar, but got {_value_kind(assignment)}")

    if inclusive_lower and value < lower:
        raise ValueError(f"must be ≥ {lower}, but got {value}")

    if not inclusive_lower and value <= lower:
        raise ValueError(f"must be > {lower}, but got {value}")

    if inclusive_upper and value > upper:
        raise ValueError(f"must be ≤ {upper}, but got {value}")

    if not inclusive_upper and value >= upper:
        raise ValueError(f"must be < {upper}, but got {value}")


def _check_list_length(assignment: Sized, length: ListLength) -> None:
    """
    Validate a list's length against an exact length or a lower and upper bound.

    Parameters
    ----------
    assignment
        The list whose length is checked.
    length
        Exact length, or lower and upper bound. Any falsy length makes no
        check, ``0`` as well as ``None``.
    """
    if not length:
        return

    if isinstance(length, tuple):
        lower, upper = length

        if (lower is not None) and (len(assignment) < lower):
            raise ValueError(f"List must contain at least {lower} values.")

        if (upper is not None) and (len(assignment) > upper):
            raise ValueError(f"List must contain at most {upper} values.")
    elif len(assignment) != length:
        raise ValueError(f"List must contain exactly {length} values.")


def _check_list_is_unique(assignment: Sequence[Assignment]) -> None:
    """
    Validate that no node is named twice in a list.

    Parameters
    ----------
    assignment
        The list whose node references are checked.
    """
    names = [entry.name for entry in assignment if isinstance(entry, Node)]
    if not list_is_unique(names):
        raise ValueError("requires all entries in the list to be unique")


def _check_fraction_list(fractions: list[float]) -> None:
    """
    Validate that an assignment is a list of non-negative plain numbers.

    Parameters
    ----------
    fractions
        The value passed to the setter.
    """
    if not isinstance(fractions, list):
        raise ValueError("only allows assignment of lists")

    # a non-number would reach the comparison below as a TypeError carrying no
    # deck line for the parser to report; int, and the bool that subclasses it,
    # pass because assign_fraction_list floats every entry it is handed
    for fraction in fractions:
        if not isinstance(fraction, (int, float)):
            raise ValueError(_only_allows("plain numbers", fraction))

        if fraction < 0.0:
            raise ValueError("does not allow negative values")
