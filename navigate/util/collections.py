# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""List and dict helpers, including extraction and slicing of profile results."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, cast

import numpy as np

if TYPE_CHECKING:
    from collections.abc import (
        Callable,
        Collection,
        Hashable,
        Iterable,
        Mapping,
        Sequence,
    )

    from navigate.util.arrays import FloatArray, FloatLike


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
    unique_objects = unique_list(objects)
    count = len(objects)
    return {
        object_: [index for index in range(count) if object_ == objects[index]]
        for object_ in unique_objects
    }


def merge_dicts[K, V](
    dict1: dict[K, V], *dicts: dict[K, V], in_place: bool = False
) -> dict[K, V]:
    """
    Merge dicts while maintaining the order of them.

    Parameters
    ----------
    dict1
        Primary dict.
    dicts
        A number of dicts with unique keys.
    in_place
        If true all other dicts are merged into 'dict1'.

    Returns
    -------
    dict[K, V]
        A single merged dict.
    """
    merged = dict1 if in_place else copy.deepcopy(dict1)

    for number, other in enumerate(dicts):
        for key, value in other.items():
            if key in merged:
                raise KeyError(
                    f"Key {key} encountered in dict number {number} is present in "
                    f"multiple dicts."
                )

            merged[key] = value

    return merged


def add_dicts[K](
    dict1: dict[K, FloatLike],
    *dicts: dict[K, FloatLike],
    in_place: bool = False,
) -> dict[K, FloatLike]:
    """
    Merge dicts together, adding the values if keys are duplicate across multiple dicts.

    Parameters
    ----------
    dict1
        Primary dict.
    dicts
        A number of dicts with similar or unique keys.
    in_place
        If true all other dicts are summed into 'dict1'.

    Returns
    -------
    dict[K, FloatLike]
        A single merged dict with the sum of overlapping keys.
    """
    merged = dict1 if in_place else copy.deepcopy(dict1)

    for other in dicts:
        for key, value in other.items():
            merged.setdefault(key, 0.0)
            merged[key] += value

    return merged


def multiply_dicts[K](
    dict1: dict[K, FloatLike],
    *dicts: dict[K, FloatLike],
    in_place: bool = False,
) -> dict[K, FloatLike]:
    """
    Merge dicts, multiplying the values if keys are duplicate across multiple dicts.

    Parameters
    ----------
    dict1
        Primary dict.
    dicts
        A number of dicts with similar or unique keys.
    in_place
        If true all other dicts are multiplied into 'dict1'.

    Returns
    -------
    dict[K, FloatLike]
        A single merged dict with the product of overlapping keys.
    """
    merged = dict1 if in_place else copy.deepcopy(dict1)

    for other in dicts:
        for key, value in other.items():
            merged.setdefault(key, 1.0)
            merged[key] *= value

    return merged


def divide_dicts[K](
    dict1: dict[K, FloatLike],
    *dicts: dict[K, FloatLike],
    in_place: bool = False,
) -> dict[K, FloatLike]:
    """
    Merge dicts together, divide the values if keys are duplicate across multiple dicts.

    Parameters
    ----------
    dict1
        Primary dict.
    dicts
        A number of dicts with similar or unique keys.
    in_place
        If true all other dicts are divided into 'dict1'.

    Returns
    -------
    dict[K, FloatLike]
        A single merged dict with the division of overlapping keys.
    """
    merged = dict1 if in_place else copy.deepcopy(dict1)

    for other in dicts:
        for key, value in other.items():
            if key in merged:
                merged[key] /= value
            else:
                merged[key] = value

    return merged


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


def extract_from_dict[K](
    result: dict[K, FloatLike],
    key: K | None = None,
    idx: int | slice | None = None,
    transform: Callable[[FloatLike], FloatLike] = lambda x: x,
) -> dict[K, FloatLike] | FloatLike:
    """
    Extract results from a plain dict: dict[K, FloatLike].

    If key is given, returns a single (possibly sliced) value.
    If key is None, returns the whole dict.

    If idx is not None and the return is a dict, values are sliced (when possible) then
    transformed.

    Parameters
    ----------
    result
        Profile result given as a plain dict.
    key
        Key.
    idx
        Time-step index or slice.
    transform
        Transform of the extracted values.

    Returns
    -------
    dict[K, FloatLike] | FloatLike
        Desired form of result from dict.
    """
    if not result:
        return result

    if key is not None:
        value = result[key]
        return transform(_slice_value(value, idx))

    return _resolve_dict(result, idx, transform)


