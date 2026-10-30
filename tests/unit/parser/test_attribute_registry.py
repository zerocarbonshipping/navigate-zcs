# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The attribute surface: which attribute each node type takes, and in which section.

Every `(node type, attribute)` the classes declare is tried in both sections
against the check the parser runs before any setter, so an attribute marked
on a setter is covered here without a new case. Whether the marks match the
setters and the reference manual is the docs suite's question.
"""

from __future__ import annotations

import re

import pytest

from helpers.deck_surface import (
    GENERAL_NODE_ATTRIBUTE_SECTIONS,
    NODE_ATTRIBUTE_SECTIONS,
)
from navigate.core.dsl import SECTION_DEFINE
from navigate.core.enum_ import SectionID
from navigate.exceptions import DeckError
from navigate.parser._collect import deck_entry
from navigate.parser._syntax import Assignment

DEFINE = SectionID.DEFINE
EVENTS = SectionID.EVENTS

NODE_ENTRIES = [
    pytest.param(node_type, attribute, sections, id=f"{node_type}.{attribute}")
    for node_type, attributes in NODE_ATTRIBUTE_SECTIONS.items()
    for attribute, sections in attributes.items()
]
GENERAL_NODE_ENTRIES = [
    pytest.param(type_, attribute, sections, id=f"{type_}.{attribute}")
    for type_, attributes in GENERAL_NODE_ATTRIBUTE_SECTIONS.items()
    for attribute, sections in attributes.items()
]

# the DEFINE-only attributes; a deck may re-open any node type in EVENTS
EVENTS_REJECTED = [
    pytest.param(node_type, attribute, id=f"{node_type}.{attribute}")
    for node_type, attributes in NODE_ATTRIBUTE_SECTIONS.items()
    for attribute, sections in attributes.items()
    if sections == SECTION_DEFINE
]


# ── the check, entry by entry ─────────────────────────────────────────────────


# input:    | e.g. Fleet "f" { Memory = 3 }        in EVENTS
#           | and  Fleet "f" { InitialVessels = 10 } in EVENTS
# expected: -> Memory (DEFINE and EVENTS) is accepted; InitialVessels (DEFINE-only)
#              -> DeckError "Nodes of type 'Fleet' does not allow setting
#              attribute 'InitialVessels' in 'EVENTS'"
@pytest.mark.parametrize(("node_type", "attribute", "sections"), NODE_ENTRIES)
@pytest.mark.parametrize("section", [DEFINE, EVENTS], ids=["DEFINE", "EVENTS"])
def test_node_attribute_section(node_type, attribute, sections, section):
    if section in sections:
        deck_entry(node_type, Assignment(attribute, 0.0), section)
        return

    message = (
        f"Nodes of type '{node_type}' does not allow setting attribute "
        f"'{attribute}' in '{section.name}'"
    )
    with pytest.raises(DeckError, match=f"{re.escape(message + '.')}$"):
        deck_entry(node_type, Assignment(attribute, 0.0), section)


# input:    | e.g. ModelDefinition { StartDate = "01-01-2026" }  in DEFINE / EVENTS
# expected: -> accepted in DEFINE; in EVENTS -> DeckError "'ModelDefinition'
#              does not allow setting attribute 'StartDate' in 'EVENTS'"
@pytest.mark.parametrize(("type_", "attribute", "sections"), GENERAL_NODE_ENTRIES)
@pytest.mark.parametrize("section", [DEFINE, EVENTS], ids=["DEFINE", "EVENTS"])
def test_general_node_attribute_section(type_, attribute, sections, section):
    if section in sections:
        deck_entry(type_, Assignment(attribute, 0.0), section)
        return

    message = (
        f"'{type_}' does not allow setting attribute '{attribute}' in '{section.name}'"
    )
    with pytest.raises(DeckError, match=f"{re.escape(message + '.')}$"):
        deck_entry(type_, Assignment(attribute, 0.0), section)


# input:    | e.g. Fuel "f" { Bogus = 1 }
# expected: -> DeckError "Nodes of type 'Fuel' has no attribute 'Bogus'"
@pytest.mark.parametrize("node_type", NODE_ATTRIBUTE_SECTIONS)
def test_node_type_has_no_unknown_attribute(node_type):
    message = f"Nodes of type '{node_type}' has no attribute 'Bogus'"

    with pytest.raises(DeckError, match=f"{re.escape(message + '.')}$"):
        deck_entry(node_type, Assignment("Bogus", 0.0), DEFINE)


# input:    | e.g. BunkerOptions { Bogus = 1 }
# expected: -> DeckError "'BunkerOptions' has no attribute 'Bogus'"
@pytest.mark.parametrize("type_", GENERAL_NODE_ATTRIBUTE_SECTIONS)
def test_general_node_type_has_no_unknown_attribute(type_):
    message = f"'{type_}' has no attribute 'Bogus'"

    with pytest.raises(DeckError, match=f"{re.escape(message + '.')}$"):
        deck_entry(type_, Assignment("Bogus", 0.0), DEFINE)


# input:    | Vessel "v" { lifetime = 25 }
# expected: -> DeckError "... has no attribute 'lifetime'" (only Lifetime is known)
def test_an_attribute_name_is_case_sensitive():
    with pytest.raises(DeckError, match="has no attribute 'lifetime'"):
        deck_entry("Vessel", Assignment("lifetime", 0.0), DEFINE)


# ── the parser runs the check before the setter ───────────────────────────────


# input:    | DEFINE: Fleet "n" { }
#           | EVENTS: Start
#           |         Fleet "n" { InitialVessels = 0 }
# expected: -> DeckError "Error in deck file, line 2, include file
#              '.../events.inc', line 3: Nodes of type 'Fleet' does not allow setting
#              attribute 'InitialVessels' in 'EVENTS'."
@pytest.mark.parametrize(("node_type", "attribute"), EVENTS_REJECTED)
def test_a_define_only_attribute_in_events_stops_the_deck(
    tmp_path, read_deck, node_type, attribute
):
    # the value is never handed to a setter, so any value shows the rejection
    message = (
        f"Error in deck file, line 2, include file '{tmp_path / 'events.inc'}', "
        f"line 3: Nodes of type '{node_type}' does not allow setting attribute "
        f"'{attribute}' in 'EVENTS'."
    )

    with pytest.raises(DeckError, match=f"^{re.escape(message)}$"):
        read_deck(
            f'{node_type} "n" {{\n}}\n',
            events=f'Start\n{node_type} "n" {{\n    {attribute} = 0\n}}\n',
        )


# input:    | Fuel "f" {
#           |     Bogus = 1
#           | }
# expected: -> DeckError "Error in deck file, line 1, include file
#              '.../define.inc', line 6: Nodes of type 'Fuel' has no attribute 'Bogus'."
@pytest.mark.parametrize(
    ("declaration", "message"),
    [
        (
            'Fuel "f" {\n    Bogus = 1\n}\n',
            "Nodes of type 'Fuel' has no attribute 'Bogus'.",
        ),
        (
            "BunkerOptions {\n    Bogus = 1\n}\n",
            "'BunkerOptions' has no attribute 'Bogus'.",
        ),
    ],
    ids=["node", "general_node"],
)
def test_an_unknown_attribute_stops_the_deck(tmp_path, read_deck, declaration, message):
    message = (
        f"Error in deck file, line 1, include file '{tmp_path / 'define.inc'}', "
        f"line 6: {message}"
    )

    with pytest.raises(DeckError, match=f"^{re.escape(message)}$"):
        read_deck(declaration)
