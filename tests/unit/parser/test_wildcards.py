# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
A wildcard node reference in a value expands to the declared nodes it matches.

The assignment is held back until the registry is complete, so it matches
nodes declared after it, and the setter only ever sees the expanded nodes. A
wildcard inside a list splices its matches in place, a bare one becomes a
list, and one matching nothing is a located deck error. A command argument
takes no wildcard node reference. (Wildcards in node names and in enum command
arguments are covered with declarations and with the command registry.)
"""

from __future__ import annotations

import pytest

from helpers.parser_decks import FLEET, FUEL, line_of
from navigate.core.enum_ import SectionID
from navigate.core.nodes.port import Port
from navigate.core.nodes.route import Route
from navigate.exceptions import CommandError, DeckFormatError
from navigate.parser._lark_parser import Assignment, SourceLocation
from navigate.parser._node_reference import WildcardNodeReference
from navigate.parser.parser import Parser

# a second vessel under a name the Fleet's wildcard matches, and a third one it
# does not; the Fleet re-declaration comes before both
SECOND_VESSEL = 'Copy Vessel "vessel" "vessel_b"\n'
OTHER_VESSEL = 'Copy Vessel "vessel" "other"\n'


def _parser_with_ports(*names):
    parser = Parser()
    for name in names:
        parser.nodes.ports[name] = Port(name)
    return parser


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

    assert [vessel.name for vessel in parser.nodes.fleets["fleet"].assets] == expected


# input:    | Fleet "fleet" { Vessels = Vessel("ghost*") }
# expected: -> DeckFormatError "...define.inc', line N: Wildcard 'ghost*' did
#              not match any Vessel nodes."
def test_a_wildcard_value_without_a_match_is_a_located_error(tmp_path, read_deck):
    define = FLEET + 'Fleet "fleet" {\n    Vessels = Vessel("ghost*")\n}\n'

    with pytest.raises(DeckFormatError) as error:
        read_deck(define)

    line = line_of(tmp_path / "define.inc", 'Vessel("ghost*")')
    assert str(error.value).endswith(
        f"define.inc', line {line}: Wildcard 'ghost*' did not match any Vessel nodes."
    )


# input:    | Fuel "oil" { ... set_ttw("co2", Variable("v*")) }
# expected: -> CommandError "...line 11: 'set_ttw' does not accept a wildcard
#              node reference as an argument."
def test_a_wildcard_command_argument_is_rejected(read_deck):
    define = 'Emission "co2" { }\n' + FUEL.replace(
        "}", '    set_ttw("co2", Variable("v*"))\n}'
    )

    with pytest.raises(
        CommandError,
        match=(
            r"define\.inc', line 11: 'set_ttw' does not accept a wildcard node "
            r"reference as an argument\.$"
        ),
    ):
        read_deck(define)


# input:    | ["BEFORE", Port("port_*"), "AFTER"]   with ports port_a, port_b, other
# expected: -> "BEFORE", port_a, port_b, "AFTER" in that order
def test_a_wildcard_inside_a_list_is_spliced_in_place():
    parser = _parser_with_ports("port_a", "port_b", "other")

    expanded = parser._expand_wildcards(
        ["BEFORE", WildcardNodeReference("Port", "port_*"), "AFTER"], "loc"
    )

    assert expanded[0] == "BEFORE"
    assert expanded[-1] == "AFTER"
    assert sorted(node.name for node in expanded[1:-1]) == ["port_a", "port_b"]


# input:    | Route "r" { Ports = Port("*") }   with ports port_a and port_b
# expected: -> route.ports stays empty until the pending assignments are
#              flushed, then holds port_a and port_b
def test_a_pending_assignment_reaches_the_setter_expanded():
    parser = _parser_with_ports("port_a", "port_b")
    parser._current_section = SectionID.DEFINE
    route = Route("r")
    parser.nodes.routes["r"] = route

    parser._apply_assignment(
        [route],
        Assignment("Ports", WildcardNodeReference("Port", "*"), SourceLocation()),
        "Route",
    )

    # held back, so the setter has not run yet
    assert route.ports == []

    parser._flush_pending_assignments()

    assert sorted(port.name for port in route.ports) == ["port_a", "port_b"]
