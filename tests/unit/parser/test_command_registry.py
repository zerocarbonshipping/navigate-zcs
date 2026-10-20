# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The command surface: which command each node type takes, and in which section.

Every `(node type, command)` the classes declare is tried in both sections
against the check the parser runs before any command.
"""

from __future__ import annotations

import re

import pytest

from helpers.deck_surface import NODE_COMMAND_SECTIONS
from navigate.core.dsl import SECTION_DEFINE
from navigate.core.enum_ import (
    SectionID,
)
from navigate.core.node_registry import GENERAL_NODE_CLASS
from navigate.exceptions import DeckError
from navigate.parser._collect import deck_entry
from navigate.parser._lark_parser import Command

DEFINE = SectionID.DEFINE
EVENTS = SectionID.EVENTS

ENTRIES = [
    pytest.param(node_type, command, sections, id=f"{node_type}.{command}")
    for node_type, commands in NODE_COMMAND_SECTIONS.items()
    for command, sections in commands.items()
]

# the DEFINE-only commands; a deck may re-open any node type in EVENTS
EVENTS_REJECTED = [
    pytest.param(node_type, command, id=f"{node_type}.{command}")
    for node_type, commands in NODE_COMMAND_SECTIONS.items()
    for command, sections in commands.items()
    if sections == SECTION_DEFINE
]


# ── the section check, entry by entry ─────────────────────────────────────────


# input:    | e.g. Fleet "f" { set_newbuild_limit(...) }            in EVENTS
#           | and  Fleet "f" { set_initial_technology_share(...) }  in EVENTS
# expected: -> set_newbuild_limit is accepted; set_initial_technology_share
#              -> DeckError "Nodes of type 'Fleet' does not allow use of command
#              'set_initial_technology_share' in 'EVENTS'"
@pytest.mark.parametrize(("node_type", "command", "sections"), ENTRIES)
@pytest.mark.parametrize("section", [DEFINE, EVENTS], ids=["DEFINE", "EVENTS"])
def test_command_section(node_type, command, sections, section):
    if section in sections:
        deck_entry(node_type, Command(command), section)
        return

    message = (
        f"Nodes of type '{node_type}' does not allow use of command '{command}' in "
        f"'{section.name}'"
    )
    with pytest.raises(DeckError, match=f"{re.escape(message + '.')}$"):
        deck_entry(node_type, Command(command), section)


# input:    | e.g. Port "p" { bogus(1) }
# expected: -> DeckError "Nodes of type 'Port' has no command 'bogus'"
@pytest.mark.parametrize("node_type", NODE_COMMAND_SECTIONS)
def test_node_type_has_no_unknown_command(node_type):
    message = f"Nodes of type '{node_type}' has no command 'bogus'"

    with pytest.raises(DeckError, match=f"{re.escape(message + '.')}$"):
        deck_entry(node_type, Command("bogus"), DEFINE)


# input:    | Fuel "f" { Set_ttw("co2", 3.2) }
# expected: -> DeckError "... has no command 'Set_ttw'" (only set_ttw is known)
def test_a_command_name_is_case_sensitive():
    with pytest.raises(DeckError, match="has no command 'Set_ttw'"):
        deck_entry("Fuel", Command("Set_ttw"), DEFINE)


# ── the parser runs the check before any command ──────────────────────────────


# input:    | DEFINE: Fleet "n" { }
#           | EVENTS: Start
#           |         Fleet "n" { set_initial_technology_share() }
# expected: -> DeckError "Error in deck file, line 2, include file '.../events.inc',
#              line 3: Nodes of type 'Fleet' does not allow use of command
#              'set_initial_technology_share' in 'EVENTS'."
@pytest.mark.parametrize(("node_type", "command"), EVENTS_REJECTED)
def test_a_define_only_command_in_events_stops_the_deck(
    tmp_path, read_deck, node_type, command
):
    message = (
        f"Error in deck file, line 2, include file '{tmp_path / 'events.inc'}', "
        f"line 3: Nodes of type '{node_type}' does not allow use of command "
        f"'{command}' in 'EVENTS'."
    )

    with pytest.raises(DeckError, match=f"^{re.escape(message)}$"):
        read_deck(
            f'{node_type} "n" {{\n}}\n',
            events=f'Start\n{node_type} "n" {{\n    {command}()\n}}\n',
        )


# input:    | Port "p" {
#           |     bogus(1)
#           | }
# expected: -> DeckError "Error in deck file, line 1, include file '.../define.inc',
#              line 6: Nodes of type 'Port' has no command 'bogus'."
def test_an_unknown_command_stops_the_deck(tmp_path, read_deck):
    message = (
        f"Error in deck file, line 1, include file '{tmp_path / 'define.inc'}', "
        "line 6: Nodes of type 'Port' has no command 'bogus'."
    )

    with pytest.raises(DeckError, match=f"^{re.escape(message)}$"):
        read_deck('Port "p" {\n    bogus(1)\n}\n')


# input:    | e.g. ModelDefinition {
#           |          set_x(1)
#           |      }
# expected: -> DeckError "Error in deck file, line 1, include file '.../define.inc',
#              line 6: 'ModelDefinition' does not support commands."
@pytest.mark.parametrize("type_", GENERAL_NODE_CLASS)
def test_a_general_node_takes_no_command(tmp_path, read_deck, type_):
    # ModelDefinition is declared again: the base declaration is re-opened
    message = (
        f"Error in deck file, line 1, include file '{tmp_path / 'define.inc'}', "
        f"line 6: '{type_}' does not support commands."
    )

    with pytest.raises(DeckError, match=f"^{re.escape(message)}$"):
        read_deck(f"{type_} {{\n    set_x(1)\n}}\n")
