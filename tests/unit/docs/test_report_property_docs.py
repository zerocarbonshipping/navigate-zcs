# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The report-property appendix documents exactly the properties a report can carry.

docs/reference_manual/report.md is hand-written with no autodoc, so a table row
and a result can drift apart in either direction without anything else
failing: a stale row sends a deck writer after a property the parser rejects, and
a result no row names is one nobody can find.

Both directions are checked here. Forward: every documented token passes the
parser's check for every command the table is listed under. Reverse: every result
reachable from a token is documented under every command whose results class
exposes it.
"""

from __future__ import annotations

import pytest

from helpers.reference_manual import REPORT_PAGE, report_property_tables
from helpers.report_properties import RESULTS_CLASSES, result_for, token_for
from navigate.core.nodes.report import check_report_property
from navigate.core.results import result_names

TABLES = report_property_tables()


def _documented_tokens():
    """Collect the tokens each report command is given a table row under."""
    documented = {command: set() for command in RESULTS_CLASSES}

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
    """Every (command, token) pair the report writer could resolve on the results."""
    found = []

    for command, results_class in RESULTS_CLASSES.items():
        for result in sorted(result_names(results_class)):
            token = token_for(result)

            # a result whose token reads back as another result is reachable from
            # no deck, so no row can be demanded for it
            if result_for(token) != result:
                continue

            found.append(pytest.param(command, token, id=f"{command}:{token}"))

    return found


# takes every property listed in the report.md tables and checks the parser
# accepts it for each command the table is listed under.
# catches: a renamed result, so the manual sends users to a property the
# parser now rejects.
@pytest.mark.parametrize(("command", "token"), _documented_properties())
def test_documented_property_resolves(command, token):
    check_report_property(command, token)


# takes every property a report command could read from its results and checks
# report.md lists it under that command.
# catches: a new result added with no manual row, so nobody knows the
# property exists.
@pytest.mark.parametrize(("command", "token"), _resolvable_properties())
def test_resolvable_property_is_documented(command, token):
    assert token in DOCUMENTED[command], (
        f"'{token}' resolves on {RESULTS_CLASSES[command].__name__} but no"
        f" {REPORT_PAGE.name} table listing {command} documents it"
    )
