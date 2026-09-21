# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import numpy as np

from navigate.core.expression import Expression
from navigate.core.node import Node
from navigate.core.node_type import is_calculator
from navigate.core.scalar import Scalar
from navigate.core.table_data import TableData
from navigate.core.wildcard import WildcardNodeReference
from navigate.core.wrap import as_scalar
from navigate.util import (
    ROUND_OFF,
    TOLERANCE,
    key_name,
    list_is_unique,
    name_contains_wildcards,
    retrieve_keys,
    unique_list,
)

_BOOL_ID = {"FALSE": False, "TRUE": True}

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
    assignment,
    lower=-np.inf,
    upper=np.inf,
    inclusive_lower=True,
    inclusive_upper=True,
):
    """

    Parameters
    ----------
    assignment : float
        The value passed to the setter.
    lower : float
        Lower bound.
    upper : float
        Upper bound.
    inclusive_lower : bool, default=True
        Lower bound is inclusive.
    inclusive_upper : bool, default=True
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


def assign_value(
    assignment,
    scalar=True,
    date=False,
    type_=None,
    lower=-np.inf,
    upper=np.inf,
    *,
    inclusive_lower=True,
    inclusive_upper=True,
):
    """
    Check whether the value (float or calculator) assigned to an attribute satisfy the requirements of that attribute.
    Only applicable to attributes requiring a single value, not lists.

    The method assumes that if scalar=False, type_ must not be None (or an empty list). No check is made for this
    as it is an implementation requirement, not a user input issue.

    If the requirements are not satisfied a ValueError is raised. Note that this error is only a partial message
    designed to be caught at a higher level.

    Parameters
    ----------
    assignment : Node | WildcardNodeReference | Scalar | float | Expression
        The value passed to the setter.
    scalar : bool
        Whether the setter accepts scalars.
    date : bool
        Whether the setter accepts dates.
    type_ : str | tuple[str]
        Type(s) of Node that attribute allows.
    lower : float
        Lower bound.
    upper : float
        Upper bound.
    inclusive_lower : bool, default=True
        Lower bound is inclusive.
    inclusive_upper : bool, default=True
        Upper bound is inclusive.

    Returns
    -------
    Node | WildcardNodeReference | Scalar | float | Expression:
        Returns the passed assignment (to allow error checking while assigning)
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


