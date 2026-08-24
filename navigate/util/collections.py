# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import copy
from typing import Any

import numpy as np


def unique_list(items):
    """
    Create an order preserved list of unique objects in items.

    Parameters
    ----------
    items : list
        List of objects.

    Returns
    -------
    list
        Order preserved list of unique objects in items.
    """

    return list(dict.fromkeys(items))


def list_intersection(list1, list2):
    """
    Create an order preserved list of the intersection between two lists.

    Parameters
    ----------
    list1 : list
        List of objects.
    list2 : list
        List of objects.

    Returns
    -------
    list
        Order preserved list of the intersection.
    """

    return [x for x in list1 if x in list2]


def list_is_unique(values):
    return len(values) == len(set(values))


def define_index_map(objects):
    unique_objects = unique_list(objects)
    n = len(objects)
    return {object_: [i for i in range(n) if object_ == objects[i]] for object_ in unique_objects}


def merge_dicts(dict1, *dicts, in_place=False):
    """
    Merge dicts while maintaining the order of them.

    Parameters
    ----------
    dict1 : dict
        Primary dict.
    dicts : dict
        A number of dicts with unique keys.
    in_place : bool
        If true all other dicts are merged into 'dict1'.

    Returns
    -------
    dict
        A single merged dict.
    """

    if in_place:
        out = dict1
    else:
        out = copy.deepcopy(dict1)

    for i, d in enumerate(dicts):
        for key, value in d.items():

            if key in out:
                raise KeyError("Key {} encountered in dict number {} is present in multiple dicts.".format(key, i))

            out[key] = value

    return out


def add_dicts(dict1, *dicts, in_place=False):
    """
    Merge dicts together, adding up the values if keys are duplicate across multiple dicts.

    Parameters
    ----------
    dict1 : dict
        Primary dict.
    dicts : dict
        A number of dicts with similar or unique keys.
    in_place : bool
        If true all other dicts are summed into 'dict1'.

    Returns
    -------
    dict
        A single merged dict with the sum of overlapping keys.
    """

    if in_place:
        out = dict1
    else:
        out = copy.deepcopy(dict1)

    for d in dicts:
        for key, value in d.items():

            out.setdefault(key, 0.)
            out[key] += value

    return out


def multiply_dicts(dict1, *dicts, in_place=False):
    """
    Merge dicts together, multiplying the values if keys are duplicate across multiple dicts.

    Parameters
    ----------
    dict1 : dict
        Primary dict.
    dicts : dict
        A number of dicts with similar or unique keys.
    in_place : bool
        If true all other dicts are multiplied into 'dict1'.

    Returns
    -------
    dict
        A single merged dict with the product of overlapping keys.
    """

    if in_place:
        out = dict1
    else:
        out = copy.deepcopy(dict1)

    for d in dicts:
        for key, value in d.items():

            out.setdefault(key, 1.)
            out[key] *= value

    return out


def divide_dicts(dict1, *dicts, in_place=False):
    """
    Merge dicts together, divide the values if keys are duplicate across multiple dicts.

    Parameters
    ----------
    dict1 : dict
        Primary dict.
    dicts : dict
        A number of dicts with similar or unique keys.
    in_place : bool
        If true all other dicts are multiplied into 'dict1'.

    Returns
    -------
    dict
        A single merged dict with the division of overlapping keys.
    """

    if in_place:
        out = dict1
    else:
        out = copy.deepcopy(dict1)

    for d in dicts:
        for key, value in d.items():

            if key in out:
                out[key] /= value
            else:
                out[key] = value

    return out


def is_single_dict(dict_):
    """
    Check whether a dict is a single dict.

    Parameters
    ----------
    dict_ : dict

    Returns
    -------
    bool
        Whether dict is a single dict.
    """

    keys = list(dict_.keys())

    if keys:

        representative = keys[0]

        if isinstance(representative, tuple):

            return False

        else:

            return True

    return None


def is_tuple_dict(dict_):
    """
    Check whether a dict is a tuple dict.

    Parameters
    ----------
    dict_ : dict

    Returns
    -------
    bool
        Whether dict is a tuple dict.
    """

    keys = list(dict_.keys())

    if keys:

        representative = keys[0]

        if isinstance(representative, tuple):

            if len(representative) == 2:

                return True

            else:

                return False

        else:

            return False

    return None


def extract_from_dict(result, key=None, idx=None, transform=lambda x: x):
    """
    Extract results from a plain dict: dict[str, np.ndarray | float].

    If key is given, returns a single (possibly sliced) value.
    If key is None, returns the whole dict.

    If idx is not None and the return is a dict, values are sliced (when possible) then transformed.
    """

    if not result:
        return result

    if key is not None:
        v = result[key]
        return transform(_slice_value(v, idx))

    if idx is None:
        return result

    return {k: transform(_slice_value(v, idx)) for k, v in result.items()}


def extract_from_dict_list(result: dict[Any, list[np.ndarray]],
                           key: Any = None,
                           idx: int | slice = np.s_[:]) -> dict[Any, list[np.ndarray]] | list[np.ndarray]:
    """

    Parameters
    ----------
    result :
        Profile result given as a dict containing lists of ndarrays.
    key :
        Key.
    idx :
        Time-step index.

    Returns
    -------
    dict[str, list[np.ndarray]] | list[np.ndarray]
        Desired form of result from dict with sliced arrays.
    """

    if key is not None:
        return [array[idx] for array in result[key]]
    else:
        return {k: [array[idx] for array in v] for k, v in result.items()}


