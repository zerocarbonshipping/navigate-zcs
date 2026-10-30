# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Validation of the values a deck assigns, shared by every DSL setter.

A value failing its attribute's requirements raises a ValueError carrying only
a partial message; the parser catches it and completes it with the deck
location and the attribute assigned to. The checks a node runs from its
lifecycle hooks, once the tables its values reference are built, name the node
and the attribute themselves.
"""

from __future__ import annotations

import logging
import math
from enum import Enum
from typing import TYPE_CHECKING, Protocol

import numpy as np

from navigate.core._bounds import Bounds
from navigate.core.enum_ import ExtrapolateID
from navigate.core.expression import Expression
from navigate.core.node import Node
from navigate.core.node_type import AcceptedNodeTypes, accepts_type, is_calculator
from navigate.core.scalar import Scalar
from navigate.core.table_data import TableData
from navigate.core.types_ import Calculator, CurveTableInput
from navigate.core.wrap import as_list
from navigate.util import (
    ROUND_OFF,
    TOLERANCE,
    is_nondecreasing,
    is_unique,
    key_name,
    name_contains_wildcards,
    retrieve_keys,
    unique_list,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Hashable, Iterator, Sequence, Sized

    from navigate.core.nodes.forecast import Forecast

logger = logging.getLogger(__name__)

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
type _Assignment = float | Scalar | Calculator | Expression

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
    *,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
) -> int:
    """
    Validate an integer assignment against bounds and return it as int.

    Infinity is always rejected, as no integer is infinite.

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
    bounds = _resolve_bounds(
        lower, upper, inclusive_lower, inclusive_upper, allow_infinite=False
    )
    _check_scalar(assignment, bounds)

    value = round(assignment)

    if abs(value - assignment) >= TOLERANCE:
        raise ValueError(f"only allows assignment of integers, but got {assignment}")

    return value


def assign_value[T: _Assignment](
    assignment: T,
    type_: AcceptedNodeTypes | None = None,
    lower: float = -np.inf,
    upper: float = np.inf,
    *,
    allow_scalar: bool = True,
    allow_expression: bool = True,
    allow_infinite: bool = False,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
) -> T:
    """
    Check whether a value assigned to an attribute satisfies its requirements.

    Only applicable to attributes requiring a single value read through a
    getter: a scalar, a calculator or an expression. An attribute holding a
    node reference is checked by assign_reference instead. A calculator or an
    expression is handed the bounds and held to them each time it is
    evaluated. Unless infinity is allowed, an infinite bound is exclusive, so
    INF and -INF are rejected where the attribute has no finite bound.

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
    allow_infinite
        Whether the setter accepts INF and -INF within its bounds.
    inclusive_lower
        Lower bound is inclusive.
    inclusive_upper
        Upper bound is inclusive.

    Returns
    -------
    T
        The value that was passed, so a setter assigns what it validated.
    """
    bounds = _resolve_bounds(
        lower, upper, inclusive_lower, inclusive_upper, allow_infinite=allow_infinite
    )

    if isinstance(assignment, Expression):
        if not allow_expression:
            raise ValueError(_failed_value_message(assignment, allow_scalar, type_))

        assignment.set_allowed_types(type_)
        assignment.set_internal_bounds(bounds)
    elif allow_scalar and isinstance(assignment, (float, Scalar)):
        _check_scalar(assignment, bounds)
    elif (
        isinstance(assignment, Node)
        and is_calculator(assignment)
        and accepts_type(type_, assignment.type)
    ):
        assignment.set_internal_bounds(bounds)
    else:
        raise ValueError(_failed_value_message(assignment, allow_scalar, type_))

    return assignment


