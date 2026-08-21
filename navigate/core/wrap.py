# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core.scalar import Scalar


def as_scalar(value):
    """
    Wrap a value in a Scalar class if it is a float, otherwise return the NodeReference or Node as is.

    The wrapping is necessary as Scalar provides a getter which takes two arguments, similar to all calculator nodes.
    This is convenient when an attribute can be defined as either a float or a calculator node.

    Parameters
    ----------
    value : float | NodeReference | Node
        Value to wrap in a Scalar if it is a float.

    Returns
    -------
    Scalar | NodeReference | Node
        Wrapped value.
    """

    if isinstance(value, float):
        return Scalar(value)
    else:
        return value


def as_scalar_list(values):
    """
    Wraps all values in a list as Scalars if they are floats. See 'as_scalar' for further documentation.

    Parameters
    ----------
    values : Generator[float | NodeReference | Node]
        List of values to wrap in a Scalar if they are floats.

    Returns
    -------
    list[Scalar | NodeReference | Node]
        List of wrapped values.
    """

    return [as_scalar(value) for value in as_list(values)]


def as_list(value):
    """
    Wrap a value in a list if it is not already a list.

    This is a convenient method when an attribute requires a list, but the list has no defined length.
    It allows the user to pass the assignment without the '[' and ']' around the value.

    Parameters
    ----------
    value : list | float | NodeReference | Node

    Returns
    -------
    list
        A list containing the passed value or simply the value itself if already a list.
    """

    if isinstance(value, tuple):
        return list(value)

    else:
        return [value] if not isinstance(value, list) else value
