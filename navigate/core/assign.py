# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.expression import Expression
from navigate.core.node import Node
from navigate.core.node_type import AcceptedTypes, is_calculator
from navigate.core.scalar import Scalar
from navigate.core.table_data import TableData
from navigate.core.wildcard import WildcardNodeReference
from navigate.core.wrap import Assignment, WrappedAssignment, as_scalar
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
    from collections.abc import Sequence, Sized

_BOOL_ID = {"FALSE": False, "TRUE": True}
_BOUND_ID = {"-INF": -np.inf, "INF": np.inf}

# an exact length, or a lower and an upper bound either of which may be open
type ListLength = int | tuple[int | None, int | None] | None

# kind words for the values a setter can be handed; a value of no kind listed
# here is echoed in the error instead, as its own text is what identifies it.
# 'bool' precedes 'int' because it is a subclass of it, and the first match wins
_VALUE_KINDS = (
    ((list, tuple), "list"),
    (TableData, "table"),
    ((float, Scalar), "scalar"),
    (np.datetime64, "date"),
    (bool, "boolean"),
    (int, "integer"),
)


def assign_integer(
    assignment: float,
    lower: float = -np.inf,
    upper: float = np.inf,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
) -> int:
    """

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
    int:
        Returns the passed assignment as integer (to allow error checking while assigning)
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
    date: bool = False,
    type_: AcceptedTypes = None,
    lower: float = -np.inf,
    upper: float = np.inf,
    *,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
) -> T:
    """
    Check whether the value (float or calculator) assigned to an attribute satisfy the requirements of that attribute.
    Only applicable to attributes requiring a single value, not lists.

    The method assumes that if scalar=False, type_ must not be None (or an empty list). No check is made for this
    as it is an implementation requirement, not a user input issue.

    If the requirements are not satisfied a ValueError is raised. Note that this error is only a partial message
    designed to be caught at a higher level.

    Parameters
    ----------
    assignment
        The value passed to the setter.
    scalar
        Whether the setter accepts scalars.
    date
        Whether the setter accepts dates.
    type_
        Type(s) of Node that attribute allows.
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
    Assignment
        The value that was passed, so a setter assigns what it validated.
    """
    is_float = isinstance(assignment, (float, Scalar))
    is_date = isinstance(assignment, np.datetime64)
    is_expression = isinstance(assignment, Expression)
    is_node = isinstance(assignment, Node)
    is_wildcard = isinstance(assignment, WildcardNodeReference)
    type_is_list = isinstance(type_, (list, tuple))

    float_allowed = is_float and scalar
    date_allowed = is_date and date
    reference_allowed = (
        (is_node or is_wildcard)
        and (type_ is not None)
        and (assignment.type in type_ if type_is_list else assignment.is_type(type_))
    )

    if float_allowed:
        _check_scalar(
            assignment,
            lower=lower,
            upper=upper,
            inclusive_lower=inclusive_lower,
            inclusive_upper=inclusive_upper,
        )

    elif is_expression:
        assignment.set_allowed_types(type_)

    elif not (date_allowed or reference_allowed):
        raise ValueError(_failed_value_message(assignment, scalar, date, type_))

    # only a calculator has bounds to tighten; is_calculator reads the type tag,
    # which a wildcard of a calculator type carries too, and its matches get none
    if is_expression or (is_node and is_calculator(assignment)):
        assignment.set_internal_bounds(lower, upper)

    return assignment


def assign_list[T: Assignment](
    assignment: list[T],
    length: ListLength = None,
    unique: bool = False,
    scalar: bool = True,
    date: bool = False,
    type_: AcceptedTypes = None,
    lower: float = -np.inf,
    upper: float = np.inf,
    *,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
) -> list[T]:
    """
    Check whether the value (float or calculator) assigned to an attribute satisfy the requirements of that attribute.
    Only applicable to attributes requiring a list of values.

    If the requirements are not satisfied a ValueError is raised. Note that this error is only a partial message
    designed to be caught at a higher level.

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
    date
        Whether the setter accepts dates.
    type_
        Type(s) of Node that attribute allows.
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
            date,
            type_,
            lower,
            upper,
            inclusive_lower=inclusive_lower,
            inclusive_upper=inclusive_upper,
        )

    return assignment


def assign_boolean(assignment: object) -> bool:
    """
    Check whether the value assigned to a boolean attribute is a boolean keyword.

    If the requirements are not satisfied a ValueError is raised. Note that this error is only a partial message
    designed to be caught at a higher level.

    Parameters
    ----------
    assignment
        Value passed to the setter.

    Returns
    -------
    bool
        Value of the keyword.
    """
    try:
        return _BOOL_ID[assignment]

    # a list or a table reaches the lookup as an unhashable key, and the
    # TypeError that raises carries no deck line for the parser to report
    except (KeyError, TypeError):
        raise ValueError(_only_allows("TRUE or FALSE", assignment))


