# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Validation of the values a deck assigns, shared by every DSL setter.

A value failing its attribute's requirements raises a ValueError carrying only
a partial message; the parser catches it and completes it with the deck
location and the attribute assigned to.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import TYPE_CHECKING, Protocol

import numpy as np

from navigate.core.expression import Expression
from navigate.core.node import Node
from navigate.core.node_type import AcceptedNodeTypes, is_calculator
from navigate.core.scalar import Scalar
from navigate.core.table_data import TableData
from navigate.core.types_ import Calculator
from navigate.core.wrap import as_list
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

# everything a validator may be handed for a single-valued attribute read
# through a getter: a bare float, or a value that already answers a getter.
# An attribute holding a node reference is typed by its node class instead.
# The alias is the contract for typed callers, not a claim about what reaches
# the boundary at runtime: the parser is untyped, so it hands every deck value
# in as 'Any' and a deck can name any shape the grammar accepts - a bare
# string, a list, a TableData. That is why the validators here keep runtime
# reject arms for values their typed callers never pass.
type Assignment = float | Scalar | Calculator | Expression

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
    type_: AcceptedNodeTypes | None = None,
    lower: float = -np.inf,
    upper: float = np.inf,
    *,
    allow_scalar: bool = True,
    allow_expression: bool = True,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
) -> T:
    """
    Check whether a value assigned to an attribute satisfies its requirements.

    Only applicable to attributes requiring a single value read through a
    getter: a scalar, a calculator or an expression. An attribute holding a
    node reference is checked by assign_reference instead. A calculator or an
    expression is handed the bounds and held to them each time it is
    evaluated.

    Parameters
    ----------
    assignment
        The value passed to the setter.
    type_
        The calculator type(s) the attribute accepts.
    lower
        Lower bound.
    upper
        Upper bound.
    allow_scalar
        Whether the setter accepts scalars.
    allow_expression
        Whether the setter accepts expressions.
    inclusive_lower
        Lower bound is inclusive.
    inclusive_upper
        Upper bound is inclusive.

    Returns
    -------
    Assignment
        The value that was passed, so a setter assigns what it validated.
    """
    if isinstance(assignment, Expression):
        if not allow_expression:
            raise ValueError(_failed_value_message(assignment, allow_scalar, type_))

        assignment.set_allowed_types(type_)
        assignment.set_internal_bounds(
            lower,
            upper,
            inclusive_lower=inclusive_lower,
            inclusive_upper=inclusive_upper,
        )
    elif allow_scalar and isinstance(assignment, (float, Scalar)):
        _check_scalar(
            assignment,
            lower=lower,
            upper=upper,
            inclusive_lower=inclusive_lower,
            inclusive_upper=inclusive_upper,
        )
    elif (
        isinstance(assignment, Node)
        and is_calculator(assignment)
        and _accepts_reference(assignment, type_)
    ):
        assignment.set_internal_bounds(
            lower,
            upper,
            inclusive_lower=inclusive_lower,
            inclusive_upper=inclusive_upper,
        )
    else:
        raise ValueError(_failed_value_message(assignment, allow_scalar, type_))

    return assignment


def assign_list[T: Assignment](
    assignment: list[T],
    min_length: int = 0,
    type_: AcceptedNodeTypes | None = None,
    lower: float = -np.inf,
    upper: float = np.inf,
    *,
    allow_expression: bool = True,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
) -> list[T]:
    """
    Check whether a value assigned to an attribute satisfies its requirements.

    Only applicable to attributes requiring a list of values read through a
    getter, each checked as assign_value checks a single one; a list of node
    references is checked by assign_reference_list instead.

    Parameters
    ----------
    assignment
        List of values passed to the setter.
    min_length
        Fewest values the list may contain.
    type_
        The calculator type(s) the attribute accepts.
    lower
        Lower bound.
    upper
        Upper bound.
    allow_expression
        Whether the setter accepts expressions.
    inclusive_lower
        Lower bound is inclusive.
    inclusive_upper
        Upper bound is inclusive.

    Returns
    -------
    list[Assignment]
        The list that was passed, so a setter assigns what it validated.
    """
    _check_list_length(assignment, min_length)

    for value in assignment:
        assign_value(
            value,
            type_=type_,
            lower=lower,
            upper=upper,
            allow_expression=allow_expression,
            inclusive_lower=inclusive_lower,
            inclusive_upper=inclusive_upper,
        )

    return assignment


