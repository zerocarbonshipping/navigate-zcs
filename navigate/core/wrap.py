# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Wrapping of a deck value so a plain number and a calculator node read alike."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

from navigate.core.scalar import Scalar

if TYPE_CHECKING:
    import numpy as np

    from navigate.core.expression import Expression
    from navigate.core.node import Node

# these two aliases are the contract for typed callers, not a claim about what
# reaches the boundary at runtime: the parser is untyped, so it hands every
# deck value in as 'Any' and a deck can name any shape the grammar accepts -
# a bare string, a list, a TableData. That is why the helpers in 'assign' keep
# runtime reject arms that a reader of the annotations alone would take for
# dead code, and why their validators take 'object' rather than a narrow type.

# a value that already answers a getter, and a date, pass the wrappers
# untouched; only a bare float needs wrapping
type WrappedAssignment = Scalar | Node | Expression | np.datetime64

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
    arguments, similar to all calculator nodes.

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
        wrapped: Assignment = Scalar(value)
    else:
        wrapped = value

    return wrapped


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
    list has no defined length.

    Parameters
    ----------
    value
        Value that may or may not already be a list.

    Returns
    -------
    list[T]
        A list containing the passed value or simply the value itself if already a list.
    """
    if isinstance(value, tuple):
        value_list = list(value)
    elif isinstance(value, list):
        value_list = value
    else:
        value_list = [value]

    return value_list
