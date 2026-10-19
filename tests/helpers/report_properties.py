# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Shared state for the tests that check report properties against profile results.

Used by the report-property checks over the reference manual in tests/unit/docs.
"""

from __future__ import annotations

from navigate.parser._commands import _REPORT_COMMANDS
from navigate.parser._report_properties import PROFILE_CLASSES
from navigate.util import attribute_to_instance_name

assert set(PROFILE_CLASSES) == set(_REPORT_COMMANDS)


def result_for(token: str) -> str:
    """
    Name the profile result a report-property token resolves to.

    Parameters
    ----------
    token : str
        The property token as a deck writes it, e.g. ``TotalEquivalentWTT``.

    Returns
    -------
    str :
        The result name, e.g. ``total_equivalent_wtt``.
    """
    return attribute_to_instance_name(token)


def token_for(result: str) -> str:
    """
    Spell the report-property token a profile result would be reached by.

    ``attribute_to_instance_name`` is lossy - it drops every character outside an
    ``[A-Z][a-z]*`` run - so this is a candidate token, not an inverse: a caller
    must check that ``result_for`` maps it back to the result it started from.

    Parameters
    ----------
    result : str
        A result name of a profile class, e.g. ``total_equivalent_wtt``.

    Returns
    -------
    str :
        The candidate token, e.g. ``TotalEquivalentWtt``.
    """
    return "".join(part.capitalize() for part in result.split("_"))
