# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import copy
import os
import re
from math import floor, log10
from typing import Any

import numpy as np

from navigate.core.misc import ROUND_OFF, TOLERANCE, YEAR


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


def to_numpy(scalars, x=None, y=None, n=None):
    values = np.array([_to_value(s, x, y) for s in scalars])

    if n is not None:
        values = np.array([np.full(n, v) for v in values])

    return values


def _to_value(scalar, x=None, y=None):
    return scalar if isinstance(scalar, float) else scalar.get(x, y)


def is_strictly_increasing(x):
    """
    Testing by use of np.any as it is faster than np.all.

    Parameters
    ----------
    x : np.ndarray
        Vector.

    Returns
    -------
    bool
        Whether 'x' is strictly increasing.
    """

    return not np.any(np.diff(x) <= 0)


def is_non_strictly_increasing(x):
    """
    Testing by use of np.any as it is faster than np.all.

    Parameters
    ----------
    x : np.ndarray
        Vector.

    Returns
    -------
    bool
        Whether 'x' is non-strictly increasing.
    """

    return not np.any(np.diff(x) < 0)


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


def divide_nonzero(a, b, default=0.):
    """
    Divide 'a' with 'b' where b>0, leaving defaults elsewhere.

    Parameters
    ----------
    a : np.ndarray | float
        Numerator.
    b : np.ndarray | float
        Denominator.
    default : float
        Default value in case b is zero.

    Returns
    -------
    float | np.ndarray
        Result after division.
    """

    a = np.asarray(a)
    b = np.asarray(b)

    if np.isscalar(b):
        if b > 0.0:
            return a / b
        # b <= 0: return default with shape of a
        if np.isscalar(a):
            return default
        out = np.empty_like(a, dtype=np.result_type(a, b))
        out.fill(default)
        return out

    # Allocate output with the BROADCASTED shape (not a.shape, not b.shape)
    dtype = np.result_type(a, b)
    shape = np.broadcast(a, b).shape

    if default == 0.:
        out = np.zeros(shape, dtype=dtype)
    else:
        out = np.empty(shape, dtype=dtype)
        out.fill(default)

    # where must also broadcast; b > 0 broadcasts fine
    np.divide(a, b, out=out, where=(b > 0.0))
    return out


def normalize_fractional(values, times):
    """
    Ensure values sum to unity and return a normalized container otherwise.

    Parameters
    ----------
    values : list | tuple | dict
        Container with floats and/or calculator nodes.
    times : float | np.ndarray
        Times to pass to potential calculator nodes.

    Returns
    -------
    np.ndarray | dict[float | np.ndarray]
        Normalized version of values.
    """

    n = len(values)

    if isinstance(values, list) or isinstance(values, tuple):

        _values = to_numpy(values, x=times)

        total = np.round(np.sum(_values, axis=0), ROUND_OFF)

        out = np.array([divide_nonzero(v, total, default=1. / n) for v in _values])

    elif isinstance(values, dict):

        _values = {key: _to_value(value, x=times) for key, value in values.items()}
        total = np.round(np.sum(list(_values.values()), axis=0), ROUND_OFF)

        out = {key: divide_nonzero(value, total, default=1. / n) for key, value in _values.items()}

    else:
        raise ValueError("'Values' must be either a list, tuple, or a dict.")

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


def retrieve_keys(key, allowed_keys, key_fn=None):
    """
    Retrieve all keys from 'allowed_keys' which match the (potential) wildcard expression in key.

    Parameters
    ----------
    key : str | int | Enum
        Name of node, possibly including wildcards.
    allowed_keys : tuple | dict | Enum
        Collection of allowable keys.
    key_fn : callable, optional
        Function to extract a string name from each key for matching.
        When ``None``, keys are used directly.

    Returns
    -------
    list :
        List of all keys matching 'key' ('key' only if no wildcards)
    """

    if not isinstance(key, str):
        return [key]

    # Fast path: exact lookup when no wildcards are present.
    if not name_contains_wildcards(key):
        for allowed_key in allowed_keys:
            match_name = key_fn(allowed_key) if key_fn else allowed_key
            if match_name == key:
                return [allowed_key]
        raise KeyError(key)

    regex = re.compile(wildcard_to_regex(key))
    keys = []

    for allowed_key in allowed_keys:
        match_name = key_fn(allowed_key) if key_fn else allowed_key
        if regex.match(match_name):
            keys.append(allowed_key)

    if not keys:
        raise KeyError(key)

    return keys


