# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Wildcard matching and mapping of deck-facing attribute tokens to method names."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Iterable


def retrieve_keys[K](key: str | K, allowed_keys: Iterable[K]) -> list[K]:
    """
    Retrieve all keys from 'allowed_keys' matching the (potential) wildcard in key.

    Parameters
    ----------
    key
        Name of node, possibly including wildcards; a non-string key is
        returned as-is without matching.
    allowed_keys
        Collection of allowable keys; strings whenever 'key' is a string.

    Returns
    -------
    list[K]
        List of all keys matching 'key' ('key' only if no wildcards).
    """
    if not isinstance(key, str):
        return [key]

    # fast path: exact lookup when no wildcards are present
    if not name_contains_wildcards(key):
        for allowed_key in allowed_keys:
            if allowed_key == key:
                return [allowed_key]
        raise KeyError(key)

    regex = re.compile(wildcard_to_regex(key))
    # a string key is only matched against string keys; non-string keys
    # take the early return above
    keys = [
        allowed_key
        for allowed_key in allowed_keys
        if regex.match(cast("str", allowed_key))
    ]

    if not keys:
        raise KeyError(key)

    return keys


def matching_keys[K](key: str | K, allowed_keys: Iterable[K]) -> list[K]:
    """
    Retrieve the keys matching the wildcard expression in 'key'.

    A key matching nothing returns an empty list instead of raising.

    Parameters
    ----------
    key
        Name of node, possibly including wildcards; a non-string key is
        returned as-is without matching.
    allowed_keys
        Collection of allowable keys; strings whenever 'key' is a string.

    Returns
    -------
    list[K]
        List of all keys matching 'key'; empty when nothing matches.
    """
    try:
        return retrieve_keys(key, allowed_keys)
    except KeyError:
        return []


def attribute_to_setter(attribute: str, method: str = "set") -> str:
    """
    Convert a Parser-read attribute name to a setter method name.

    The attribute is read from the input deck in format:
        AbcdEfgh
    and converted to internal setter method format:
        <method>_abcd_efgh

    Only capitalized words are kept: any character outside an [A-Z][a-z]* run
    is dropped.

    Examples
    --------
    - Extrapolate
    - LowerHeatingValue

    Parameters
    ----------
    attribute
        String read as the left-hand side of an assignment statement in the input deck.
    method
        Prefix to the function, usually either 'set' or 'get'.

    Returns
    -------
    str
        String which can be used to call a setter method of a Class using 'getattr()'.
    """
    return method + "".join(
        "_" + word.lower() for word in re.findall(r"[A-Z][a-z]*", attribute)
    )


def attribute_to_instance_name(attribute: str) -> str:
    """
    Convert a DSL attribute name to its snake_case instance-attribute name.

    E.g. 'LowerHeatingValue' becomes 'lower_heating_value', matching what its setter
    assigns.

    Parameters
    ----------
    attribute
        String read as the left-hand side of an assignment statement in the input deck.

    Returns
    -------
    str
        The corresponding instance-attribute name.
    """
    return attribute_to_setter(attribute, method="")[1:]


def name_contains_wildcards(name: str) -> bool:
    """
    Test whether a node name includes wildcard characters.

    Examples
    --------
    - Na*
    - Na?e

    Parameters
    ----------
    name
        Name used to access a specific node.

    Returns
    -------
    bool
        Whether the name includes wildcards.
    """
    return any(wildcard in name for wildcard in ("*", "?"))


def wildcard_to_regex(word: str) -> str:
    """
    Convert a limited selection of Windows wildcards to a python regular expression.

    Examples
    --------
    - Na*
    - Na?e
    - Name

    Parameters
    ----------
    word
        Word possibly containing wildcards.

    Returns
    -------
    str
        Regular expression.
    """
    replacements = {"*": r".*", "?": r"\w"}
    return "^" + "".join(replacements.get(char, char) for char in word) + "$"
