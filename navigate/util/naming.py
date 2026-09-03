# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import re


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


def matching_keys(key, allowed_keys, key_fn=None):
    """
    Retrieve the keys matching the (potential) wildcard expression in 'key',
    with a key matching nothing returning an empty list instead of raising.

    Parameters
    ----------
    key : str | int | Enum
        Name of node, possibly including wildcards.
    allowed_keys : tuple | dict | Enum
        Collection of allowable keys.
    key_fn : callable, optional
        Function to extract a string name from each key for matching.

    Returns
    -------
    list :
        List of all keys matching 'key'; empty when nothing matches.
    """

    try:
        return retrieve_keys(key, allowed_keys, key_fn)
    except KeyError:
        return []


def attribute_to_setter(attribute, method='set'):
    """
    Converts attributes read by the Parser from the input deck in format:
        AbcdEfgh
    to internal setter method format:
        <method>_abcd_efgh

    Acronym runs are lowercased as a single segment: 'CAPEX' becomes
    'set_capex' and 'TotalEquivalentWTT' becomes 'get_total_equivalent_wtt'.

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
        method += '_' + match.lower()

    return method


def attribute_to_instance_name(attribute):
    """
    Converts a DSL attribute name (e.g. 'LowerHeatingValue') to the snake_case
    instance-attribute name its setter assigns (e.g. 'lower_heating_value').

    Parameters
    ----------
    attribute : str
        String read as the left-hand side of an assignment statement in the input deck.

    Returns
    -------
    str :
        The corresponding instance-attribute name.
    """

    return attribute_to_setter(attribute, method='')[1:]


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
