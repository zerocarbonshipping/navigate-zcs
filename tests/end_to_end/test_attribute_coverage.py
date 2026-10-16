# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Attribute coverage: one deck that touches the whole registered DSL surface.

The static checks hold the deck to the registries in _attributes.py and
_commands.py, and to the ID values a deck can write: an attribute, command or ID
value added to the model without a use in the deck would otherwise ship without
ever being parsed or executed by a test. The deck exercises both DEFINE and
EVENTS, so every SECTION_BOTH attribute and command is set at startup and updated
at runtime, and one run takes it through the full simulation pipeline. Nothing
asserts its results; it answers "does every input still run".
"""

from __future__ import annotations

import inspect
from enum import Enum
from pathlib import Path

import pytest

from helpers.simulation import check_invariants, run_simulation
from navigate.core import enum_
from navigate.core.enum_ import ReportReduceID
from navigate.parser._attributes import (
    GENERAL_NODE_ATTRIBUTE_SECTIONS,
    NODE_ATTRIBUTE_SECTIONS,
)
from navigate.parser._commands import (
    _REPORT_COMMANDS,
    _WILDCARD_DOMAINS,
    NODE_COMMAND_SECTIONS,
)
from navigate.parser._keywords import (
    GENERAL_NODE_CLASS,
    NODE_CLASS,
    SECTION_BOTH,
)
from navigate.parser._lark_parser import (
    Assignment,
    Command,
    EventsBlock,
    GeneralNodeDeclaration,
    IncludeDirective,
    NodeDeclaration,
    parse_deck_content,
    parse_include_content,
)
from navigate.util import attribute_to_setter

DECK_DIR = Path(__file__).resolve().parent / "simulations" / "attribute_coverage"

ATTRIBUTES = NODE_ATTRIBUTE_SECTIONS | GENERAL_NODE_ATTRIBUTE_SECTIONS

# ID values the deck cannot write: a deck holds a single BunkerOptions, so it
# names one solver and one method, and the coverage deck keeps AUTOMATIC so it
# runs with or without a Gurobi licence
EXCLUDED_IDS = {
    ("BunkerOptions", "Solver", "GUROBI"),
    ("BunkerOptions", "Solver", "HIGHS"),
    ("BunkerOptions", "SolverMethod", "AUTOMATIC"),
    ("BunkerOptions", "SolverMethod", "NON_DETERMINISTIC"),
}

# SECTION_BOTH attributes the deck cannot update in EVENTS: every attribute that
# takes a Surface is DEFINE-only, so the parser pins every Surface and rejects
# an EVENTS assignment to it
EXCLUDED_EVENTS_ATTRIBUTES = {
    ("Surface", "Table"),
    ("Surface", "Addition"),
    ("Surface", "Multiplier"),
    ("Surface", "LowerBound"),
    ("Surface", "UpperBound"),
}

# a value no enum member is named, so a setter that rejects it as an unknown ID
# takes an ID
_NOT_AN_ID = "NOT_AN_ID"

_ID_NAMES = sorted(
    {
        member.name
        for enum in vars(enum_).values()
        if isinstance(enum, type) and issubclass(enum, Enum) and enum is not Enum
        for member in enum
    }
)


class _DeckUse:
    """Every assignment and command the deck's includes make, with its section."""

    def __init__(self) -> None:
        self.assignments: list[tuple[str, str, object, bool]] = []
        self.commands: list[tuple[str, str, list[object], bool]] = []

        nav_file = DECK_DIR / f"{DECK_DIR.name}.nav"
        for block in parse_deck_content(nav_file.read_text(encoding="utf-8")):
            in_events = isinstance(block, EventsBlock)

            for directive in block.directives:
                # the deck is self-contained: a Load would hide uses from this scan
                assert isinstance(directive, IncludeDirective), directive
                self._scan(DECK_DIR / directive.path, in_events)

    def _scan(self, path: Path, in_events: bool) -> None:
        for statement in parse_include_content(path.read_text(encoding="utf-8")):
            if not isinstance(statement, NodeDeclaration | GeneralNodeDeclaration):
                continue

            for item in statement.body:
                if isinstance(item, Assignment):
                    self.assignments.append(
                        (statement.node_type, item.attribute, item.value, in_events)
                    )
                elif isinstance(item, Command):
                    self.commands.append(
                        (statement.node_type, item.name, item.args, in_events)
                    )

    def attributes(self, *, events_only: bool = False) -> set[tuple[str, str]]:
        return {
            (node_type, attribute)
            for node_type, attribute, _, in_events in self.assignments
            if in_events or not events_only
        }

    def command_names(self, *, events_only: bool = False) -> set[tuple[str, str]]:
        return {
            (node_type, name)
            for node_type, name, _, in_events in self.commands
            if in_events or not events_only
        }


USE = _DeckUse()


def _probe(node_type: str, attribute: str, value: str) -> str | None:
    """Assign a value to a fresh node; return the error message, or None."""
    cls = NODE_CLASS.get(node_type) or GENERAL_NODE_CLASS[node_type]
    node = cls("probe") if node_type in NODE_CLASS else cls()

    # a setter reached only with a parsed value, such as a Table, may fail on a
    # bare string with any error type; only the message matters here
    try:
        getattr(node, attribute_to_setter(attribute))(value)
    except Exception as e:
        return str(e)

    return None


