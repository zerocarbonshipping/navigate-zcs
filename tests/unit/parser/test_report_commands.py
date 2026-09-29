# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
A Report property its command does not report stops the parse at its deck line.

The Report node is a root, so the prune keeps it without a referencing node.
"""

from __future__ import annotations

import pytest

from navigate.exceptions import CommandError


def _report(*commands):
    return 'Report "r" {\n' + "".join(f"    {c}\n" for c in commands) + "}\n"


def test_a_reported_property_parses(read_deck):
    parser = read_deck(_report('add_fleet_property("*", CargoMiles)'))

    assert parser.nodes.reports["r"].fleet_reports["*"].getters == ["get_cargo_miles"]


@pytest.mark.parametrize(
    ("command", "token"),
    [
        ("add_fleet_property", "CargoMils"),
        # BunkerPrice is reported for ports only
        ("add_vessel_property", "BunkerPrice"),
    ],
    ids=["unknown_token", "token_of_another_command"],
)
def test_an_unreported_property_is_a_command_error_at_its_line(
    read_deck, command, token
):
    # define.inc opens with a blank line and the three lines of ModelDefinition,
    # then the Report header and the valid command
    deck = _report('add_fleet_property("*", CargoMiles)', f'{command}("*", {token})')

    with pytest.raises(
        CommandError, match=rf"define\.inc', line 7: '{command}' .*'{token}'"
    ):
        read_deck(deck)
