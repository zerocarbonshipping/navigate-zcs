# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Wrapping of a deck value so a plain number and a calculator node read alike."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np

from navigate.core.scalar import Scalar

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.core.expression import Expression
    from navigate.core.node import Node
    from navigate.core.nodes.input_kinds import ForecastInput
    from navigate.util.types_ import FloatArray

# these two aliases are the contract for typed callers, not a claim about what
# reaches the boundary at runtime: the parser is untyped, so it hands every
# deck value in as 'Any' and a deck can name any shape the grammar accepts -
# a bare string, a list, a TableData. That is why the validators in 'assign'
# keep runtime reject arms for values their typed callers never pass.

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
        return Scalar(value)

    return value


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
        return list(value)

    if isinstance(value, list):
        return value

    return [value]


def to_numpy(scalars: Iterable[float | ForecastInput]) -> FloatArray:
    """
    Evaluate a collection of floats and/or calculators into a numpy array.

    Parameters
    ----------
    scalars
        Floats and/or calculator nodes to evaluate.

    Returns
    -------
    FloatArray
        Evaluated values.
    """
    return np.array(
        [
            scalar if isinstance(scalar, float) else scalar.get(None, None)
            for scalar in scalars
        ]
    )
