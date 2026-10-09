# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The attribute registry: which attribute each node type takes, and in which section.

Every `(node type, attribute)` entry of `NODE_ATTRIBUTE_SECTIONS` and
`GENERAL_NODE_ATTRIBUTE_SECTIONS` is tried in both sections against the check
the parser runs before any setter, so an attribute added to the registry is
covered here without a new case. Whether the registry matches the setters and
the reference manual is the docs suite's question.
"""

from __future__ import annotations

import re

import pytest

from navigate.core.enum_ import SectionID
from navigate.exceptions import AttributeAssignmentError
from navigate.parser._attributes import (
    GENERAL_NODE_ATTRIBUTE_SECTIONS,
    NODE_ATTRIBUTE_SECTIONS,
    check_general_node_attribute_is_allowed,
    check_node_attribute_is_allowed,
)
from navigate.parser._commands import NODE_COMMAND_SECTIONS
from navigate.parser._keywords import (
    GENERAL_NODE_CLASS,
    KEYWORD_SECTIONS,
    NODE_CLASS,
    SECTION_DEFINE,
)

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

# the DEFINE-only attributes of the node types a deck may re-open in EVENTS
EVENTS_REJECTED = [
    pytest.param(node_type, attribute, id=f"{node_type}.{attribute}")
    for node_type, attributes in NODE_ATTRIBUTE_SECTIONS.items()
    for attribute, sections in attributes.items()
    if sections == SECTION_DEFINE and EVENTS in KEYWORD_SECTIONS[node_type]
]


# input:    | Fleet "f" { ... }  /  BunkerOptions { ... }
# expected: -> every declarable type, e.g. Fleet, has an attribute table to check
#              its assignments against
def test_every_node_type_has_a_registry():
    assert set(NODE_ATTRIBUTE_SECTIONS) == set(NODE_CLASS)
    assert set(GENERAL_NODE_ATTRIBUTE_SECTIONS) == set(GENERAL_NODE_CLASS)


# input:    | Fuel "f" { MassDensity = 0.9 }   (Fuel can only be declared in DEFINE)
# expected: -> every Fuel attribute and command is DEFINE-only, since a Fuel block
#              in EVENTS is rejected before any attribute is read
@pytest.mark.parametrize(
    "node_type", [t for t, s in KEYWORD_SECTIONS.items() if s == SECTION_DEFINE]
)
def test_a_define_only_node_type_takes_nothing_in_events(node_type):
    # its declaration is rejected in EVENTS, so an EVENTS entry could never apply
    attributes = {
        **NODE_ATTRIBUTE_SECTIONS.get(node_type, {}),
        **GENERAL_NODE_ATTRIBUTE_SECTIONS.get(node_type, {}),
    }
    commands = NODE_COMMAND_SECTIONS.get(node_type, {})

    assert all(sections == SECTION_DEFINE for sections in attributes.values())
    assert all(sections == SECTION_DEFINE for sections in commands.values())


# ── the check, entry by entry ─────────────────────────────────────────────────


# input:    | e.g. Fleet "f" { Memory = 3 }        in EVENTS
#           | and  Fleet "f" { InitialVessels = 10 } in EVENTS
# expected: -> Memory (DEFINE and EVENTS) is accepted; InitialVessels (DEFINE-only)
#              -> AttributeAssignmentError "Nodes of type 'Fleet' does not allow
#              setting attribute 'InitialVessels' in 'EVENTS'"
@pytest.mark.parametrize(("node_type", "attribute", "sections"), NODE_ENTRIES)
@pytest.mark.parametrize("section", [DEFINE, EVENTS], ids=["DEFINE", "EVENTS"])
def test_node_attribute_section(node_type, attribute, sections, section):
    if section in sections:
        check_node_attribute_is_allowed(node_type, attribute, section)
        return

    message = (
        f"Nodes of type '{node_type}' does not allow setting attribute "
        f"'{attribute}' in '{section.name}'"
    )
    with pytest.raises(AttributeAssignmentError, match=f"^{re.escape(message)}$"):
        check_node_attribute_is_allowed(node_type, attribute, section)


# input:    | e.g. ModelDefinition { StartDate = "01-01-2026" }  in DEFINE / EVENTS
# expected: -> accepted in DEFINE; in EVENTS -> AttributeAssignmentError
#              "'ModelDefinition' does not allow setting attribute 'StartDate'
#              in 'EVENTS'"
@pytest.mark.parametrize(("type_", "attribute", "sections"), GENERAL_NODE_ENTRIES)
@pytest.mark.parametrize("section", [DEFINE, EVENTS], ids=["DEFINE", "EVENTS"])
def test_general_node_attribute_section(type_, attribute, sections, section):
    if section in sections:
        check_general_node_attribute_is_allowed(type_, attribute, section)
        return

    message = (
        f"'{type_}' does not allow setting attribute '{attribute}' in '{section.name}'"
    )
    with pytest.raises(AttributeAssignmentError, match=f"^{re.escape(message)}$"):
        check_general_node_attribute_is_allowed(type_, attribute, section)


# input:    | e.g. Fuel "f" { Bogus = 1 }
# expected: -> AttributeAssignmentError "Nodes of type 'Fuel' has no attribute 'Bogus'"
@pytest.mark.parametrize("node_type", NODE_ATTRIBUTE_SECTIONS)
def test_node_type_has_no_unknown_attribute(node_type):
    message = f"Nodes of type '{node_type}' has no attribute 'Bogus'"

    with pytest.raises(AttributeAssignmentError, match=f"^{re.escape(message)}$"):
        check_node_attribute_is_allowed(node_type, "Bogus", DEFINE)


# input:    | e.g. BunkerOptions { Bogus = 1 }
# expected: -> AttributeAssignmentError "'BunkerOptions' has no attribute 'Bogus'"
@pytest.mark.parametrize("type_", GENERAL_NODE_ATTRIBUTE_SECTIONS)
def test_general_node_type_has_no_unknown_attribute(type_):
    message = f"'{type_}' has no attribute 'Bogus'"

    with pytest.raises(AttributeAssignmentError, match=f"^{re.escape(message)}$"):
        check_general_node_attribute_is_allowed(type_, "Bogus", DEFINE)


# input:    | Vessel "v" { lifetime = 25 }
# expected: -> AttributeAssignmentError "... has no attribute 'lifetime'"
#              (only Lifetime is known)
def test_an_attribute_name_is_case_sensitive():
    with pytest.raises(AttributeAssignmentError, match="has no attribute 'lifetime'"):
        check_node_attribute_is_allowed("Vessel", "lifetime", DEFINE)


# ── the parser runs the check before the setter ───────────────────────────────


# input:    | DEFINE: Fleet "n" { }
#           | EVENTS: Fleet "n" { InitialVessels = 0 }
# expected: -> AttributeAssignmentError "Error in deck file, line 2, include file
#              '.../events.inc', line 2: Nodes of type 'Fleet' does not allow setting
#              attribute 'InitialVessels' in 'EVENTS'."
@pytest.mark.parametrize(("node_type", "attribute"), EVENTS_REJECTED)
def test_a_define_only_attribute_in_events_stops_the_deck(
    tmp_path, read_deck, node_type, attribute
):
    # the value is never handed to a setter, so any value shows the rejection
    message = (
        f"Error in deck file, line 2, include file '{tmp_path / 'events.inc'}', "
        f"line 2: Nodes of type '{node_type}' does not allow setting attribute "
        f"'{attribute}' in 'EVENTS'."
    )

    with pytest.raises(AttributeAssignmentError, match=f"^{re.escape(message)}$"):
        read_deck(
            f'{node_type} "n" {{\n}}\n',
            events=f'{node_type} "n" {{\n    {attribute} = 0\n}}\n',
        )


# input:    | Fuel "f" {
#           |     Bogus = 1
#           | }
# expected: -> AttributeAssignmentError "Error in deck file, line 1, include file
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

    with pytest.raises(AttributeAssignmentError, match=f"^{re.escape(message)}$"):
        read_deck(declaration)