def assign_bound(assignment: object) -> float:
    """
    Check whether the value assigned to a bound attribute is a scalar or an infinity keyword.

    If the requirements are not satisfied a ValueError is raised. Note that this error is only a partial message
    designed to be caught at a higher level.

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

    try:
        return _BOUND_ID[assignment]

    # a list or a table reaches the lookup as an unhashable key, and the
    # TypeError that raises carries no deck line for the parser to report
    except (KeyError, TypeError):
        raise ValueError(_only_allows("scalars, -INF or INF", assignment))


def assign_id[E: Enum](assignment: object, id_enum: type[E]) -> E:
    """
    Check whether the ID assigned to an attribute satisfy the requirements of that attribute.

    If the requirements are not satisfied a ValueError is raised. Note that this error is only a partial message
    designed to be caught at a higher level.

    Parameters
    ----------
    assignment
        Value passed to the setter.
    id_enum
        Enumerator.

    Returns
    -------
    Enum
        Returns the passed assignment (to allow error checking while assigning).
    """
    try:
        return id_enum[assignment]

    # a list or a table reaches the lookup as an unhashable key, and the
    # wildcard test below only reads a string
    except (KeyError, TypeError):
        if not isinstance(assignment, str):
            raise ValueError(_only_allows("IDs", assignment))

        if name_contains_wildcards(assignment):
            raise ValueError(
                f"does not accept ID '{assignment}' — wildcards are not supported "
                "for this command"
            )
        raise ValueError(f"does not accept ID '{assignment}'")


def assign_member[E: Enum](assignment: object, members: tuple[E, ...]) -> E:
    """
    Check whether the ID assigned to an attribute is one the attribute accepts.

    The sibling of :func:`assign_id` for an attribute holding a subset of an
    enum: ``assign_id`` subscripts the enum class, which a tuple of members
    cannot answer, and would accept every member the class has.

    If the requirements are not satisfied a ValueError is raised. Note that this error is only a partial message
    designed to be caught at a higher level.

    Parameters
    ----------
    assignment
        Value passed to the setter.
    members
        The enum members the attribute accepts.

    Returns
    -------
    Enum
        Returns the passed assignment (to allow error checking while assigning).
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

    Delegates to :func:`retrieve_keys` which handles Enum-keyed collections.

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

    try:
        return retrieve_keys(pattern, members, key_fn=lambda m: m.name)
    except KeyError:
        raise ValueError(
            f"wildcard '{pattern}' did not match any of {_member_names(members)}"
        )


