# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""List and dict helpers, including extraction and slicing of profile results."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast, overload

import numpy as np

if TYPE_CHECKING:
    from collections.abc import (
        Collection,
        Hashable,
        Iterable,
        Mapping,
        Sequence,
    )

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
    Merge dicts together, adding the values if keys are duplicate across multiple dicts.

    Parameters
    ----------
    dicts
        A number of dicts with similar or unique keys.

    Returns
    -------
    dict[K, FloatLike]
        A single merged dict with the sum of overlapping keys; the values
        never alias the inputs.
    """
    total: dict[K, FloatLike] = {}

    for other in dicts:
        for key, value in other.items():
            total[key] = total.get(key, 0.0) + value

    return total


def multiply_dicts[K](*dicts: dict[K, FloatLike]) -> dict[K, FloatLike]:
    """
    Merge dicts, multiplying the values if keys are duplicate across multiple dicts.

    Parameters
    ----------
    dicts
        A number of dicts with similar or unique keys.

    Returns
    -------
    dict[K, FloatLike]
        A single merged dict with the product of overlapping keys; the values
        never alias the inputs.
    """
    total: dict[K, FloatLike] = {}

    for other in dicts:
        for key, value in other.items():
            total[key] = total.get(key, 1.0) * value

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

    representative = next(iter(dict_))
    return not isinstance(representative, tuple)


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

    representative = next(iter(dict_))
    return isinstance(representative, tuple) and len(representative) == 2


@overload
def extract_from_dict[K](
    result: dict[K, FloatLike], key: None = None, idx: Index = ...
) -> dict[K, FloatLike]: ...
@overload
def extract_from_dict[K](
    result: dict[K, FloatLike], key: K, idx: Index = ...
) -> FloatLike: ...
def extract_from_dict[K](
    result: dict[K, FloatLike],
    key: K | None = None,
    idx: Index = np.s_[:],
) -> dict[K, FloatLike] | FloatLike:
    """
    Extract results from a plain dict: dict[K, FloatLike].

    If key is given, returns the sliced value at key.
    If key is None, returns the whole dict with each value sliced (when possible).

    Parameters
    ----------
    result
        Profile result given as a plain dict.
    key
        Key.
    idx
        Time-step index(es) or slice; defaults to the full slice.

    Returns
    -------
    dict[K, FloatLike] | FloatLike
        Desired form of result from dict, mirroring whether key is given.
    """
    if not result:
        return result

    if key is not None:
        return _slice_value(result[key], idx)

    return _resolve_dict(result, idx)


def sum_dict_results[K](
    result: dict[K, FloatArray],
    idx: Index | None = None,
) -> FloatLike:
    """
    Sum a dict's values, optionally sliced by index first.

    Parameters
    ----------
    result
        Profile result given as a dict of arrays.
    idx
        Time-step index(es) or slice.

    Returns
    -------
    FloatLike
        Sum of the (sliced) values; 0.0 for an empty dict with an index.
    """
    arrays = list(result.values())

    if not arrays:
        if idx is not None:
            return 0.0

        raise ValueError("Dict is empty.")

    if idx is not None:
        total: FloatLike = np.add.reduce([array[idx] for array in arrays])
        return total

    summed: FloatArray = np.add.reduce(arrays)
    return summed


def collapse_tuple_dict[K1: Hashable, K2: Hashable](
    result: dict[tuple[K1, K2], FloatArray],
    key1: bool = False,
    key2: bool = False,
) -> (
    FloatLike
    | dict[K1, FloatLike]
    | dict[K2, FloatLike]
    | dict[tuple[K1, K2], FloatLike]
):
    """
    Sum a tuple dict over its collapsed key part(s).

    Collapsing both parts sums everything into a single value; collapsing one
    part returns a dict keyed by the other; collapsing neither returns the
    dict as-is.

    Parameters
    ----------
    result
        Profile result given as a tuple dict.
    key1
        Whether to collapse the dict over the primary keys.
    key2
        Whether to collapse the dict over the secondary keys.

    Returns
    -------
    dict | FloatLike
        Desired form of result from tuple dict; dicts are keyed by the
        uncollapsed key part(s).
    """
    if key1 and key2:
        return sum_dict_results(result)

    if key1:
        primary_keys = unique_list([key for (key, _) in result])
        return {
            key: sum_dict_results(
                {k2: value for (k1, k2), value in result.items() if k1 == key}
            )
            for key in primary_keys
        }

    if key2:
        secondary_keys = unique_list([key for (_, key) in result])
        return {
            key: sum_dict_results(
                {k1: value for (k1, k2), value in result.items() if k2 == key}
            )
            for key in secondary_keys
        }

    # returned as-is; only the static value type widens
    return cast("dict[tuple[K1, K2], FloatLike]", result)


def slice_list(
    result: list[FloatArray],
    idx: Index = np.s_[:],
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
    idx: Index = np.s_[:],
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
    idx: Index = np.s_[:],
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


def _resolve_dict[K](
    result: dict[K, FloatLike],
    idx: Index | None,
) -> dict[K, FloatLike]:
    if idx is None:
        return result

    return {key: _slice_value(value, idx) for key, value in result.items()}


def _slice_value(value: FloatLike, idx: Index | None) -> FloatLike:
    # unchecked callers pass scalar kinds beyond the declared float; only
    # arrays are sliceable, everything else passes through untouched
    if idx is None or not isinstance(value, np.ndarray):
        return value

    sliced: FloatLike = value[idx]
    return sliced