def extract_from_dict_list[K](
    result: dict[K, list[FloatArray]],
    key: K | None = None,
    idx: int | slice = np.s_[:],
) -> dict[K, list[FloatArray]] | list[FloatArray]:
    """
    Extract and slice arrays from a dict of lists of ndarrays.

    Parameters
    ----------
    result
        Profile result given as a dict containing lists of ndarrays.
    key
        Key.
    idx
        Time-step index.

    Returns
    -------
    dict[K, list[FloatArray]] | list[FloatArray]
        Desired form of result from dict with sliced arrays.
    """
    if key is not None:
        return [array[idx] for array in result[key]]
    else:
        return {k: [array[idx] for array in v] for k, v in result.items()}


def extract_from_tuple_dict[K1, K2](
    result: dict[tuple[K1, K2], FloatLike],
    key1: K1 | None = None,
    key2: K2 | None = None,
    idx: int | slice | None = None,
    transform: Callable[[FloatLike], FloatLike] = lambda x: x,
) -> (
    dict[tuple[K1, K2], FloatLike]
    | dict[K1, FloatLike]
    | dict[K2, FloatLike]
    | FloatLike
):
    """
    Extract results from a tuple-keyed dict: dict[tuple[K1, K2], FloatLike].

    If both keys are given, returns a single (possibly sliced) value.
    If only key1 is given, returns {key2: value} for matching (key1, key2).
    If only key2 is given, returns {key1: value} for matching (key1, key2).
    If neither is given, returns the whole dict.

    If idx is not None and the return is a dict, values are sliced (when possible) then
    transformed.

    Parameters
    ----------
    result
        Profile result given as a tuple dict.
    key1
        First key.
    key2
        Second key.
    idx
        Time-step index or slice.
    transform
        Transform of the extracted values.

    Returns
    -------
    dict | FloatLike
        Desired form of result from tuple dict; dicts are keyed by the
        remaining key part(s).
    """
    if not result:
        return result

    if (key1 is not None) and (key2 is not None):
        value = result[(key1, key2)]
        return transform(_slice_value(value, idx))

    if key1 is not None:
        by_key2 = {k2: value for (k1, k2), value in result.items() if k1 == key1}
        return _resolve_dict(by_key2, idx, transform)

    if key2 is not None:
        by_key1 = {k1: value for (k1, k2), value in result.items() if k2 == key2}
        return _resolve_dict(by_key1, idx, transform)

    return _resolve_dict(result, idx, transform)


def sum_dict_results[K](
    result: dict[K, FloatArray],
    key: K | None = None,
    idx: int | None = None,
    n: int | None = None,
) -> FloatLike:
    """
    Sum a dict's values, or return one key's value, optionally sliced by index.

    Parameters
    ----------
    result
        Profile result given as a dict of arrays.
    key
        Key.
    idx
        Time-step index.
    n
        Length of time-line, used to size the result of an empty dict.

    Returns
    -------
    FloatLike
        Desired form of result from dict.
    """
    if key is not None:
        values = result[key]

        if idx is not None:
            value: float = values[idx]
            return value

        return values

    arrays = list(result.values())

    if not arrays:
        if idx is not None:
            return 0.0

        if n is not None:
            return np.zeros((n,))

        raise ValueError("Dict is empty and no default size 'n' is passed.")

    if idx is not None:
        total: float = np.add.reduce([array[idx] for array in arrays])
        return total

    summed: FloatArray = np.add.reduce(arrays)
    return summed


def sum_tuple_dict_results[K1, K2](
    result: dict[tuple[K1, K2], FloatArray],
    key1: K1 | None = None,
    key2: K2 | None = None,
    idx: int | None = None,
    n: int | None = None,
) -> FloatLike:
    """
    Sum the results from a tuple dict.

    If both keys are given the value is returned directly.
    If the first key is given, but not the second, it returns the sum of values for
    which the first key is included.
    If the second key is given, but not the first, it returns the sum of values for
    which the second key is included.
    If no keys are given it returns the sum of the full dict.

    Parameters
    ----------
    result
        Profile result given as a tuple dict.
    key1
        First key.
    key2
        Second key.
    idx
        Time-step index.
    n
        Length of time-line, used to size the result of an empty dict.

    Returns
    -------
    FloatLike
        Desired form of result from tuple dict.
    """
    if (key1 is not None) and (key2 is not None):
        return result[(key1, key2)]

    if key1 is not None:
        arrays = [value for (k1, _), value in result.items() if k1 == key1]
    elif key2 is not None:
        arrays = [value for (_, k2), value in result.items() if k2 == key2]
    else:
        arrays = list(result.values())

    if not arrays:
        if n is not None:
            return np.zeros((n,))

        raise ValueError("Dict is empty and no default size 'n' is passed.")

    if idx is not None:
        total: float = np.add.reduce([array[idx] for array in arrays])
        return total

    summed: FloatArray = np.add.reduce(arrays)
    return summed


