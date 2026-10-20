# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The DEFINE and EVENTS sections of a deck, and which keywords each one accepts.

A deck holds one DEFINE block, then one EVENTS block; the grammar refuses any
other shape. A node block is read in either section, where EVENTS re-opens a
node DEFINE declared. The other keywords belong to one section: Copy, Import
and the general nodes to DEFINE, Start, Date and End to EVENTS. A keyword in
the wrong section is rejected with its location.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import numpy as np
import pytest

from helpers.parser_decks import FLEET, FUEL, emission_holding, variable, write_library
from navigate.core.enum_ import SectionID
from navigate.exceptions import DeckError
from navigate.parser.parser import Parser

if TYPE_CHECKING:
    from pathlib import Path

DEFINE = SectionID.DEFINE
EVENTS = SectionID.EVENTS

MODEL_DEFINITION = '\nModelDefinition {\n    StartDate = "01-01-2026"\n}\n'

# the keywords of one section, each with a statement using it
SECTION_KEYWORDS = {
    DEFINE: {
        "Copy": 'Copy Variable "v" "w"\n',
        "Import": 'Import Variable "lib"\n',
        "BunkerOptions": "BunkerOptions {\n}\n",
    },
    EVENTS: {"Start": "Start\n", "Date": 'Date "01-01-2030"\n', "End": "End\n"},
}

# a declared Variable a root holds, for the DEFINE keywords to act on
VARIABLE = emission_holding('Variable("v")') + variable(Value=1.0)


def _keyword_cases(section: SectionID) -> list[tuple[str, str]]:
    return [
        (keyword, statement) for keyword, statement in SECTION_KEYWORDS[section].items()
    ]


def _read_nav(tmp_path: Path, nav: str) -> Parser:
    """Write a deck with its own .nav text beside a define.inc, and read it."""
    (tmp_path / "define.inc").write_text(MODEL_DEFINITION)
    deck = tmp_path / "deck.nav"
    deck.write_text(nav)

    parser = Parser()
    parser.read_deck(deck, data_dir=tmp_path / "data")
    return parser


# ── the blocks of a deck ──────────────────────────────────────────────────────


# input:    | EVENTS {
#           | }
#           | DEFINE {
#           |   Include "define.inc"
#           | }
# expected: -> DeckError "In file '.../deck.nav', line 1: ..." (a syntax error:
#              a deck is one DEFINE block followed by one EVENTS block)
@pytest.mark.parametrize(
    "nav",
    [
        'EVENTS {\n}\nDEFINE {\n  Include "define.inc"\n}\n',
        'DEFINE {\n  Include "define.inc"\n}\nDEFINE {\n}\nEVENTS {\n}\n',
        'DEFINE {\n  Include "define.inc"\n}\nEVENTS {\n}\nEVENTS {\n}\n',
        'DEFINE {\n  Include "define.inc"\n}\nEVENTS {\n}\nDEFINE {\n}\n',
        "",
        'DEFINE {\n  Include "define.inc"\n}\n',
        "EVENTS {\n}\n",
    ],
    ids=[
        "events_first",
        "two_defines",
        "two_events",
        "define_after_events",
        "empty_deck",
        "no_events",
        "no_define",
    ],
)
def test_one_define_block_then_one_events_block(tmp_path, nav):
    with pytest.raises(DeckError, match=r"^In file '.*deck\.nav', line \d+:"):
        _read_nav(tmp_path, nav)


# input:    | navigate missing.nav   (the file does not exist)
# expected: -> FileNotFoundError "Unable to locate .../missing.nav."
def test_a_missing_deck_is_named(tmp_path):
    deck = tmp_path / "missing.nav"

    with pytest.raises(
        FileNotFoundError, match=f"^{re.escape(f'Unable to locate {deck}.')}$"
    ):
        Parser().read_deck(deck)


# input:    | DEFINE {
#           |   Include "missing.inc"
#           | }
# expected: -> DeckError "Error in deck file, line 2: Include file
#              '.../missing.inc' not found."
def test_a_missing_include_is_named_with_its_deck_line(tmp_path):
    message = (
        f"Error in deck file, line 2: Include file '{tmp_path / 'missing.inc'}' "
        "not found."
    )

    with pytest.raises(DeckError, match=f"^{re.escape(message)}$"):
        _read_nav(tmp_path, 'DEFINE {\n  Include "missing.inc"\n}\nEVENTS {\n}\n')