def assign_reference[N: Node](assignment: N, type_: AcceptedNodeTypes) -> N:
    """
    Check whether a node assigned to an attribute is of a type it references.

    Only applicable to attributes holding a single node reference, which is
    read as the node itself rather than through a getter.

    Parameters
    ----------
    assignment
        The value passed to the setter.
    type_
        The node type(s) the attribute accepts a reference to.

    Returns
    -------
    Node
        The node that was passed, so a setter assigns what it validated.
    """
    # an expression has nothing to evaluate it at a reference, so it is
    # refused by kind like any other value that is not an accepted node
    if not (isinstance(assignment, Node) and _accepts_reference(assignment, type_)):
        raise ValueError(_only_allows(_node_types_phrase(type_), assignment))

    return assignment


def assign_reference_list[N: Node](
    assignment: N | list[N], type_: AcceptedNodeTypes, *, unique: bool = False
) -> list[N]:
    """
    Check whether the nodes assigned to an attribute are of a type it references.

    Only applicable to attributes holding a list of node references, each
    checked as assign_reference checks a single one. A deck may give a single
    value where the attribute takes a list, so a bare node is accepted and
    returned wrapped in a list.

    Parameters
    ----------
    assignment
        Value or list of values passed to the setter.
    type_
        The node type(s) the attribute accepts a reference to.
    unique
        Whether no node may be named twice in the list.

    Returns
    -------
    list[Node]
        The list that was passed, or the single value wrapped in one, so a
        setter assigns what it validated.
    """
    references = as_list(assignment)

    if unique:
        _check_list_is_unique(references)

    for reference in references:
        assign_reference(reference, type_)

    return references


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


def assign_date(assignment: np.datetime64) -> np.datetime64:
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
    assignment: str | list[str],
    id_enum: type[E],
    min_length: int = 0,
) -> list[E]:
    """
    Check whether an assigned ID satisfies an attribute's requirements.

    Only applicable to attributes requiring a list of values. A deck may give a
    single ID where the attribute takes a list, so a bare ID is accepted and
    wrapped in a list. Supports wildcard patterns which are expanded before the
    length check.

    Parameters
    ----------
    assignment
        ID or list of IDs passed to the setter.
    id_enum
        Enum class the assigned name is looked up in.
    min_length
        Fewest members the list may contain once wildcards are expanded.

    Returns
    -------
    list[Enum]
        The members the assigned IDs name, with wildcards expanded.
    """
    expanded = []
    for value in as_list(assignment):
        if isinstance(value, str) and name_contains_wildcards(value):
            expanded.extend(expand_id_wildcard(value, id_enum))
        else:
            expanded.append(assign_id(value, id_enum))

    _check_list_length(expanded, min_length)
    return expanded


def assign_fraction_list(fractions: list[float]) -> tuple[list[float], bool]:
    """
    Check whether a value assigned to an attribute satisfies its requirements.

    Only applicable to attributes requiring a list of values summing to 1.
    Entries are floated first, so a list written as integers is rescaled the
    same way as its float spelling; the guard has already rejected any entry,
    or total, that does not float to a finite value. The entries must sum to
    more than 0 once rounded to ``ROUND_OFF`` decimals, so an all-zero list
    and an empty list are rejected: a zero total cannot be rescaled to 1. Any
    other total than 1 is rescaled proportionally.

    Parameters
    ----------
    fractions
        List of fractions passed to the setter.

    Returns
    -------
    tuple[list[float], bool]
        The fractions, rescaled to sum to 1, and whether they were rescaled by
        more than one percent.

    Raises
    ------
    ValueError
        If the entries do not sum to more than 0.
    """
    _check_fraction_list(fractions)

    fractions = [float(fraction) for fraction in fractions]

    rescaled = False
    total = round(sum(fractions), ROUND_OFF)

    if not total > 0.0:
        raise ValueError("requires entries summing to more than 0")

    if total != 1.0:
        fractions = [fraction / total for fraction in fractions]
        rescaled = abs(total - 1) > 0.01

    return assign_list(fractions, lower=0.0, upper=1.0), rescaled


def write_matching_keys[K: str | Enum, V](
    key: K | str,
    value: V,
    assignment_dict: _CommandDict[K, V],
) -> None:
    """
    Write an already validated value to each dict entry matching a key pattern.

    Parameters
    ----------
    key
        Name of node, possibly including wildcards.
    value
        Value assigned to every matched entry, validated by the caller.
    assignment_dict
        The dictionary being assigned to.
    """
    keys = retrieve_keys(key, assignment_dict)

    # every matched key holds the same object: a Scalar answers a getter and
    # carries no per-key state, and a node or an expression was always shared
    for key_ in keys:
        assignment_dict[key_] = value