def collapse_dict[K](
    result: dict[K, FloatArray],
    key: bool = False,
    idx: int | None = None,
    n: int | None = None,
) -> FloatLike | dict[K, FloatLike]:
    """
    Combine extract_from_dict and sum_dict_results.

    Collapses all arrays over the undefined key instead of creating a subdict.

    Parameters
    ----------
    result
        Profile result given as a dict of arrays.
    key
        Whether to collapse the dict.
    idx
        Time-step index.
    n
        Length of time-line, used to size the result of an empty dict.

    Returns
    -------
    dict | FloatLike
        Desired form of result from dict.
    """
    if key:
        return sum_dict_results(result, idx=idx, n=n)

    if idx is not None:
        return slice_dict(result, idx=idx)

    # returned as-is; only the static value type widens
    return cast("dict[K, FloatLike]", result)


def collapse_tuple_dict[K1: Hashable, K2: Hashable](
    result: dict[tuple[K1, K2], FloatArray],
    key1: bool = False,
    key2: bool = False,
    idx: int | None = None,
    n: int | None = None,
) -> (
    FloatLike
    | dict[K1, FloatLike]
    | dict[K2, FloatLike]
    | dict[tuple[K1, K2], FloatLike]
):
    """
    Combine extract_from_tuple_dict and sum_tuple_dict_results.

    Collapses all arrays over the undefined key instead of creating a subdict.

    Parameters
    ----------
    result
        Profile result given as a tuple dict.
    key1
        Whether to collapse the dict over the primary keys.
    key2
        Whether to collapse the dict over the secondary keys.
    idx
        Time-step index.
    n
        Length of time-line, used to size the result of an empty dict.

    Returns
    -------
    dict | FloatLike
        Desired form of result from tuple dict; dicts are keyed by the
        uncollapsed key part(s).
    """
    if key1 and key2:
        return sum_tuple_dict_results(result, idx=idx)

    if key1:
        primary_keys = unique_list([key for (key, _) in result])
        return {
            key: sum_tuple_dict_results(result, key1=key, idx=idx, n=n)
            for key in primary_keys
        }

    if key2:
        secondary_keys = unique_list([key for (_, key) in result])
        return {
            key: sum_tuple_dict_results(result, key2=key, idx=idx, n=n)
            for key in secondary_keys
        }

    if idx is not None:
        return slice_dict(result, idx)

    # returned as-is; only the static value type widens
    return cast("dict[tuple[K1, K2], FloatLike]", result)


def slice_list(
    result: list[FloatArray],
    idx: int | slice = np.s_[:],
    transform: Callable[[FloatLike], FloatLike] = lambda x: x,
) -> list[FloatLike]:
    """
    Slice and transform each array in a list.

    Parameters
    ----------
    result
        Result to be sliced.
    idx
        Specific index or slice object.
    transform
        Transform of the list values.

    Returns
    -------
    list[FloatLike]
        Sliced and transformed result.
    """
    return [transform(value[idx]) for value in result]


def slice_dict[K](
    result: dict[K, FloatArray],
    idx: int | slice = np.s_[:],
    transform: Callable[[FloatLike], FloatLike] = lambda x: x,
) -> dict[K, FloatLike]:
    """
    Slice and transform each value in a dict.

    Parameters
    ----------
    result
        Result to be sliced.
    idx
        Specific index or slice object.
    transform
        Transform of the dict values.

    Returns
    -------
    dict[K, FloatLike]
        Sliced and transformed result.
    """
    return {key: transform(value[idx]) for key, value in result.items()}


def _resolve_dict[K](
    result: dict[K, FloatLike],
    idx: int | slice | None,
    transform: Callable[[FloatLike], FloatLike],
) -> dict[K, FloatLike]:
    if idx is None:
        return result

    return {key: transform(_slice_value(value, idx)) for key, value in result.items()}


def _slice_value(value: FloatLike, idx: int | slice | None) -> FloatLike:
    if idx is None:
        return value

    if np.isscalar(value) or isinstance(value, (float, int, np.number)):
        # unchecked callers pass scalar kinds beyond the declared float
        return cast("FloatLike", value)

    sliced: FloatLike = value[idx]
    return sliced
