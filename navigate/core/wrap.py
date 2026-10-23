# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Wrapping of deck values for storage, and evaluation of calculators into numbers."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np

from navigate.core.scalar import Scalar

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from navigate.core.expression import Expression
    from navigate.core.types_ import Calculator, ForecastInput
    from navigate.util.types_ import FloatArray


@overload
def as_scalar(value: float) -> Scalar: ...
@overload
def as_scalar[T: Calculator | Expression](value: T) -> T: ...
def as_scalar(
    value: float | Calculator | Expression,
) -> Scalar | Calculator | Expression:
    """
    Wrap a float deck value in a Scalar, and return anything else as is.

    The wrapping is necessary as Scalar provides a getter which takes two
    arguments, similar to all calculator nodes. The parser hands deck values
    in untyped, so anything that is not a float passes through unchanged for
    the validators in 'assign' to accept or reject.

    Parameters
    ----------
    value
        Value to wrap in a Scalar if it is a float.

    Returns
    -------
    Scalar | Calculator | Expression
        The float wrapped in a Scalar, or the calculator or expression as is.
    """
    if isinstance(value, float):
        return Scalar(value)

    return value


def as_list[T](value: T | list[T]) -> list[T]:
    """
    Wrap a bare deck value in a list, and return a list as is.

    A deck may give a single value where an attribute takes a list, e.g.
    'MainFuelTypes = OIL' instead of 'MainFuelTypes = [OIL]'; a deck list
    always arrives as a Python list.

    Parameters
    ----------
    value
        A deck value, bare or a list.

    Returns
    -------
    list[T]
        The value in a list, or the list as is.
    """
    if isinstance(value, list):
        return value

    return [value]


def to_numpy(calculators: Iterable[ForecastInput]) -> FloatArray:
    """
    Evaluate a collection of calculators into a numpy array.

    Parameters
    ----------
    calculators
        Calculator nodes to evaluate.

    Returns
    -------
    FloatArray
        Evaluated values.
    """
    return np.array([calculator.get(None, None) for calculator in calculators])


def to_floats[K](calculators: Mapping[K, ForecastInput]) -> dict[K, float]:
    """
    Evaluate a mapping of calculators into floats, keeping its keys.

    Parameters
    ----------
    calculators
        Calculator nodes to evaluate, by key.

    Returns
    -------
    dict[K, float]
        Evaluated values, by key.
    """
    return {key: calculator.get(None, None) for key, calculator in calculators.items()}
