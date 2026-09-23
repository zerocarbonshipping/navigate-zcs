# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The report-property appendix documents exactly the properties a report can carry.

docs/reference_manual/report.md is hand-written with no autodoc, and report
properties have no parser-side allow-list, so a table row and a profile getter
can drift apart in either direction without anything failing: a stale row sends a
deck writer after a column the report writer will skip with a logged error, and a
getter no row names is a result nobody can find.

Both directions are checked here. Forward: every documented token resolves to a
getter the report writer can call on the profile class of every command the table
is listed under. Reverse: every getter reachable from a token is documented under
every command whose profile class exposes it. The corpus is the manual;
test_report_properties.py holds the committed decks to the same getters.
"""

from __future__ import annotations

import pytest

from helpers.reference_manual import REPORT_PAGE, report_property_tables
from helpers.report_properties import (
    PLUMBING_GETTERS,
    PROFILE_CLASSES,
    getter_for,
    is_argument_free,
    token_for,
)

TABLES = report_property_tables()


def _documented_tokens():
    """Collect the tokens each report command is given a table row under."""
    documented = {command: set() for command in PROFILE_CLASSES}

    for table in TABLES:
        for command in table.commands:
            documented[command].update(row.token for row in table.rows)

    return documented


DOCUMENTED = _documented_tokens()


def _documented_properties():
    """Every (command, token) pair an appendix table carries, with its page line."""
    return [
        pytest.param(command, token, id=f"{REPORT_PAGE.name}:{line}:{command}:{token}")
        for table in TABLES
        for command in table.commands
        for line, token in table.rows
    ]


def _resolvable_properties():
    """Every (command, token) pair the report writer could resolve on a profile."""
    found = []

    for command, profile_class in PROFILE_CLASSES.items():
        getters = sorted(name for name in dir(profile_class) if name.startswith("get_"))

        for getter in getters:
            if getter in PLUMBING_GETTERS:
                continue

            if not is_argument_free(getattr(profile_class, getter)):
                continue

            token = token_for(getter)

            # a getter whose token reads back as another getter is reachable from
            # no deck, so no row can be demanded for it
            if getter_for(token) != getter:
                continue

            found.append(pytest.param(command, token, id=f"{command}:{token}"))

    return found


@pytest.mark.parametrize(("command", "token"), _documented_properties())
def test_documented_property_resolves(command, token):
    profile_class = PROFILE_CLASSES[command]
    getter = getter_for(token)

    assert hasattr(profile_class, getter), (
        f"'{token}' is documented for {command} but {profile_class.__name__} has no"
        f" getter '{getter}'"
    )

    assert is_argument_free(getattr(profile_class, getter)), (
        f"'{token}' is documented for {command} but resolves to"
        f" {profile_class.__name__}.{getter}, which the report writer cannot call"
        " without arguments"
    )


@pytest.mark.parametrize(("command", "token"), _resolvable_properties())
def test_resolvable_property_is_documented(command, token):
    assert token in DOCUMENTED[command], (
        f"'{token}' resolves on {PROFILE_CLASSES[command].__name__} but no"
        f" {REPORT_PAGE.name} table listing {command} documents it"
    )