def timedelta_to_days(delta):
    """

    Parameters
    ----------
    delta : np.timedelta64
        Difference between two np.datetime64 objects.

    Returns
    -------
    np.ndarray :
        Timedelta in years.
    """

    return delta.astype(np.float64)


def _timedelta_to_years(delta):
    """

    Parameters
    ----------
    delta : np.timedelta64
        Difference between two np.datetime64 objects.

    Returns
    -------
    np.ndarray :
        Timedelta in years.
    """

    return timedelta_to_days(delta) / YEAR


def dates_to_days(dates):
    """
    Converts a numpy date array to an array of days.

    Parameters
    ----------
    dates : np.ndarray
        Array of dates in numpy datetime64[D] format.

    Returns
    -------
    np.ndarray
        Array of days in numpy float64 format.
    """

    return timedelta_to_days(dates - dates[0])


def dates_to_years(dates):
    """
    Converts a numpy date array to an array of days.

    Parameters
    ----------
    dates : np.ndarray
        Array of dates in numpy datetime64[D] format.

    Returns
    -------
    np.ndarray
        Array of days in numpy float64 format.
    """

    return _timedelta_to_years(dates - dates[0])


def decompose_dates(dates):
    """
    Decompose a numpy date array into three arrays containing the years, months and days (integers).

    Parameters
    ----------
    dates : np.ndarray
        Array of dates in numpy datetime64[D] format.

    Returns
    -------
    tuple[np.ndarray, np.ndarray, np.ndarray]
        Arrays containing years, months and days as integers.
    """

    years = dates.astype('datetime64[Y]').astype(int) + 1970
    months = dates.astype('datetime64[M]').astype(int) % 12 + 1
    days = (dates - dates.astype('datetime64[M]')).astype(int) + 1

    return years, months, days


def get_increments_origin_index(years, current_year, ages):
    """
    Find the time-step indexes at which a increments (vessel or plant) entered the simulation at 'age' years ago.
    Notice here that if the entity was part of the initialization of the node index 0 is used.
    This is the best available approximation as historical data is unavailable.

    years : np.ndarray
        Simulation timeline in years.
    current_year : float
        The current year (years[idx]).
    age : float
        The age of the increment.

    Returns
    -------
    np.ndarray
        Time-step indexes at which increments were added to the simulation.
    """

    return find_nearest(years, (current_year - ages)[::-1])[::-1]


def get_increment_origin_index(years, current_year, age):
    """
    Find the time-step index at which an increment (vessel or plant) entered the simulation at 'age' years ago.
    Notice here that if the entity was part of the initialization of the node index 0 is used.
    This is the best available approximation as historical data is unavailable.

    Parameters
    ----------
    years : np.ndarray
        Simulation timeline in years.
    current_year : float
        The current year (years[idx]).
    age : float
        The age of the increment.

    Returns
    -------
    int
        Time-step index at which an increment was added to the simulation.
    """

    return find_nearest(years, current_year - age)


def find_nearest(array, values):
    """
    Reference: https://stackoverflow.com/questions/2566412/find-nearest-value-in-numpy-array
    Answer by "anthonybell".

    Parameters
    ----------
    array
    values

    Returns
    -------

    """

    # make sure array is a numpy array
    array = np.array(array)

    # get insert positions
    idxs = np.searchsorted(array, values, side="left")

    # find indexes where previous index is closer
    prev_idx_is_less = ((idxs == len(array))
                        | (np.fabs(values - array[np.maximum(idxs - 1, 0)])
                           < np.fabs(values - array[np.minimum(idxs, len(array) - 1)])))

    if isinstance(values, float):
        idxs -= 1 if prev_idx_is_less else 0
    else:
        idxs[prev_idx_is_less] -= 1

    return idxs


