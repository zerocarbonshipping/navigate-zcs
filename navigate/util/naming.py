# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Wildcard matching and mapping of deck-facing attribute tokens to method names."""

from __future__ import annotations

import re
from enum import Enum
from fnmatch import fnmatchcase
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


def retrieve_keys[K: str | Enum](key: str | K, allowed_keys: Iterable[K]) -> list[K]:
    """
    Retrieve all keys from 'allowed_keys' matching the (potential) wildcard in key.

    Parameters
    ----------
    key
        Name of node, possibly including wildcards; a non-string key is
        returned as-is, but must be present in 'allowed_keys'.
    allowed_keys
        Collection of allowable keys; strings whenever 'key' is a string.

    Returns
    -------
    list[K]
        List of all keys matching 'key' ('key' only if no wildcards).

    Raises
    ------
    KeyError
        If no allowed key matches 'key'.
    """
    if not isinstance(key, str):
        if key not in allowed_keys:
            raise KeyError(key_name(key))

        return [key]

    # fast path: exact lookup when no wildcards are present
    if not name_contains_wildcards(key):
        for allowed_key in allowed_keys:
            if allowed_key == key:
                return [allowed_key]
        raise KeyError(key)

    # a string pattern only matches string keys
    keys: list[K] = [
        allowed_key
        for allowed_key in allowed_keys
        if isinstance(allowed_key, str) and fnmatchcase(str(allowed_key), str(key))
    ]

    if not keys:
        raise KeyError(key)

    return keys


def matching_keys[K: str | Enum](key: str | K, allowed_keys: Iterable[K]) -> list[K]:
    """
    Retrieve the keys matching the wildcard expression in 'key'.

    A key matching nothing returns an empty list instead of raising.

    Parameters
    ----------
    key
        Name of node, possibly including wildcards; a non-string key is
        returned as-is when present in 'allowed_keys'.
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


def key_name(key: str | Enum) -> str:
    """
    Name a dictionary key the way a deck writes it.

    Enum members are named so that an error carrying the key reads as the deck
    wrote it; a KeyError renders its argument with 'repr'.

    Parameters
    ----------
    key
        Key of a dictionary keyed by node names or enum members.

    Returns
    -------
    str
        Name of an enum member, the key itself otherwise.
    """
    return key.name if isinstance(key, Enum) else key


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


def setter_to_attribute(setter: str) -> str:
    """
    Convert a setter method name back to the deck attribute it takes.

    The inverse of ``attribute_to_setter``: ``set_lower_heating_value`` is
    ``LowerHeatingValue``.

    Parameters
    ----------
    setter
        The method name, ``set_`` followed by lowercase words joined by ``_``.

    Returns
    -------
    str
        The attribute name as a deck writes it.
    """
    return "".join(word.capitalize() for word in setter.removeprefix("set_").split("_"))


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

    The glob is matched with ``fnmatch``: ``*`` matches any run of characters,
    ``?`` any one character, and ``[...]`` one character of a set.

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