def assign_list[T: _Assignment](
    assignment: list[T],
    min_length: int = 0,
    type_: AcceptedNodeTypes | None = None,
    lower: float = -np.inf,
    upper: float = np.inf,
    *,
    allow_expression: bool = True,
    allow_infinite: bool = False,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
) -> list[T]:
    """
    Check each value of a list assigned to an attribute against its requirements.

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
    allow_infinite
        Whether the setter accepts INF and -INF within its bounds.
    inclusive_lower
        Lower bound is inclusive.
    inclusive_upper
        Upper bound is inclusive.

    Returns
    -------
    list[T]
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
            allow_infinite=allow_infinite,
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
    if not (isinstance(assignment, Node) and accepts_type(type_, assignment.type)):
        raise ValueError(_only_allows(_node_types_phrase(type_), assignment))

    return assignment


def assign_reference_list[N: Node](
    assignment: N | list[N],
    type_: AcceptedNodeTypes,
    min_length: int = 0,
    *,
    unique: bool = False,
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
    min_length
        Fewest nodes the list may contain.
    unique
        Whether no node may be named twice in the list.

    Returns
    -------
    list[Node]
        The list that was passed, or the single value wrapped in one, so a
        setter assigns what it validated.
    """
    references = as_list(assignment)
    _check_list_length(references, min_length)

    if unique:
        # the parser hands the list in untyped, and an entry that is no node
        # is refused by assign_reference once the names are known to be unique
        names = [entry.name for entry in references if isinstance(entry, Node)]
        _check_list_is_unique(names)

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
    if not (isinstance(assignment, str) and assignment in _BOOL_ID):
        raise ValueError(_only_allows("TRUE or FALSE", assignment))

    return _BOOL_ID[assignment]


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
    if not isinstance(assignment, np.datetime64):
        raise ValueError(_only_allows("dates", assignment))

    return assignment


def assign_bound(
    assignment: float | str,
    *,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
) -> float:
    """
    Check whether a bound assignment is a scalar or an infinity keyword.

    A bound accepts infinity, INF meaning no upper bound and -INF no lower
    one; the setter of each excludes the infinity on the other side through
    the inclusive flags.

    Parameters
    ----------
    assignment
        Value passed to the setter.
    inclusive_lower
        Whether the bound may be -INF.
    inclusive_upper
        Whether the bound may be INF.

    Returns
    -------
    float
        The scalar itself, or the value of the keyword.
    """
    if isinstance(assignment, str):
        assignment = _BOUND_ID.get(assignment, assignment)

    if not isinstance(assignment, float):
        raise ValueError(_only_allows("scalars, -INF or INF", assignment))

    return assign_value(
        assignment,
        allow_infinite=True,
        inclusive_lower=inclusive_lower,
        inclusive_upper=inclusive_upper,
    )


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

    names = ", ".join(member.name for member in members)
    raise ValueError(_only_allows(names, assignment))


def assign_id_list[E: Enum](
    assignment: str | list[str],
    id_enum: type[E],
    min_length: int = 0,
    *,
    unique: bool = False,
) -> list[E]:
    """
    Check whether an assigned ID satisfies an attribute's requirements.

    Only applicable to attributes requiring a list of values. A deck may give a
    single ID where the attribute takes a list, so a bare ID is accepted and
    wrapped in a list.

    Parameters
    ----------
    assignment
        ID or list of IDs passed to the setter.
    id_enum
        Enum class the assigned name is looked up in.
    min_length
        Fewest members the list may contain.
    unique
        Whether no member may be named twice.

    Returns
    -------
    list[Enum]
        The members the assigned IDs name.
    """
    members = [assign_id(value, id_enum) for value in as_list(assignment)]
    _check_list_length(members, min_length)

    if unique:
        _check_list_is_unique(members)

    return members