def assign_id_list[E: Enum](
    assignment: list[object],
    id_enum: type[E],
    length: ListLength = None,
) -> list[E]:
    """
    Check whether the ID assigned to an attribute satisfy the requirements of that attribute.
    Only applicable to attributes requiring a list of values. Supports wildcard patterns
    which are expanded before the length check.

    If the requirements are not satisfied a ValueError is raised. Note that this error is only a partial message
    designed to be caught at a higher level.

    Parameters
    ----------
    assignment
        List of values passed to the setter.
    id_enum
        Enumerator.
    length
        Exact length the list should have or lower and upper bound. Any falsy
        length makes no check, ``0`` as well as ``None``.

    Returns
    -------
    list[Enum] :
        Returns the passed assignment (to allow error checking while assigning).
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
    Check whether the value (float or calculator) assigned to an attribute satisfy the requirements of that attribute.
    Only applicable to attributes requiring a list of values.
    Additionally, requires that the sum of values in the list sum to 1.

    A list summing to anything else is rescaled proportionally, and the flag
    says whether the deviation was large enough for the setter to report it.

    If the requirements are not satisfied a ValueError is raised. Note that this error is only a partial message
    designed to be caught at a higher level.

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

    rescaled = False
    total = round(sum(fractions), ROUND_OFF)

    if fractions and (total != 1.0) and (total > 0.0):
        fractions = [fraction / total for fraction in fractions]
        rescaled = abs(total - 1) > 0.01

    return assign_list(fractions, lower=0.0, upper=1.0), rescaled


def command_assignment_to_dict[K: str | Enum](
    key: K | str,
    assignment: Assignment,
    assignment_dict: dict[K, WrappedAssignment | None],
    scalar: bool = True,
    date: bool = False,
    type_: AcceptedTypes = None,
    lower: float = -np.inf,
    upper: float = np.inf,
    *,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
) -> None:
    """

    Parameters
    ----------
    key
        Name of node, possibly including wildcards.
    assignment
        Assignment to dict.
    assignment_dict
        The dictionary being assigned to.
    scalar
        Whether the setter accepts scalars.
    date
        Whether the setter accepts dates.
    type_
        Type(s) of Node that attribute allows.
    lower
        Lower bound.
    upper
        Upper bound.
    inclusive_lower
        Lower bound is inclusive.
    inclusive_upper
        Upper bound is inclusive.
    """
    keys = retrieve_keys(key, assignment_dict)

    # every matched key holds the same object: a Scalar answers a getter and
    # carries no per-key state, and a node or an expression was always shared
    value = assign_value(
        as_scalar(assignment),
        scalar,
        date,
        type_,
        lower,
        upper,
        inclusive_lower=inclusive_lower,
        inclusive_upper=inclusive_upper,
    )

    for key_ in keys:
        assignment_dict[key_] = value


def command_assignment_to_tuple_dict[K1: str | Enum, K2: str | Enum](
    key: tuple[K1 | str, K2 | str],
    assignment: Assignment,
    assignment_dict: dict[tuple[K1, K2], WrappedAssignment | None],
    scalar: bool = True,
    date: bool = False,
    type_: AcceptedTypes = None,
    lower: float = -np.inf,
    upper: float = np.inf,
    *,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
) -> None:
    """

    Parameters
    ----------
    key
        Tuple of node names, possibly including wildcards.
    assignment
        Assignment to dict.
    assignment_dict
        The dictionary being assigned to.
    scalar
        Whether the setter accepts scalars.
    date
        Whether the setter accepts dates.
    type_
        Type(s) of Node that attribute allows.
    lower
        Lower bound.
    upper
        Upper bound.
    inclusive_lower
        Lower bound is inclusive.
    inclusive_upper
        Upper bound is inclusive.
    """
    keys = [
        retrieve_keys(k, unique_list(keys))
        for k, keys in zip(key, zip(*assignment_dict.keys()))
    ]

    if not keys:
        raise KeyError(", ".join(key_name(k) for k in key))

    keys1, keys2 = keys
    value = assign_value(
        as_scalar(assignment),
        scalar,
        date,
        type_,
        lower,
        upper,
        inclusive_lower=inclusive_lower,
        inclusive_upper=inclusive_upper,
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
        if allow_empty and name_contains_wildcards(key):
            # TODO logging.warning()
            return
        else:
            raise KeyError(key)

    for name in names:
        assignment_dict[name] = value


def _failed_value_message(
    assignment: object, scalar: bool, date: bool, type_: AcceptedTypes
) -> str:
    """
    Build the error message for a value an attribute does not accept.

    Parameters
    ----------
    assignment
        The value passed to the setter.
    scalar
        Whether the setter accepts scalars.
    date
        Whether the setter accepts dates.
    type_
        Type(s) of Node that attribute allows.

    Returns
    -------
    str :
        Error message of a failed error check.
    """
    # a setter accepting no kind at all, and an empty 'type_', are
    # implementation errors rather than deck errors, so neither the empty
    # 'allowed' nor the empty subscript below is handled (see assign_value)
    allowed = []

    if scalar:
        allowed.append("scalars")

    if date:
        allowed.append("dates")

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
    str :
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
    str :
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
    str :
        Kind word of the value, or the value itself.
    """
    for types, kind in _VALUE_KINDS:
        if isinstance(assignment, types):
            return kind

    return str(assignment)


def _check_scalar(
    assignment: object,
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

    if inclusive_lower:
        if value < lower:
            raise ValueError(f"must be ≥ {lower}, but got {value}")
    else:
        if value <= lower:
            raise ValueError(f"must be > {lower}, but got {value}")

    if inclusive_upper:
        if value > upper:
            raise ValueError(f"must be ≤ {upper}, but got {value}")
    else:
        if value >= upper:
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
    if length:
        if isinstance(length, tuple):
            lower, upper = length

            if (lower is not None) and (len(assignment) < lower):
                raise ValueError(f"List must contain at least {lower} values.")

            if (upper is not None) and (len(assignment) > upper):
                raise ValueError(f"List must contain at most {upper} values.")

        else:
            if len(assignment) != length:
                raise ValueError(f"List must contain exactly {length} values.")


def _check_list_is_unique(assignment: Sequence[Assignment]) -> None:
    names = [
        entry.name
        for entry in assignment
        if isinstance(entry, (Node, WildcardNodeReference))
    ]
    if not list_is_unique(names):
        raise ValueError("requires all entries in the list to be unique")


def _check_fraction_list(fractions: object) -> None:
    if not isinstance(fractions, list):
        raise ValueError("only allows assignment of lists")

    # a non-number would reach the comparison below as a TypeError carrying no
    # deck line for the parser to report; a deck writes floats only, and the
    # integer list a Python caller can pass is accepted when it rescales
    for fraction in fractions:
        if not isinstance(fraction, (int, float)):
            raise ValueError(_only_allows("plain numbers", fraction))

        if fraction < 0.0:
            raise ValueError("does not allow negative values")
