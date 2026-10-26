# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""List and dict helpers: deduplication, indexing, sums and slicing."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Collection, Hashable, Iterable, Mapping, Sequence

    from navigate.util.types_ import FloatArray, FloatLike, Index


def unique_list[T: Hashable](items: Iterable[T]) -> list[T]:
    """
    Create an order preserved list of the unique items.

    Parameters
    ----------
    items
        Objects to deduplicate.

    Returns
    -------
    list[T]
        Order preserved list of the unique items.
    """
    return list(dict.fromkeys(items))


def list_intersection[T](items: Iterable[T], others: Collection[T]) -> list[T]:
    """
    Create an order preserved list of the items also found among the others.

    Parameters
    ----------
    items
        Objects to keep or drop, in the order kept.
    others
        Objects an item must be among to be kept.

    Returns
    -------
    list[T]
        Order preserved list of the intersection.
    """
    return [item for item in items if item in others]


def is_unique(items: Collection[Hashable]) -> bool:
    """
    Test whether all items are distinct.

    Parameters
    ----------
    items
        Objects to test.

    Returns
    -------
    bool
        Whether no item occurs more than once.
    """
    return len(items) == len(set(items))


def index_map[T: Hashable](items: Iterable[T]) -> dict[T, list[int]]:
    """
    Map each unique item to the indices at which it occurs.

    Parameters
    ----------
    items
        Objects to index, possibly with repetitions.

    Returns
    -------
    dict[T, list[int]]
        Indices of each unique item, in first-occurrence order.
    """
    indices: dict[T, list[int]] = {}

    for index, item in enumerate(items):
        indices.setdefault(item, []).append(index)

    return indices


def is_single_dict[K](dict_: Mapping[K, object]) -> bool:
    """
    Test whether a dict is a single dict, keyed by non-tuple keys.

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
    Test whether a dict is a tuple dict, keyed by two-element tuples.

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


def add_dicts[K](*dicts: Mapping[K, FloatLike]) -> dict[K, FloatLike]:
    """
    Merge dicts, adding the values of keys they share.

    Parameters
    ----------
    dicts
        Dicts to merge.

    Returns
    -------
    dict[K, FloatLike]
        Sum of the values under each key; no value aliases an input.
    """
    total: dict[K, FloatLike] = {}

    for dict_ in dicts:
        for key, value in dict_.items():
            total[key] = total.get(key, 0.0) + value

    return total


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


def sum_nonempty_values[K](dict_: Mapping[K, FloatArray]) -> FloatArray:
    """
    Sum a non-empty dict's arrays element-wise.

    Parameters
    ----------
    dict_
        Arrays to sum, at least one.

    Returns
    -------
    FloatArray
        Sum of the arrays.
    """
    summed: FloatArray = np.add.reduce(list(dict_.values()))
    return summed


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


def sum_by_first_key[K1, K2](
    dict_: Mapping[tuple[K1, K2], FloatArray],
) -> dict[K1, FloatArray]:
    """
    Sum a tuple dict's values over the second key, keyed by the first.

    Parameters
    ----------
    dict_
        Arrays to sum, keyed by pairs.

    Returns
    -------
    dict[K1, FloatArray]
        Sums over the second key, by the first.
    """
    groups: dict[K1, dict[K2, FloatArray]] = {}

    for (first, second), value in dict_.items():
        groups.setdefault(first, {})[second] = value

    return {key: sum_nonempty_values(group) for key, group in groups.items()}


def sum_by_second_key[K1, K2](
    dict_: Mapping[tuple[K1, K2], FloatArray],
) -> dict[K2, FloatArray]:
    """
    Sum a tuple dict's values over the first key, keyed by the second.

    Parameters
    ----------
    dict_
        Arrays to sum, keyed by pairs.

    Returns
    -------
    dict[K2, FloatArray]
        Sums over the first key, by the second.
    """
    groups: dict[K2, dict[K1, FloatArray]] = {}

    for (first, second), value in dict_.items():
        groups.setdefault(second, {})[first] = value

    return {key: sum_nonempty_values(group) for key, group in groups.items()}


def slice_list(arrays: Sequence[FloatArray], idx: Index) -> list[FloatLike]:
    """
    Slice each array in a list.

    Parameters
    ----------
    arrays
        Arrays to slice.
    idx
        Time-step index(es) or slice.

    Returns
    -------
    list[FloatLike]
        Sliced arrays, in order.
    """
    return [array[idx] for array in arrays]


def slice_dict[K](dict_: Mapping[K, FloatArray], idx: Index) -> dict[K, FloatLike]:
    """
    Slice each array in a dict.

    Parameters
    ----------
    dict_
        Arrays to slice.
    idx
        Time-step index(es) or slice.

    Returns
    -------
    dict[K, FloatLike]
        Sliced arrays, by key.
    """
    return {key: value[idx] for key, value in dict_.items()}


def slice_dict_list[K](
    dict_: Mapping[K, Sequence[FloatArray]], idx: Index
) -> dict[K, list[FloatLike]]:
    """
    Slice each array in each list of a dict of lists.

    Parameters
    ----------
    dict_
        Lists of arrays to slice.
    idx
        Time-step index(es) or slice.

    Returns
    -------
    dict[K, list[FloatLike]]
        Sliced lists of arrays, by key.
    """
    return {key: slice_list(value, idx) for key, value in dict_.items()}
