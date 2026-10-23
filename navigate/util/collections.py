# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""List and dict helpers, including arithmetic and slicing of results."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Collection, Hashable, Iterable, Mapping, Sequence

    from navigate.util.types_ import FloatArray, FloatLike, Index


def unique_list[T: Hashable](items: Iterable[T]) -> list[T]:
    """
    Create an order preserved list of unique objects in items.

    Parameters
    ----------
    items
        Objects to deduplicate.

    Returns
    -------
    list[T]
        Order preserved list of unique objects in items.
    """
    return list(dict.fromkeys(items))


def list_intersection[T](list1: list[T], list2: list[T]) -> list[T]:
    """
    Create an order preserved list of the intersection between two lists.

    Parameters
    ----------
    list1
        List of objects.
    list2
        List of objects.

    Returns
    -------
    list[T]
        Order preserved list of the intersection.
    """
    return [item for item in list1 if item in list2]


def list_is_unique(values: Collection[Hashable]) -> bool:
    """
    Test whether all values are distinct.

    Parameters
    ----------
    values
        Values to test.

    Returns
    -------
    bool
        Whether no value occurs more than once.
    """
    return len(values) == len(set(values))


def define_index_map[T: Hashable](objects: Sequence[T]) -> dict[T, list[int]]:
    """
    Map each unique object to the indexes at which it occurs.

    Parameters
    ----------
    objects
        Objects to index, possibly with repetitions.

    Returns
    -------
    dict[T, list[int]]
        Indexes of each unique object, in first-occurrence order.
    """
    index_map: dict[T, list[int]] = {}

    for index, object_ in enumerate(objects):
        index_map.setdefault(object_, []).append(index)

    return index_map


def add_dicts[K](*dicts: dict[K, FloatLike]) -> dict[K, FloatLike]:
    """
    Merge dicts, adding the values of keys they share.

    Parameters
    ----------
    dicts
        Dicts to merge.

    Returns
    -------
    dict[K, FloatLike]
        A single merged dict with the sum of overlapping keys; the values
        never alias the inputs.
    """
    total: dict[K, FloatLike] = {}

    for dict_ in dicts:
        for key, value in dict_.items():
            total[key] = total.get(key, 0.0) + value

    return total


def is_single_dict[K](dict_: Mapping[K, object]) -> bool:
    """
    Check whether a dict is a single dict (keyed by non-tuple keys).

    Parameters
    ----------
    dict_
        Dict whose key kind is tested.

    Returns
    -------
    bool
        Whether the first key is a non-tuple; False for an empty dict.
    """
    if not dict_:
        return False

    first_key = next(iter(dict_))
    return not isinstance(first_key, tuple)


def is_tuple_dict[K](dict_: Mapping[K, object]) -> bool:
    """
    Check whether a dict is a tuple dict (keyed by two-element tuples).

    Parameters
    ----------
    dict_
        Dict whose key kind is tested.

    Returns
    -------
    bool
        Whether the first key is a two-element tuple; False for an empty dict.
    """
    if not dict_:
        return False

    first_key = next(iter(dict_))
    return isinstance(first_key, tuple) and len(first_key) == 2


def sum_dict_results[K](result: dict[K, FloatArray]) -> FloatArray:
    """
    Sum a dict's array values element-wise, adding the arrays across its keys.

    Parameters
    ----------
    result
        Result given as a non-empty dict of arrays.

    Returns
    -------
    FloatArray
        Sum of the values.
    """
    summed: FloatArray = np.add.reduce(list(result.values()))
    return summed


def sum_values[K](dict_: Mapping[K, FloatArray], shape: tuple[int, ...]) -> FloatArray:
    """
    Sum a dict's arrays element-wise; an empty dict sums to zeros.

    Parameters
    ----------
    dict_
        Arrays to sum, all of the given shape.
    shape
        Shape of the arrays.

    Returns
    -------
    FloatArray
        Sum of the arrays.
    """
    return sum(dict_.values(), start=np.zeros(shape))


def sum_per_key[K](
    dict_: Mapping[K, FloatArray | Sequence[FloatArray]],
) -> dict[K, float]:
    """
    Sum the values held under each key of a dict into one number per key.

    Parameters
    ----------
    dict_
        Values to sum, by key: an array or a sequence of arrays per key.

    Returns
    -------
    dict[K, float]
        Total of the values under each key.
    """
    return {key: float(np.sum(values)) for key, values in dict_.items()}


def sum_by_first_key[K1: Hashable, K2: Hashable](
    result: dict[tuple[K1, K2], FloatArray],
) -> dict[K1, FloatArray]:
    """
    Sum a tuple dict's values over the second key, keyed by the first.

    Parameters
    ----------
    result
        Result given as a tuple dict.

    Returns
    -------
    dict[K1, FloatArray]
        Dict keyed by the first tuple element, summed over the second.
    """
    groups: dict[K1, dict[K2, FloatArray]] = {}

    for (first, second), value in result.items():
        groups.setdefault(first, {})[second] = value

    return {key: sum_dict_results(group) for key, group in groups.items()}


def sum_by_second_key[K1: Hashable, K2: Hashable](
    result: dict[tuple[K1, K2], FloatArray],
) -> dict[K2, FloatArray]:
    """
    Sum a tuple dict's values over the first key, keyed by the second.

    Parameters
    ----------
    result
        Result given as a tuple dict.

    Returns
    -------
    dict[K2, FloatArray]
        Dict keyed by the second tuple element, summed over the first.
    """
    groups: dict[K2, dict[K1, FloatArray]] = {}

    for (first, second), value in result.items():
        groups.setdefault(second, {})[first] = value

    return {key: sum_dict_results(group) for key, group in groups.items()}


def slice_list(
    result: list[FloatArray],
    idx: Index,
) -> list[FloatLike]:
    """
    Slice each array in a list.

    Parameters
    ----------
    result
        Result to be sliced.
    idx
        Time-step index(es) or slice.

    Returns
    -------
    list[FloatLike]
        Sliced result.
    """
    return [value[idx] for value in result]


def slice_dict[K](
    result: dict[K, FloatArray],
    idx: Index,
) -> dict[K, FloatLike]:
    """
    Slice each value in a dict.

    Parameters
    ----------
    result
        Result to be sliced.
    idx
        Time-step index(es) or slice.

    Returns
    -------
    dict[K, FloatLike]
        Sliced result.
    """
    return {key: value[idx] for key, value in result.items()}


def slice_dict_list[K](
    result: dict[K, list[FloatArray]],
    idx: Index,
) -> dict[K, list[FloatLike]]:
    """
    Slice each array in each list of a dict of lists.

    Parameters
    ----------
    result
        Result to be sliced.
    idx
        Time-step index(es) or slice.

    Returns
    -------
    dict[K, list[FloatLike]]
        Sliced result.
    """
    return {key: slice_list(value, idx) for key, value in result.items()}