def _id_attributes() -> dict[tuple[str, str], set[str]]:
    """Map every attribute that takes an ID to the names its setter accepts."""
    domains = {}

    for node_type, attributes in ATTRIBUTES.items():
        for attribute in attributes:
            error = _probe(node_type, attribute, _NOT_AN_ID)
            if error is None or "does not accept ID" not in error:
                continue

            domains[(node_type, attribute)] = {
                name for name in _ID_NAMES if _probe(node_type, attribute, name) is None
            }

    return domains


def _id_command_arguments() -> dict[tuple[str, int], set[str]]:
    """Map every (command, argument index) that takes an ID to the names it accepts."""
    domains = {
        (command, index): {member.name for member in domain}
        for command, arguments in _WILDCARD_DOMAINS.items()
        for index, domain in enumerate(arguments)
    }

    for command in _REPORT_COMMANDS:
        cls = NODE_CLASS["Report"]
        parameters = list(inspect.signature(getattr(cls, command)).parameters)
        # positions count deck arguments, which leave out self
        index = parameters.index("reduce") - 1
        domains[(command, index)] = {member.name for member in ReportReduceID}

    return domains


def _id_values_used() -> dict[frozenset[str], set[str]]:
    """Group the ID values the deck writes by the set of values their site accepts."""
    used: dict[frozenset[str], set[str]] = {}

    for (node_type, attribute), domain in ID_ATTRIBUTES.items():
        values = used.setdefault(frozenset(domain), set())
        for used_type, used_attribute, value, _ in USE.assignments:
            if (used_type, used_attribute) == (node_type, attribute):
                values.update(value if isinstance(value, list) else [value])

    for (command, index), domain in ID_COMMAND_ARGUMENTS.items():
        values = used.setdefault(frozenset(domain), set())
        for _, used_command, arguments, _ in USE.commands:
            if used_command == command and index < len(arguments):
                values.add(arguments[index])

    return used


ID_ATTRIBUTES = _id_attributes()
ID_COMMAND_ARGUMENTS = _id_command_arguments()
ID_VALUES_USED = _id_values_used()


def test_deck_uses_every_registered_attribute_and_command():
    registered_attributes = {
        (node_type, name) for node_type, names in ATTRIBUTES.items() for name in names
    }
    registered_commands = {
        (node_type, name)
        for node_type, names in NODE_COMMAND_SECTIONS.items()
        for name in names
    }

    assert not registered_attributes - USE.attributes(), (
        "registered attributes the coverage deck never assigns: "
        f"{sorted(registered_attributes - USE.attributes())}"
    )
    assert not registered_commands - USE.command_names(), (
        "registered commands the coverage deck never calls: "
        f"{sorted(registered_commands - USE.command_names())}"
    )


def test_deck_updates_every_events_attribute_and_command_in_events():
    both_attributes = {
        (node_type, name)
        for node_type, names in ATTRIBUTES.items()
        for name, sections in names.items()
        if sections == SECTION_BOTH
    }
    both_commands = {
        (node_type, name)
        for node_type, names in NODE_COMMAND_SECTIONS.items()
        for name, sections in names.items()
        if sections == SECTION_BOTH
    }

    missing_attributes = (
        both_attributes - USE.attributes(events_only=True) - EXCLUDED_EVENTS_ATTRIBUTES
    )
    missing_commands = both_commands - USE.command_names(events_only=True)

    assert not missing_attributes, (
        f"attributes allowed in EVENTS the deck never updates there: "
        f"{sorted(missing_attributes)}"
    )
    assert not missing_commands, (
        f"commands allowed in EVENTS the deck never calls there: "
        f"{sorted(missing_commands)}"
    )


def test_probe_finds_the_id_attributes():
    # the probe must find at least the attributes the parser knows take an enum;
    # an empty map would make the value check below pass vacuously
    assert ("Regulation", "Measure") in ID_ATTRIBUTES
    assert ID_ATTRIBUTES[("Fuel", "FuelType")] == {
        member.name for member in enum_.FuelTypeID
    }


@pytest.mark.parametrize(
    "site",
    sorted(ID_ATTRIBUTES) + sorted(ID_COMMAND_ARGUMENTS),
    ids=str,
)
def test_deck_uses_every_id_value(site):
    # a site's values count as used wherever the deck writes them at any site
    # accepting the same set, so FuelType need not be spelled out on every node
    domain = ID_ATTRIBUTES.get(site) or ID_COMMAND_ARGUMENTS[site]
    used = ID_VALUES_USED[frozenset(domain)]
    excluded = {value for (*key, value) in EXCLUDED_IDS if tuple(key) == site}

    assert not domain - used - excluded, (
        f"{site} accepts IDs the coverage deck never writes: "
        f"{sorted(domain - used - excluded)}"
    )


def test_exclusions_are_live():
    # a stale exclusion would hide a value or an update the deck could now make
    for node_type, attribute, value in EXCLUDED_IDS:
        domain = ID_ATTRIBUTES[(node_type, attribute)]
        assert value in domain
        assert value not in ID_VALUES_USED[frozenset(domain)]

    for node_type, attribute in EXCLUDED_EVENTS_ATTRIBUTES:
        assert ATTRIBUTES[node_type][attribute] == SECTION_BOTH
        assert (node_type, attribute) not in USE.attributes(events_only=True)


@pytest.mark.slow
def test_invariants():
    check_invariants(run_simulation(DECK_DIR))