def assign_list(
    assignment,
    length=(),
    unique=False,
    scalar=True,
    date=False,
    type_=None,
    lower=-np.inf,
    upper=np.inf,
    *,
    inclusive_lower=True,
    inclusive_upper=True,
):
    """
    Check whether the value (float or calculator) assigned to an attribute satisfy the requirements of that attribute.
    Only applicable to attributes requiring a list of values.

    If the requirements are not satisfied a ValueError is raised. Note that this error is only a partial message
    designed to be caught at a higher level.

    Parameters
    ----------
    assignment : list[Node | WildcardNodeReference | Scalar | float]
        List of values passed to the setter.
    length : int | tuple[int, int]
        Exact length the list should have or lower and upper bound. If empty, no check is made.
    unique : bool
        Whether all entries in the list must be unique.
    scalar : bool
        Whether the setter accepts scalars.
    date : bool
        Whether the setter accepts dates.
    type_ : str | tuple[str]
        Type(s) of Node that attribute allows.
    lower : float
        Lower bound.
    upper : float
        Upper bound.
    inclusive_lower: bool = True
        Lower bound is inclusive.
    inclusive_upper: bool = True
        Upper bound is inclusive.

    Returns
    -------
    List[Node | WildcardNodeReference | Scalar | float] :
        Returns the passed assignment (to allow error checking while assigning)
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


def assign_boolean(assignment):
    """
    Check whether the value assigned to a boolean attribute is a boolean keyword.

    If the requirements are not satisfied a ValueError is raised. Note that this error is only a partial message
    designed to be caught at a higher level.

    Parameters
    ----------
    assignment : str
        Value passed to the setter.

    Returns
    -------
    bool
        Value of the keyword.
    """
    try:
        return _BOOL_ID[assignment]
    except KeyError:
        raise ValueError(
            f"only allows assignment of TRUE or FALSE, but got {assignment}"
        )


def assign_id(assignment, id_enum):
    """
    Check whether the ID assigned to an attribute satisfy the requirements of that attribute.

    If the requirements are not satisfied a ValueError is raised. Note that this error is only a partial message
    designed to be caught at a higher level.

    Parameters
    ----------
    assignment : str
        Value passed to the setter.
    id_enum : Enum
        Enumerator.

    Returns
    -------
    Enum
        Returns the passed assignment (to allow error checking while assigning).
    """
    try:
        return id_enum[assignment]
    except KeyError:
        if name_contains_wildcards(assignment):
            raise ValueError(
                f"does not accept ID '{assignment}' — wildcards are not supported "
                "for this command"
            )
        raise ValueError(f"does not accept ID '{assignment}'")


def expand_id_wildcard(pattern: str, id_enum) -> list:
    """
    Expand a wildcard pattern against an enum's member names.

    Delegates to :func:`retrieve_keys` which handles Enum-keyed collections.

    Parameters
    ----------
    pattern
        Glob-style pattern (e.g. ``"M*"``), matched against each member's ``.name``.
    id_enum
        Enum class to match against.

    Returns
    -------
    List of matching enum members.
    """
    try:
        return retrieve_keys(pattern, id_enum, key_fn=lambda m: m.name)
    except KeyError:
        raise ValueError(
            f"wildcard '{pattern}' did not match any member of {id_enum.__name__}"
        )


def assign_id_list(assignment, id_enum, length=()):
    """
    Check whether the ID assigned to an attribute satisfy the requirements of that attribute.
    Only applicable to attributes requiring a list of values. Supports wildcard patterns
    which are expanded before the length check.

    If the requirements are not satisfied a ValueError is raised. Note that this error is only a partial message
    designed to be caught at a higher level.

    Parameters
    ----------
    assignment : list[str]
        List of values passed to the setter.
    id_enum : Enum
        Enumerator.
    length : int | tuple[int, int]
        Exact length the list should have or lower and upper bound. If empty, no check is made.

    Returns
    -------
    List[Enum] :
        Returns the passed assignment (to allow error checking while assigning).
    """
    expanded = []
    for value in assignment:
        if name_contains_wildcards(value):
            expanded.extend(expand_id_wildcard(value, id_enum))
        else:
            expanded.append(assign_id(value, id_enum))

    _check_list_length(expanded, length)
    return expanded


def assign_fraction_list(fractions):
    """
    Check whether the value (float or calculator) assigned to an attribute satisfy the requirements of that attribute.
    Only applicable to attributes requiring a list of values.
    Additionally, requires that the sum of values in the list sum to 1.

    If the requirements are not satisfied a ValueError is raised. Note that this error is only a partial message
    designed to be caught at a higher level.

    Parameters
    ----------
    fractions

    Returns
    -------
    list[float]
        List of floats that at maximum sum to 1.
    """
    _check_fraction_list(fractions)

    normalized = False
    total = round(sum(fractions), ROUND_OFF)

    if fractions and (total != 1.0) and (total > 0.0):
        fractions[:] = [fraction / total for fraction in fractions]
        normalized = abs(total - 1) > 0.01

    return assign_list(fractions, lower=0.0, upper=1.0), normalized


def command_assignment_to_dict(
    key,
    assignment,
    assignment_dict,
    scalar=True,
    date=False,
    type_=None,
    lower=-np.inf,
    upper=np.inf,
    *,
    inclusive_lower=True,
    inclusive_upper=True,
):
    """

    Parameters
    ----------
    key : str | Enum
        Name of node, possibly including wildcards.
    assignment : Any
        Assignment to dict.
    assignment_dict : dict
        The dictionary being assigned to.
    scalar : bool
        Whether the setter accepts scalars.
    date : bool
        Whether the setter accepts dates.
    type_ : str or tuple[str]
        Type(s) of Node that attribute allows.
    lower : float
        Lower bound.
    upper : float
        Upper bound.
    inclusive_lower: bool = True
        Lower bound is inclusive.
    inclusive_upper: bool = True
        Upper bound is inclusive.
    """
    for key_ in retrieve_keys(key, assignment_dict):
        assignment_dict[key_] = assign_value(
            as_scalar(assignment),
            scalar,
            date,
            type_,
            lower,
            upper,
            inclusive_lower=inclusive_lower,
            inclusive_upper=inclusive_upper,
        )


def command_assignment_to_tuple_dict(
    key,
    assignment,
    assignment_dict,
    scalar=True,
    date=False,
    type_=None,
    lower=-np.inf,
    upper=np.inf,
    *,
    inclusive_lower=True,
    inclusive_upper=True,
    symmetric=False,
):
    """

    Parameters
    ----------
    key : tuple[str, str] | tuple[Enum, Enum]
        Tuple of node names, possibly including wildcards.
    assignment : Any
        Assignment to dict.
    assignment_dict : dict
        The dictionary being assigned to.
    scalar : bool
        Whether the setter accepts scalars.
    date : bool
        Whether the setter accepts dates.
    type_ : str or tuple[str]
        Type(s) of Node that attribute allows.
    lower : float
        Lower bound.
    upper : float
        Upper bound.
    inclusive_lower: bool = True
        Lower bound is inclusive.
    inclusive_upper: bool = True
        Upper bound is inclusive.
    symmetric : bool
        Whether the dictionary is symmetric, i.e. (key1, key2) = (key2, key1).
    """
    keys = [
        retrieve_keys(k, unique_list(keys))
        for k, keys in zip(key, zip(*assignment_dict.keys()))
    ]

    if not keys:
        raise KeyError(", ".join(key_name(k) for k in key))

    keys1, keys2 = keys

    for key1 in keys1:
        for key2 in keys2:
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
            assignment_dict[(key1, key2)] = value

            if symmetric:
                assignment_dict[(key2, key1)] = value


def command_assignment_to_boolean_dict(
    key, assignment, assignment_dict, allow_empty=False
):
    """

    Parameters
    ----------
    key : str
        Key to assignment_dict. May include wildcards.
    assignment : str
        Boolean value TRUE or FALSE.
    assignment_dict : dict[str, bool]
        Dict to assign the boolean value to.
    allow_empty : bool
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


