# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.expression import Expression
from navigate.core.node_reference import NodeReference
from navigate.core.nodes.node import Node
from navigate.core.scalar import Scalar
from navigate.core.wrap import as_scalar
from navigate.util import ROUND_OFF, TOLERANCE, name_contains_wildcards, retrieve_keys, unique_list

BOOL_ID = {'FALSE': False,
           'TRUE': True}


def assign_integer(assignment, lower=-np.inf, upper=np.inf, inclusive_lower=True, inclusive_upper=True,):
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

    _check_scalar(assignment, lower=lower, upper=upper, inclusive_lower=inclusive_lower, inclusive_upper=inclusive_upper)

    value = int(assignment)

    if abs(value - assignment) >= TOLERANCE:
        raise ValueError("only allows assignment of integers, but got {}".format(assignment))

    return value


def assign_value(assignment, scalar=True, date=False, type_=None,
                 lower=-np.inf, upper=np.inf, *,
                 inclusive_lower=True, inclusive_upper=True):
    """
    Check whether the value (float or calculator) assigned to an attribute satisfy the requirements of that attribute.
    Only applicable to attributes requiring a single value, not lists.

    The method assumes that if scalar=False, type_ must not be None (or an empty list). No check is made for this
    as it is an implementation requirement, not a user input issue.

    If the requirements are not satisfied a ValueError is raised. Note that this error is only a partial message
    designed to be caught at a higher level.

    Parameters
    ----------
    assignment : Node | NodeReference | Scalar | float | Expression
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
    NodeReference | Scalar | float | Expression:
        Returns the passed assignment (to allow error checking while assigning)
    """

    if isinstance(assignment, (list, tuple)):
        raise ValueError("{}, but got list".format(_failed_value_message(scalar, date, type_)))

    is_float = isinstance(assignment, (float, Scalar))
    is_date = isinstance(assignment, np.datetime64)
    is_expression = isinstance(assignment, Expression)
    is_node = isinstance(assignment, (Node, NodeReference))
    type_is_list = isinstance(type_, (list, tuple))

    if is_float:

        if scalar:
            _check_scalar(assignment, lower=lower, upper=upper,
                          inclusive_lower=inclusive_lower, inclusive_upper=inclusive_upper)

        else:
            raise ValueError("{}, but got scalar".format(_failed_value_message(scalar, date, type_)))

    elif is_date:

        if not date:
            raise ValueError("{}, but got date".format(_failed_value_message(scalar, date, type_)))

    elif is_expression:

        assignment.set_allowed_types(type_)

    elif is_node:

        if type_ is None:
            raise ValueError(_failed_value_message(scalar, date, type_))

        if type_is_list:

            if not assignment.get_type() in type_:
                raise ValueError("{}, but got {}".format(_failed_value_message(scalar, date, type_), assignment))

        elif not assignment.is_type(type_):
            raise ValueError("{}, but got {}".format(_failed_value_message(scalar, date, type_), assignment))

    # is a calculator or expression
    if (not is_float) and (not is_date):
        # Assignment.set_inclusive_bounds
        assignment.set_internal_bounds(lower, upper)

    return assignment


def assign_list(assignment, length=(), unique=False, scalar=True, date=False, type_=None,
                lower=-np.inf, upper=np.inf, *, inclusive_lower=True, inclusive_upper=True):
    """
    Check whether the value (float or calculator) assigned to an attribute satisfy the requirements of that attribute.
    Only applicable to attributes requiring a list of values.

    If the requirements are not satisfied a ValueError is raised. Note that this error is only a partial message
    designed to be caught at a higher level.

    Parameters
    ----------
    assignment : list[NodeReference | Scalar | float]
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
    List[NodeReference | Scalar | float] :
        Returns the passed assignment (to allow error checking while assigning)
    """

    _check_list_length(assignment, length)

    if unique:
        _check_list_is_unique(assignment)

    for value in assignment:
        assign_value(value, scalar, date, type_, lower, upper,
                     inclusive_lower=inclusive_lower, inclusive_upper=inclusive_upper)

    return assignment


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
                "does not accept ID '{}' — wildcards are not supported "
                "for this command".format(assignment)
            )
        raise ValueError("does not accept ID '{}'".format(assignment))


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
        raise ValueError("wildcard '{}' did not match any member of {}".format(pattern, id_enum.__name__))


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

    if fractions and (total != 1.) and (total > 0.):
        fractions[:] = [fraction / total for fraction in fractions]
        normalized = abs(total - 1) > 0.01

    return assign_list(fractions, lower=0., upper=1.), normalized


def command_assignment_to_dict(key, assignment, assignment_dict, scalar=True, date=False, type_=None,
                               lower=-np.inf, upper=np.inf, *, inclusive_lower=True, inclusive_upper=True,):
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
        assignment_dict[key_] = assign_value(as_scalar(assignment), scalar, date, type_, lower, upper,
                                             inclusive_lower=inclusive_lower, inclusive_upper=inclusive_upper)


