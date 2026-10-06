# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Attribute coverage: one deck that touches every registered attribute and command.

The deck exercises both DEFINE and EVENTS, so SECTION_BOTH attributes are set at
startup and updated at runtime, and runs through the full simulation pipeline.
The registry check holds the deck to the registries in _attributes.py and
_commands.py: an attribute or command added there without a use in the deck would
otherwise ship without ever being parsed or executed by a test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from helpers.simulation import check_invariants, run_simulation
from navigate.parser._attributes import (
    GENERAL_NODE_ATTRIBUTE_SECTIONS,
    NODE_ATTRIBUTE_SECTIONS,
)
from navigate.parser._commands import NODE_COMMAND_SECTIONS
from navigate.parser._lark_parser import (
    Assignment,
    Command,
    GeneralNodeDeclaration,
    IncludeDirective,
    NodeDeclaration,
    parse_deck_content,
    parse_include_content,
)

DECK_DIR = Path(__file__).resolve().parent / "simulations" / "attribute_coverage"


def _deck_uses() -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """Every (node type, attribute) and (node type, command) the deck's includes use."""
    attributes: set[tuple[str, str]] = set()
    commands: set[tuple[str, str]] = set()
    nav_file = DECK_DIR / f"{DECK_DIR.name}.nav"
    for block in parse_deck_content(nav_file.read_text(encoding="utf-8")):
        for directive in block.directives:
            # the deck is self-contained: a Load would hide uses from this scan
            assert isinstance(directive, IncludeDirective), directive
            path = DECK_DIR / directive.path
            for statement in parse_include_content(path.read_text(encoding="utf-8")):
                if not isinstance(statement, NodeDeclaration | GeneralNodeDeclaration):
                    continue
                for item in statement.body:
                    if isinstance(item, Assignment):
                        attributes.add((statement.node_type, item.attribute))
                    elif isinstance(item, Command):
                        commands.add((statement.node_type, item.name))
    return attributes, commands


def test_deck_uses_every_registered_attribute_and_command():
    attributes, commands = _deck_uses()
    registered_attributes = {
        (node_type, name)
        for registry in (NODE_ATTRIBUTE_SECTIONS, GENERAL_NODE_ATTRIBUTE_SECTIONS)
        for node_type, names in registry.items()
        for name in names
    }
    registered_commands = {
        (node_type, name)
        for node_type, names in NODE_COMMAND_SECTIONS.items()
        for name in names
    }

    assert not registered_attributes - attributes, (
        "registered attributes the coverage deck never assigns: "
        f"{sorted(registered_attributes - attributes)}"
    )
    assert not registered_commands - commands, (
        "registered commands the coverage deck never calls: "
        f"{sorted(registered_commands - commands)}"
    )


@pytest.mark.slow
def test_invariants():
    check_invariants(run_simulation(DECK_DIR))