# input:    | DEFINE {
#           |   Include "sub/define.inc"      (or the same path written absolute)
#           | }
# expected: -> sub/define.inc is read next to the deck: StartDate 01-01-2030 is the
#              first date
@pytest.mark.parametrize(
    "include",
    ["sub/define.inc", "{tmp_path}/sub/define.inc"],
    ids=["relative_to_the_deck", "absolute"],
)
def test_an_include_path(tmp_path, include):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "define.inc").write_text(
        'ModelDefinition {\n    StartDate = "01-01-2030"\n}\n'
    )
    include = include.format(tmp_path=tmp_path)

    parser = _read_nav(
        tmp_path, f'DEFINE {{\n  Include "{include}"\n}}\nEVENTS {{\n}}\n'
    )

    assert parser.dates[0] == np.datetime64("2030-01-01")


# ── keywords by section ───────────────────────────────────────────────────────


# input:    | Fleet "fleet" { ... }   in DEFINE, then
#           | Fleet "fleet" { Memory = 0.3 }   in EVENTS after Start
# expected: -> accepted in both; EVENTS re-opens the same Fleet "fleet" instead
#              of making a new one, so its Memory reads 0.3 at the start date
def test_a_node_block_is_accepted_in_both_sections(read_deck):
    parser = read_deck(FLEET + FUEL, events='Start\nFleet "fleet" { Memory = 0.3 }\n')
    node = parser.nodes.fleets["fleet"]

    parser.read_events(parser.dates[0])

    assert parser.nodes.fleets == {"fleet": node}
    assert node.memory.get() == 0.3


# input:    | e.g. Copy Variable "v" "w"   in DEFINE,  or  Start   in EVENTS
# expected: -> the deck reads
@pytest.mark.parametrize(
    ("section", "keyword", "statement"),
    [
        (section, keyword, statement)
        for section in (DEFINE, EVENTS)
        for keyword, statement in _keyword_cases(section)
    ],
    ids=lambda value: value if isinstance(value, str) and " " not in value else None,
)
def test_a_keyword_is_accepted_in_its_section(
    tmp_path, read_deck, section, keyword, statement
):
    data_dir = write_library(
        tmp_path / "data", "Variable", {"lib": variable("lib", Value=1)}
    )
    deck = (
        {"define": VARIABLE + statement} if section == DEFINE else {"events": statement}
    )

    read_deck(**deck, data_dir=data_dir)


# input:    | EVENTS: Start
#           |         Date "01-01-2030"
# expected: -> dates = [2026-01-01 (the StartDate), 2030-01-01]
def test_a_timeline_read_in_events_dates_the_deck(read_deck):
    parser = read_deck(events='Start\nDate "01-01-2030"\n')

    np.testing.assert_array_equal(
        parser.dates, np.array(["2026-01-01", "2030-01-01"], dtype="datetime64[D]")
    )


# input:    | e.g. Copy Variable "v" "w"   in EVENTS,  or  Start   in DEFINE
# expected: -> DeckError "Error in deck file, line 2, include file
#              '.../events.inc', line 1: 'Copy' is not allowed in the EVENTS
#              section."
@pytest.mark.parametrize(
    ("section", "keyword", "statement"),
    [
        (section, keyword, statement)
        for section in (DEFINE, EVENTS)
        for keyword, statement in _keyword_cases(
            EVENTS if section == DEFINE else DEFINE
        )
    ],
    ids=lambda value: value if isinstance(value, str) and " " not in value else None,
)
def test_a_keyword_is_rejected_outside_its_section(
    tmp_path, read_deck, section, keyword, statement
):
    if section == DEFINE:
        location = f"line 1, include file '{tmp_path / 'define.inc'}', line 5"
        deck = {"define": statement}
    else:
        location = f"line 2, include file '{tmp_path / 'events.inc'}', line 1"
        deck = {"events": statement}

    message = (
        f"Error in deck file, {location}: '{keyword}' is not allowed in the "
        f"{section.name} section."
    )

    with pytest.raises(DeckError, match=f"^{re.escape(message)}$"):
        read_deck(**deck)


# input:    | Foo "x" {
#           | }
# expected: -> DeckError "Error in deck file, line 1, include file
#              '.../define.inc', line 5: 'Foo' is not a recognized node type."
@pytest.mark.parametrize(
    ("deck", "location"),
    [
        ({"define": 'Foo "x" {\n}\n'}, "line 1, include file '{define}', line 5"),
        ({"define": "Foo {\n}\n"}, "line 1, include file '{define}', line 5"),
        (
            {"events": 'Start\nFoo "x" {\n}\n'},
            "line 2, include file '{events}', line 2",
        ),
    ],
    ids=["named", "general", "in_events"],
)
def test_an_unknown_node_type_is_rejected(tmp_path, read_deck, deck, location):
    location = location.format(
        define=tmp_path / "define.inc", events=tmp_path / "events.inc"
    )
    message = f"Error in deck file, {location}: 'Foo' is not a recognized node type."

    with pytest.raises(DeckError, match=f"^{re.escape(message)}$"):
        read_deck(**deck)