def assign_fraction_list(assignment: list[float]) -> tuple[list[float], bool]:
    """
    Check a list of fractions assigned to an attribute and rescale it to sum to 1.

    Only applicable to attributes requiring a list of values summing to 1.
    Entries are floated first, so a list written as integers is rescaled the
    same way as its float spelling; an entry, or a total, that does
    not float to a finite value is rejected. The entries must sum to
    more than 0 once rounded to ``ROUND_OFF`` decimals, so an all-zero list
    and an empty list are rejected: a zero total cannot be rescaled to 1. Any
    other total than 1 is rescaled proportionally.

    Parameters
    ----------
    assignment
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
    floated = _floated_fractions(assignment)
    total = round(sum(floated), ROUND_OFF)

    if total <= 0.0:
        raise ValueError("requires entries summing to more than 0")

    rescaled = [fraction / total for fraction in floated]
    was_rescaled = abs(total - 1.0) > 0.01

    return assign_list(rescaled, lower=0.0, upper=1.0), was_rescaled


def check_tables_are_finite(
    node: Node, attribute: str, entries: Sequence[CurveTableInput | Forecast]
) -> None:
    """
    Reject a table among an attribute's entries that holds a non-finite value.

    The Curves and Forecasts are read as tables, never evaluated, so no bound
    they are assigned under ever checks their values; the table itself rejects
    a non-finite x-value. A node runs this from check_consistency, as the tables
    are built only after its setters have run.

    Parameters
    ----------
    node
        Node holding the attribute, named in the error.
    attribute
        Name of the attribute, or of the tables' role on the node, named in the
        error.
    entries
        The attribute's entries; a number among them is skipped.

    Raises
    ------
    ValueError
        If a table holds an INF, -INF or NaN value.
    """
    for entry in entries:
        if isinstance(entry, Scalar):
            continue

        if not np.all(np.isfinite(entry.y)):
            raise ValueError(f"{node}: {attribute} ({entry}) must hold finite values.")


def check_lengths_match(
    node: Node,
    attribute: str,
    entries: Sized,
    other_attribute: str,
    other_entries: Sized,
) -> None:
    """
    Reject two attributes whose entries pair up one to one but differ in number.

    Parameters
    ----------
    node
        Node holding the attributes, named in the error.
    attribute
        DSL name of the attribute, named in the error.
    entries
        The attribute's entries.
    other_attribute
        DSL name of the attribute paired with it, named in the error.
    other_entries
        The paired attribute's entries.

    Raises
    ------
    ValueError
        If the two attributes hold a different number of entries.
    """
    if len(entries) != len(other_entries):
        raise ValueError(
            f"{node}: The length of {attribute} ({len(entries)}) and "
            f"{other_attribute} ({len(other_entries)}) must correspond."
        )


def check_forecast_is_cumulative(node: Node, attribute: str, entry: Forecast) -> None:
    """
    Reject a cumulative Forecast that decreases, and warn where it extrapolates.

    A cumulative count read as a table never falls, and LINEAR extrapolation
    lets it keep growing past its last date.

    Parameters
    ----------
    node
        Node holding the Forecast, named in the error.
    attribute
        Name of the attribute, or of the Forecast's role on the node such as
        Orderbook, named in the error.
    entry
        The attribute's Forecast of the cumulative count.

    Raises
    ------
    ValueError
        If the Forecast's values decrease anywhere.
    """
    if not is_nondecreasing(entry.y):
        raise ValueError(
            f"{node}: {attribute} ({entry}) is not non-strictly increasing."
        )

    if entry.extrapolate == ExtrapolateID.LINEAR:
        logger.warning(
            "%s: %s (%s) allows extrapolation and may therefore continue past the"
            " last date.",
            node,
            attribute,
            entry,
        )


def write_matching_keys[K: str | Enum, V](
    key: K | str,
    value: V,
    assignment_dict: _CommandDict[K, V],
    *,
    allow_empty: bool = False,
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
    allow_empty
        Whether a wildcard pattern that matches nothing is not an error.
    """
    try:
        matches = retrieve_keys(key, assignment_dict)
    except KeyError:
        if allow_empty and isinstance(key, str) and name_contains_wildcards(key):
            # wildcards in a shared include are written against whatever the
            # deck defines, so a pattern that matches nothing is not an error
            return

        raise ValueError(_missing_names(key_name(key))) from None

    # every matched key holds the same object: a Scalar answers a getter and
    # carries no per-key state, and a node or an expression was always shared
    for match in matches:
        assignment_dict[match] = value


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
        names = ", ".join(key_name(key_part) for key_part in key)
        raise ValueError(_missing_names(names))

    columns = zip(*assignment_dict, strict=True)
    try:
        matches = [
            retrieve_keys(key_part, unique_list(existing_keys))
            for key_part, existing_keys in zip(key, columns, strict=True)
        ]
    except KeyError as e:
        raise ValueError(_missing_names(e.args[0])) from None

    # every matched key holds the same object: a Scalar answers a getter and
    # carries no per-key state, and a node or an expression was always shared
    firsts, seconds = matches
    for first in firsts:
        for second in seconds:
            assignment_dict[(first, second)] = value


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
    allowed = []
    if allow_scalar:
        allowed.append("scalars")
    if type_ is not None:
        allowed.append(_node_types_phrase(type_))

    return _only_allows(" and ".join(allowed), assignment)


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