def write_matching_key_pairs[K1: str | Enum, K2: str | Enum, V](
    key: tuple[K1 | str, K2 | str],
    value: V,
    assignment_dict: _CommandDict[tuple[K1, K2], V],
) -> None:
    """
    Write an already validated value to dict entries keyed by matching tuples.

    Parameters
    ----------
    key
        Tuple of node names, possibly including wildcards.
    value
        Value assigned to every matched entry, validated by the caller.
    assignment_dict
        The dictionary being assigned to.
    """
    if not assignment_dict:
        raise KeyError(", ".join(key_name(key_part) for key_part in key))

    columns = zip(*assignment_dict, strict=True)
    keys = [
        retrieve_keys(key_part, unique_list(existing_keys))
        for key_part, existing_keys in zip(key, columns, strict=True)
    ]

    # every matched key holds the same object: a Scalar answers a getter and
    # carries no per-key state, and a node or an expression was always shared
    keys1, keys2 = keys
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


def _accepts_reference(node: Node, type_: AcceptedNodeTypes | None) -> bool:
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


def _failed_value_message(
    assignment: object, allow_scalar: bool, type_: AcceptedNodeTypes | None
) -> str:
    """
    Build the error message for a value an attribute does not accept.

    Parameters
    ----------
    assignment
        The value passed to the setter.
    allow_scalar
        Whether the setter accepts scalars.
    type_
        The node type(s) the attribute accepts a reference to.

    Returns
    -------
    str
        Error message of a failed error check.
    """
    # a setter accepting no kind at all is an implementation error rather
    # than a deck error, so the empty 'allowed' is not handled
    allowed = []
    if allow_scalar:
        allowed.append("scalars")
    if type_ is not None:
        allowed.append(_node_types_phrase(type_))

    if len(allowed) == 1:
        joined = allowed[0]
    else:
        joined = ", ".join(allowed[:-1]) + " and " + allowed[-1]

    return _only_allows(joined, assignment)


def _node_types_phrase(type_: AcceptedNodeTypes) -> str:
    """
    Spell the node types an attribute accepts, as its rejection names them.

    Parameters
    ----------
    type_
        The node type(s) the attribute accepts.

    Returns
    -------
    str
        The phrase naming the accepted node types.
    """
    # an empty tuple is an implementation error rather than a deck error, so
    # the empty subscript below is not handled
    if isinstance(type_, str):
        return f"nodes of type {type_}"

    return "nodes of type {} or {}".format(", ".join(type_[:-1]), type_[-1])


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


def _check_list_length(assignment: Sized, min_length: int) -> None:
    """
    Validate that a list contains at least a minimum number of values.

    Parameters
    ----------
    assignment
        The list whose length is checked.
    min_length
        Fewest values the list may contain.
    """
    if len(assignment) < min_length:
        raise ValueError(f"List must contain at least {min_length} values.")


def _check_list_is_unique(assignment: Sequence[Node]) -> None:
    """
    Validate that no node is named twice in a list.

    Parameters
    ----------
    assignment
        The list whose node references are checked.
    """
    # the parser hands the list in untyped, and an entry that is no node is
    # refused by assign_reference once the names are known to be unique
    names = [entry.name for entry in assignment if isinstance(entry, Node)]
    if not list_is_unique(names):
        raise ValueError("requires all entries in the list to be unique")


def _check_fraction_list(fractions: list[float]) -> None:
    """
    Validate that an assignment is a list of non-negative finite numbers.

    Every entry must be a plain number that floats to a finite value, and the
    float total must be finite too, so the rescale in assign_fraction_list
    can neither overflow nor turn an entry into NaN.

    Parameters
    ----------
    fractions
        The value passed to the setter.
    """
    if not isinstance(fractions, list):
        raise ValueError("only allows assignment of lists")

    # a non-number would reach the comparison below as a TypeError carrying no
    # deck line for the parser to report; int, and the bool that subclasses it,
    # pass because assign_fraction_list floats every entry it is handed, so
    # each entry is floated here first: an int too large for a float would
    # otherwise escape that floating as an OverflowError, which the parser
    # cannot locate either
    floated = []
    for fraction in fractions:
        if not isinstance(fraction, (int, float)):
            raise ValueError(_only_allows("plain numbers", fraction))

        try:
            value = float(fraction)
        except OverflowError:
            raise ValueError(
                "only allows assignment of finite numbers, "
                "but got a number too large for a float"
            ) from None

        # ahead of the sign check, which NaN passes because it never compares:
        # an infinite entry would rescale to NaN, and a NaN entry stays one
        if not math.isfinite(value):
            raise ValueError(
                f"only allows assignment of finite numbers, but got {value}"
            )

        if value < 0.0:
            raise ValueError("does not allow negative values")

        floated.append(value)

    # finite entries can still sum past the largest float, and the rescale
    # divides by that sum
    if not math.isfinite(sum(floated)):
        raise ValueError("requires entries whose sum is finite")