def round_for_display(x):
    """
    Rounds off a value to the appropriate decimals for visual display.

    Parameters
    ----------
    x : float
        Value to be rounded for display.

    Returns
    -------
    float | int
        Rounded value.
    """

    abs_x = abs(x)

    if abs_x <= TOLERANCE:
        return 0

    significant = -int(floor(log10(abs_x)))

    if significant <= 0:
        return int(np.round(x, 0))

    return np.round(x, significant)


def attribute_to_setter(attribute, method='set'):
    """
    Converts attributes read by the Parser from the input deck in format:
        AbcdEfgh
    to internal setter method format:
        <method>_abcd_efgh

    Examples
    --------
    - Extrapolate
    - LowerHeatingValue

    Parameters
    ----------
    attribute : str
        String read as the left-hand side of an assignment statement in the input deck.
    method : str
        Prefix to the function, usually either 'set' or 'get'.

    Returns
    -------
    str :
        String which can be used to call a setter method of a Class using 'getattr()'.
    """

    matches = re.findall(r'([A-Z]{2,}(?=[A-Z][a-z]|$)|[A-Z][a-z]*)', attribute)

    for match in matches:
        method += '_'

        # all characters are capitalized, such as CAPEX
        if len(match) > 1 and match.isupper():
            method += match

        # only first letter is capitalized
        else:
            method += match.lower()

    return method


def name_contains_wildcards(name):
    """
    Test whether a node name include wildcard characters.

    Examples
    --------
    - Na*
    - Na?e
    - Name#


    Parameters
    ----------
    name : str
        Name used to access a specific node.

    Returns
    -------
    bool :
        Whether the name includes wildcards.
    """

    return True if any([wildcard in name for wildcard in ('*', '?')]) else False


def wildcard_to_regex(word):
    """
    Converts a limited selection of Windows wildcards to a python regular expression.

    Examples
    --------
    - Na*
    - Na?e
    - Name

    Parameters
    ----------
    word : str
        Word possibly containing wildcards.

    Returns
    -------
    str :
        Regular expression.
    """

    expression = r'^'

    for char in word:

        if char == '*':
            expression += r'.*'

        elif char == '?':
            expression += r'\w'

        else:
            expression += char

    expression += r'$'

    return expression


def get_attributes(class_, exclude=(), name_only=False, attr_only=False):
    """
    Extracts all attributes from the supplied class except built-in attributes and attributes listed in 'exclude'.

    Parameters
    ----------
    class_ : class
        Class from which to extract attributes.
    exclude : tuple[str]
        Tuple of strings with attributes to exclude from the list.
    name_only : bool
        Only return attribute names (as strings).
    attr_only : bool
        Only return attributes.

    Returns
    -------
    generator :
        Generator of attributes.
    """

    attr = zip(list(class_.__dict__.keys()), list(class_.__dict__.values()))
    decl = (a for a in attr if not (a[0].startswith('__') and a[0].endswith('__')) and not (a[0] in exclude))

    if name_only:
        return (a[0] for a in decl)
    elif attr_only:
        return (a[1] for a in decl)
    else:
        return decl


def get_files_in_directory(directory):
    """
    Extract a list of all file names in the top level directory, excluding known
    helper/placeholder files (e.g. ``.gitkeep``).

    Parameters
    ----------
    directory : str
        Directory of where to look for files.

    Returns
    -------
    list[str] :
        List of file names.
    """

    ignored = frozenset({'.gitkeep'})

    return [
        f for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f)) and f not in ignored
    ]


def average(__arg1, __arg2, *_args):
    """
    Implementation of average using a similar structure of input as the python default 'min' and 'max'.

    Parameters
    ----------
    __arg1 : float
        Number 1.
    __arg2 : float
        Number 2
    _args : tuple
        Additional numbers.

    Returns
    -------
    float :
        The average of the numbers __arg1, __arg2 the multiple values in _args
    """

    return sum((__arg1, __arg2, *_args)) / float(2 + len(_args))


def _slice_value(v, idx):
    if idx is None:
        return v

    if np.isscalar(v) or isinstance(v, (float, int, np.number)):
        return v

    return v[idx]


def print_elapsed_time(elapsed, section):
    minutes = floor(elapsed / 60.)
    seconds = int(elapsed - minutes * 60.)

    print('Finished {}, elapsed time: {}m and {}s.'.format(section, minutes, seconds))