def _failed_value_message(assignment, scalar, date, type_):
    """
    Build the error message for a value an attribute does not accept.

    Parameters
    ----------
    assignment : Any
        The value passed to the setter.
    scalar : bool
        Whether the setter accepts scalars.
    date : bool
        Whether the setter accepts dates.
    type_ : str or tuple[str]
        Type(s) of Node that attribute allows.

    Returns
    -------
    str :
        Error message of a failed error check.
    """
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

    # a setter that accepts no kind at all is an implementation error rather
    # than a deck error, so an empty 'allowed' is not handled (see assign_value)
    if len(allowed) == 1:
        joined = allowed[0]
    else:
        joined = ", ".join(allowed[:-1]) + " and " + allowed[-1]

    return f"only allows assignment of {joined}, but got {_value_kind(assignment)}"


def _value_kind(assignment):
    """
    Name the kind of a value, or echo the value when it has no listed kind.

    Parameters
    ----------
    assignment : Any
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
    assignment,
    lower=-np.inf,
    upper=np.inf,
    *,
    inclusive_lower=True,
    inclusive_upper=True,
):
    """
    Validate that a scalar value satisfies the given bounds.

    Parameters
    ----------
    assignment : Scalar or float
        Float being assigned.
    lower : float
        Lower bound.
    upper : float
        Upper bound.
    inclusive_lower : bool, default=True
        If True, allow value == lower. If False, require value > lower.
    inclusive_upper : bool, default=True
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


def _check_list_length(assignment, length):

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


def _check_list_is_unique(assignment):
    names = [
        entry.name
        for entry in assignment
        if isinstance(entry, (Node, WildcardNodeReference))
    ]
    if not list_is_unique(names):
        raise ValueError("requires all entries in the list to be unique")


def _check_fraction_list(fractions):
    if not isinstance(fractions, list):
        raise ValueError("only allows assignment of lists")

    if any(fraction < 0.0 for fraction in fractions):
        raise ValueError("does not allow negative values")