def command_assignment_to_tuple_dict(key, assignment, assignment_dict, scalar=True, date=False, type_=None,
                                     lower=-np.inf, upper=np.inf, inclusive_lower=True, inclusive_upper=True,
                                     symmetric=False):
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

    keys = [retrieve_keys(k, unique_list(keys)) for k, keys in zip(key, zip(*assignment_dict.keys()))]

    if not keys:
        raise KeyError(", ".join(key))

    keys1, keys2 = keys

    for key1 in keys1:

        for key2 in keys2:

            value = assign_value(as_scalar(assignment), scalar, date, type_, lower, upper,
                                 inclusive_lower=inclusive_lower, inclusive_upper=inclusive_upper)
            assignment_dict[(key1, key2)] = value

            if symmetric:
                assignment_dict[(key2, key1)] = value


def command_assignment_to_boolean_dict(key, assignment, assignment_dict, allow_empty=False):
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

    try:
        value = BOOL_ID[assignment]
    except KeyError:
        raise KeyError("'{}' is not a valid boolean value.".format(assignment))

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


def _failed_value_message(scalar, date, type_):
    """
    Build an error message describing which assignment types are allowed.

    Parameters
    ----------
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

    parts = []

    if scalar:
        parts.append('scalars')

    if date:
        parts.append('dates')

    if type_ is not None:
        if isinstance(type_, str):
            parts.append('nodes of type {}'.format(type_))
        else:
            parts.append('nodes of type {} or {}'.format(', '.join(type_[:-1]), type_[-1]))

    if len(parts) <= 1:
        joined = parts[0] if parts else ''
    else:
        joined = ', '.join(parts[:-1]) + ' and ' + parts[-1]

    return "only allows assignment of " + joined


def _check_scalar(assignment, lower=-np.inf, upper=np.inf, *, inclusive_lower=True, inclusive_upper=True):
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
        raise ValueError("requires a scalar, but got {}".format(assignment))

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
                raise ValueError("List must contain more than {} values.".format(lower))

            if (upper is not None) and (len(assignment) > upper):
                raise ValueError("List must contain less than {} values.".format(upper))

        else:

            if len(assignment) != length:
                raise ValueError("List must contain exactly {} values.".format(length))


def _check_list_is_unique(assignment):
    seen = set()
    for entry in assignment:
        if isinstance(entry, NodeReference):
            name = entry.get_name()
            if name in seen:
                raise ValueError("requires all entries in the list to be unique")
            seen.add(name)


def _check_fraction_list(fractions):
    if not isinstance(fractions, list):
        raise ValueError("only allows assignment of lists")

    if any(fraction < 0. for fraction in fractions):
        raise ValueError("does not allow negative values")


def _check_table_holder(assignment, lower=-np.inf, upper=np.inf):
    """
    Check if a Forecast satisfies the required bounds. Raises a ValueError if bounds are not satisfied.

    Parameters
    ----------
    assignment : Forecast, Curve, Surface
        Node with a table being assigned.
    lower : float
        Lower bound.
    upper : float
        Upper bound.
    """

    # TODO: if Curve or Forecast add warning based on extrapolate if LINEAR and no bounds.

    addition = assignment.get_addition()
    multiplier = assignment.get_multiplier()

    bounds = assignment.get_bounds()
    table_limits = assignment.get_table_limits()

    # theoretical limits of the table
    limits = [addition + multiplier * table_limits[0], addition + multiplier * table_limits[1]]

    # adjust for strict bounds
    if (bounds[0] is not None) and (bounds[0] > limits[0]):
        limits[0] = bounds[0]

    if (bounds[1] is not None) and (bounds[1] < limits[1]):
        limits[1] = bounds[1]

    # limits against attribute lower/upper bounds
    if limits[0] < lower:
        raise ValueError('Node reference: {} has a minimum attainable'
                         ' value({}) lower than the attribute minimum({}).'.format(assignment, limits[0], lower))

    if limits[1] > upper:
        raise ValueError('Node reference: {} has a maximum attainable'
                         ' value({}) greater than the attribute maximum({}).'.format(assignment, limits[1], upper))


def _check_bounds(bounds):
    if not isinstance(bounds, (list, tuple)):
        raise ValueError("'Bounds' must be a list.")

    if len(bounds) != 2:
        raise ValueError("'Bounds' must contain exactly two values.")

    # TODO: does this work for np.inf?
    if not all([isinstance(bound, float) for bound in bounds]):
        raise ValueError("'Bounds' must contain scalars only.")

    if bounds[0] >= bounds[1]:
        raise ValueError("'Bounds' minimum must be less than maximum.")
