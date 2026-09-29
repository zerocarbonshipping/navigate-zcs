# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Report properties named in committed decks resolve to profile getters.

The parser rejects a property token its command's profile class has no getter for, but
only in a deck it reads, and no suite reads most of the committed .inc modules. This
test holds every committed deck to the same rule: every property token must map, via
attribute_to_setter, to a getter on the profile class of the command it is passed to,
callable without arguments the way the report writer calls it.

The deck scan is regex-based and expects single-line property calls, like the committed
decks.
"""

from __future__ import annotations

import re

import pytest

from helpers.report_properties import PROFILE_CLASSES, getter_for
from helpers.simulation import REPO_ROOT
from navigate.core.report_properties import is_argument_free

_PROPERTY_CALL = re.compile(
    r'\b({})\(\s*(?:"[^"]*"\s*,\s*)?([A-Za-z][A-Za-z0-9]*)'.format(
        "|".join(PROFILE_CLASSES)
    )
)
_COMMENT = re.compile(r"#[^\n]*")


def _deck_properties():
    """Every distinct (command, token) pair used in a committed .inc/.nav file."""
    found = {}
    for directory in ("assumptions", "simulations", "tests", "tutorials"):
        for path in sorted((REPO_ROOT / directory).rglob("*")):
            if path.suffix in (".inc", ".nav"):
                for pair in _PROPERTY_CALL.findall(_COMMENT.sub("", path.read_text())):
                    found.setdefault(pair, path)

    # every report command stays exercised by some committed deck; an empty scan means
    # the scanner rotted, not that the repo is clean
    assert {command for command, _ in found} == set(PROFILE_CLASSES)

    return [
        pytest.param(command, token, id=f"{path.relative_to(REPO_ROOT)}:{token}")
        for (command, token), path in found.items()
    ]


@pytest.mark.parametrize(("command", "token"), _deck_properties())
def test_deck_report_properties_resolve(command, token):
    profile_class = PROFILE_CLASSES[command]
    getter_name = getter_for(token)

    assert hasattr(profile_class, getter_name), (
        f"'{token}' does not resolve: {profile_class.__name__} has no getter "
        f"'{getter_name}'"
    )

    assert is_argument_free(getattr(profile_class, getter_name)), (
        f"'{token}' resolves to {profile_class.__name__}.{getter_name}, which the "
        f"report writer cannot call without arguments"
    )