def extract_from_tuple_dict(result, key1=None, key2=None, idx=None, transform=lambda x: x):
    """
    Extract results from a tuple-keyed dict: dict[tuple[str, str], np.ndarray | float].

    If both keys are given, returns a single (possibly sliced) value.
    If only key1 is given, returns {key2: value} for matching (key1, key2).
    If only key2 is given, returns {key1: value} for matching (key1, key2).
    If neither is given, returns the whole dict.

    If idx is not None and the return is a dict, values are sliced (when possible) then transformed.
    """
    if not result:
        return result

    if (key1 is not None) and (key2 is not None):
        v = result[(key1, key2)]
        return transform(_slice_value(v, idx))

    if key1 is not None:
        out = {k2: r for (k1, k2), r in result.items() if k1 == key1}
    elif key2 is not None:
        out = {k1: r for (k1, k2), r in result.items() if k2 == key2}
    else:
        out = result

    if idx is None:
        return out

    return {k: transform(_slice_value(v, idx)) for k, v in out.items()}


def sum_dict_results(result, key=None, idx=None, n=None):
    """

    Parameters
    ----------
    result : dict[np.array]
        Profile result given as a dict.
    key : str
        Key.
    idx : int
        Time-step index.
    n : int
        Length of time-line.

    Returns
    -------
    dict[float] | dict[np.ndarray] | float | np.ndarray
        Desired form of result from dict.
    """

    if key is not None:

        a = result[key]

        if idx is not None:
            return a[idx]
        else:
            return a

    else:
        arrays = list(result.values())

    if not arrays:

        if idx is not None:
            return 0.

        elif n is not None:
            return np.zeros((n,))
        else:
            raise ValueError("Dict is empty and no default size 'n' is passed.")

    if idx is not None:
        return np.add.reduce([a[idx] for a in arrays])
    else:
        return np.add.reduce(arrays)


def sum_tuple_dict_results(result, key1=None, key2=None, idx=None, n=None):
    """
    Sums the results from a tuple dict.

    If both keys are given the value is returned directly.
    If the first key is given, but not the second, it returns the sum of values for which the first key is included.
    If the second key is given, but not the second, it returns the sum of values for which the second key is included.
    If no keys are given it returns the sum of the full dict.

    Parameters
    ----------
    result : dict[np.array]
        Profile result given as a tuple dict.
    key1 : str
        First key.
    key2 : str
        Second key.
    idx : int
        Time-step index.
    n : int
        Length of time-line.

    Returns
    -------
    float | np.ndarray
        Desired form of result from tuple dict.
    """

    if (key1 is not None) and (key2 is not None):

        return result[(key1, key2)]

    elif key1 is not None:

        arrays = [result[key] for key in [(k1, k2) for (k1, k2) in result if k1 == key1]]

    elif key2 is not None:

        arrays = [result[key] for key in [(k1, k2) for (k1, k2) in result if k2 == key2]]

    else:
        arrays = list(result.values())

    if not arrays:
        if n is not None:
            return np.zeros((n,))
        else:
            raise ValueError("Dict is empty and no default size 'n' is passed.")

    if idx is not None:
        return np.add.reduce([a[idx] for a in arrays])
    else:
        return np.add.reduce(arrays)


def collapse_dict(result, key=False, idx=None, n=None):
    """
    Combines extract_from_dict and sum_dict_results by collapsing all arrays over the undefined key
    instead of creating a subdict.

    Parameters
    ----------
    result : dict[np.array]
        Profile result given as a tuple dict.
    key : bool
        Whether to collapse the dict.
    idx : int
        Time-step index.
    n : int
        Length of time-line.

    Returns
    -------
    np.ndarray | dict[np.ndarray]
        Desired form of result from tuple dict.
    """

    if key:
        return sum_dict_results(result, idx=idx, n=n)

    if idx is not None:
        return slice_dict(result, idx=idx)
    else:
        return result


def collapse_tuple_dict(result, key1=False, key2=False, idx=None, n=None):
    """
    Combines extract_from_tuple_dict and sum_tuple_dict_results by collapsing all arrays over the undefined key
    instead of creating a subdict.

    Parameters
    ----------
    result : dict[np.array]
        Profile result given as a tuple dict.
    key1 : bool
        Whether to collapse the dict over the primary keys.
    key2 : bool
        Whether to collapse the dict over the secondary keys.
    idx : int
        Time-step index.
    n : int
        Length of time-line.

    Returns
    -------
    np.ndarray | dict[np.ndarray]
        Desired form of result from tuple dict.
    """

    if key1 and key2:
        return sum_tuple_dict_results(result, idx=idx)

    if key1:
        keys = unique_list([key for (key, _) in result])
        return {key: sum_tuple_dict_results(result, key1=key, idx=idx, n=n) for key in keys}

    if key2:
        keys = unique_list([key for (_, key) in result])
        return {key: sum_tuple_dict_results(result, key2=key, idx=idx, n=n) for key in keys}

    if idx is not None:
        return slice_dict(result, idx)
    else:
        return result


def slice_list(result: list[np.ndarray], idx: int | slice = np.s_[:], transform=lambda x: x) -> list[np.ndarray]:
    """

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
    Sliced and transformed result.
    """

    return [transform(value[idx]) for value in result]


def slice_dict(result, idx=np.s_[:], transform=lambda x: x):
    """

    Parameters
    ----------
    result : dict
        Result to be sliced.
    idx : int
        Specific index or slice object.
    transform : callable
        Transform of the dict values.

    Returns
    -------
    dict
        Sliced and transformed result.
    """

    return {key: transform(value[idx]) for key, value in result.items()}


def _slice_value(v, idx):
    if idx is None:
        return v

    if np.isscalar(v) or isinstance(v, (float, int, np.number)):
        return v

    return v[idx]