def _missing_names(names: str) -> str:
    """Spell the error for a command naming keys its dictionary does not hold."""
    return f"attempts to reference non-existing name(s) '{names}'"


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


def _resolve_bounds(
    lower: float,
    upper: float,
    inclusive_lower: bool,
    inclusive_upper: bool,
    *,
    allow_infinite: bool,
) -> Bounds:
    """
    Resolve a setter's bounds into the Bounds its value is held to.

    An exclusive bound at infinity rejects exactly infinity: a scalar when it
    is assigned, a calculator or an expression each time it is evaluated.
    Refusing infinity therefore only takes making each infinite bound
    exclusive.

    Parameters
    ----------
    lower
        Lower bound.
    upper
        Upper bound.
    inclusive_lower
        Whether the setter asked for an inclusive lower bound.
    inclusive_upper
        Whether the setter asked for an inclusive upper bound.
    allow_infinite
        Whether the setter accepts INF and -INF within its bounds.

    Returns
    -------
    Bounds
        The bounds the value is held to.
    """
    if not allow_infinite:
        inclusive_lower = inclusive_lower and math.isfinite(lower)
        inclusive_upper = inclusive_upper and math.isfinite(upper)

    return Bounds(lower, upper, inclusive_lower, inclusive_upper)


def _check_scalar(assignment: float | Scalar, bounds: Bounds) -> None:
    """
    Validate that a scalar value satisfies the given bounds.

    Parameters
    ----------
    assignment
        Value being assigned, rejected unless it is a float or a Scalar.
    bounds
        The bounds the value is held to.

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

    bounds.check(value)


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
    length = len(assignment)
    if length < min_length:
        entries = "entry" if min_length == 1 else "entries"
        raise ValueError(f"requires at least {min_length} {entries}, but got {length}")


def _check_list_is_unique(entries: Collection[Hashable]) -> None:
    """
    Validate that no entry occurs twice in a list.

    Parameters
    ----------
    entries
        The entries checked, compared by equality.
    """
    if not is_unique(entries):
        raise ValueError("requires all entries in the list to be unique")


def _floated_fractions(assignment: list[float]) -> list[float]:
    """
    Float the entries of a fraction list, rejecting a negative or non-finite one.

    Every entry must be a plain number that floats to a finite value, and the
    float total must be finite too, so the rescale in assign_fraction_list
    can neither overflow nor turn an entry into NaN.

    Parameters
    ----------
    assignment
        The value passed to the setter.

    Returns
    -------
    list[float]
        The entries, floated.
    """
    if not isinstance(assignment, list):
        raise ValueError("only allows assignment of lists")

    # a non-number would reach the comparison below as a TypeError carrying no
    # deck line for the parser to report, and an int too large for a float
    # would escape the floating as an OverflowError, which the parser cannot
    # locate either; int, and the bool that subclasses it, pass
    floated = []
    for fraction in assignment:
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

    return floated
