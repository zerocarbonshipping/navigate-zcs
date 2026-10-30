# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
A wildcard node reference in a value expands to the nodes it matches.

The expansion runs once every declaration is read, so it matches nodes
declared after it, and the setter only ever sees the expanded nodes. A
wildcard inside a list splices its matches in place, a bare one becomes a
list, and one matching nothing is a located deck error. A command argument
takes no wildcard node reference. (Wildcards in node names and in enum command
arguments are covered with declarations and with the command registry.)
"""

from __future__ import annotations

import pytest

from helpers.parser_decks import FLEET, FUEL, line_of
from navigate.exceptions import DeckError

# a second vessel under a name the Fleet's wildcard matches, and a third one it
# does not; the Fleet re-declaration comes before both
SECOND_VESSEL = 'Copy Vessel "vessel" "vessel_b"\n'
OTHER_VESSEL = 'Copy Vessel "vessel" "other"\n'


# input:    | Fleet "fleet" { Vessels = Vessel("vessel*") }
#           | Copy Vessel "vessel" "vessel_b"
#           | Copy Vessel "vessel" "other"
# expected: -> fleet assets are vessel and vessel_b, declared after the Fleet;
#              "other" does not match
@pytest.mark.parametrize(
    ("vessels", "expected"),
    [
        ('Vessel("vessel*")', ["vessel", "vessel_b"]),
        ('[Vessel("other"), Vessel("vessel_*")]', ["other", "vessel_b"]),
    ],
    ids=["bare", "in_list"],
)
def test_a_wildcard_value_matches_nodes_declared_after_it(read_deck, vessels, expected):
    define = (
        FLEET
        + FUEL
        + f'Fleet "fleet" {{\n    Vessels = {vessels}\n}}\n'
        + SECOND_VESSEL
        + OTHER_VESSEL
    )

    parser = read_deck(define)

    assert [vessel.name for vessel in parser.nodes.fleets["fleet"].vessels] == expected


# input:    | Fleet "fleet" { Vessels = Vessel("ghost*") }
# expected: -> DeckError "...define.inc', line N: No node of type 'Vessel'
#              matches the wildcard expression 'ghost*'."
def test_a_wildcard_value_without_a_match_is_a_located_error(tmp_path, read_deck):
    define = FLEET + 'Fleet "fleet" {\n    Vessels = Vessel("ghost*")\n}\n'

    with pytest.raises(DeckError) as error:
        read_deck(define)

    line = line_of(tmp_path / "define.inc", 'Vessel("ghost*")')
    assert str(error.value).endswith(
        f"define.inc', line {line}: No node of type 'Vessel' matches the wildcard "
        "expression 'ghost*'."
    )


# input:    | Fuel "oil" { ... set_ttw("co2", Variable("v*")) }
# expected: -> DeckError "...line 11: 'set_ttw' does not accept a wildcard
#              node reference as an argument."
def test_a_wildcard_command_argument_is_rejected(read_deck):
    define = 'Emission "co2" { }\n' + FUEL.replace(
        "}", '    set_ttw("co2", Variable("v*"))\n}'
    )

    with pytest.raises(
        DeckError,
        match=(
            r"define\.inc', line 11: 'set_ttw' does not accept a wildcard node "
            r"reference as an argument\.$"
        ),
    ):
        read_deck(define)
