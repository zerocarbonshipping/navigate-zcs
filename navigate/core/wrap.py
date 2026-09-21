# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING, overload

from navigate.core.scalar import Scalar

if TYPE_CHECKING:
    import numpy as np

    from navigate.core.expression import Expression
    from navigate.core.node import Node
    from navigate.core.wildcard import WildcardNodeReference

# these two aliases are the contract for typed callers, not a claim about what
# reaches the boundary at runtime: the parser is untyped, so it hands every
# deck value in as 'Any' and a deck can name any shape the grammar accepts -
# a bare string, a list, a TableData. That is why the helpers in 'assign' keep
# runtime reject arms that a reader of the annotations alone would take for
# dead code, and why their validators take 'object' rather than a narrow type.

# a value that already answers a getter, and a date, pass the wrappers
# untouched; only a bare float needs wrapping
type WrappedAssignment = (
    Scalar | Node | WildcardNodeReference | Expression | np.datetime64
)

# everything a setter may be handed for a single-valued attribute
type Assignment = float | WrappedAssignment


# 'int' and 'bool' are not instances of 'float', so they pass through
# unwrapped; the numeric tower would otherwise type them as Scalar
@overload
def as_scalar(value: bool) -> bool: ...


@overload
def as_scalar(value: int) -> int: ...


@overload
def as_scalar(value: float) -> Scalar: ...


@overload
def as_scalar[T: WrappedAssignment](value: T) -> T: ...


def as_scalar(value: Assignment) -> Assignment:
    """
    Wrap a value in a Scalar class if it is a float, otherwise return the value as is.

    The wrapping is necessary as Scalar provides a getter which takes two
    arguments, similar to all calculator nodes. This is convenient when an
    attribute can be defined as either a float or a calculator node.

    Parameters
    ----------
    value
        Value to wrap in a Scalar if it is a float.

    Returns
    -------
    Assignment
        Wrapped value.
    """
    if isinstance(value, float):
        return Scalar(value)
    else:
        return value


def as_scalar_list(
    values: Assignment | list[Assignment] | tuple[Assignment, ...],
) -> list[WrappedAssignment]:
    """
    Wrap all values in a list as Scalars if they are floats.

    See 'as_scalar' for further documentation.

    Parameters
    ----------
    values
        Values to wrap in a Scalar if they are floats.

    Returns
    -------
    list[WrappedAssignment]
        List of wrapped values.
    """
    assignments: list[Assignment] = as_list(values)

    return [as_scalar(value) for value in assignments]


def as_list[T](value: T | list[T] | tuple[T, ...]) -> list[T]:
    """
    Wrap a value in a list if it is not already a list.

    This is a convenient method when an attribute requires a list, but the
    list has no defined length. It allows the user to pass the assignment
    without the '[' and ']' around the value.

    Parameters
    ----------
    value
        Value that may or may not already be a list.

    Returns
    -------
    list
        A list containing the passed value or simply the value itself if already a list.
    """
    if isinstance(value, tuple):
        return list(value)

    else:
        return [value] if not isinstance(value, list) else value
