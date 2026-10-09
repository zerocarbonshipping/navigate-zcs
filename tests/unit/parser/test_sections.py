# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The DEFINE and EVENTS sections of a deck, and which keywords each one accepts.

A deck holds one DEFINE block, then one EVENTS block. `KEYWORD_SECTIONS` lists
the sections every keyword may appear in; each keyword is tried in every
section, so a keyword added to the table is covered without a new case here.

A keyword is accepted where the parser registers what it declares, read
through the parser's own section walk; a full deck read would also run the
required-attribute and reachability checks, which an empty declaration fails
for reasons that are not the keyword's. A keyword is rejected where a deck
read stops at it, with its location.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import numpy as np
import pytest

from navigate.core.enum_ import SimulationSectionID
from navigate.exceptions import DeckFormatError, DeckKeywordError
from navigate.parser._keywords import (
    DATE,
    END,
    GENERAL_NODE_GROUP,
    KEYWORD_SECTIONS,
    NODE_GROUP,
    START,
    node_group,
)
from navigate.parser._lark_parser import parse_include_content
from navigate.parser.parser import Parser

if TYPE_CHECKING:
    from pathlib import Path

DEFINE = SimulationSectionID.DEFINE
EVENTS = SimulationSectionID.EVENTS

MODEL_DEFINITION = '\nModelDefinition {\n    StartDate = "01-01-2026"\n}\n'

SECTION_ORDER = (
    "Each section can only be defined once and must be read in the order "
    "DEFINE, EVENTS."
)
BOTH_SECTIONS = "Both a DEFINE and an EVENTS block must be defined in the deck."

# the text of one use of each timeline keyword
TIMELINE_STATEMENT = {START: "Start\n", DATE: 'Date "01-01-2030"\n', END: "End\n"}


def _statement(keyword: str) -> str:
    """Return a minimal statement using a keyword."""
    if keyword in NODE_GROUP:
        return f'{keyword} "n" {{\n}}\n'
    if keyword in GENERAL_NODE_GROUP:
        return f"{keyword} {{\n}}\n"
    return TIMELINE_STATEMENT[keyword]


def _keyword_cases(allowed: bool) -> list[tuple[str, SimulationSectionID]]:
    return [
        (keyword, section)
        for keyword, sections in KEYWORD_SECTIONS.items()
        for section in (DEFINE, EVENTS)
        if (section in sections) == allowed
    ]


def _walk(parser: Parser, section: SimulationSectionID, text: str) -> None:
    """Read include text into a section the way a deck's block reads it."""
    parser._begin_reading_section(section)
    parser._process_statements(parse_include_content(text, file=f"{section.name}.inc"))
    parser._end_reading_section(section)


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
# expected: -> DeckFormatError "...: Each section can only be defined once and must
#              be read in the order DEFINE, EVENTS."
@pytest.mark.parametrize(
    "nav",
    [
        'EVENTS {\n}\nDEFINE {\n  Include "define.inc"\n}\n',
        'DEFINE {\n  Include "define.inc"\n}\nDEFINE {\n}\nEVENTS {\n}\n',
        'DEFINE {\n  Include "define.inc"\n}\nEVENTS {\n}\nEVENTS {\n}\n',
        'DEFINE {\n  Include "define.inc"\n}\nEVENTS {\n}\nDEFINE {\n}\n',
    ],
    ids=["events_first", "two_defines", "two_events", "define_after_events"],
)
def test_one_define_block_then_one_events_block(tmp_path, nav):
    # the deck line the message names is not pinned: it is the last directive
    # read before the offending block, not the block itself
    with pytest.raises(DeckFormatError, match=rf": {re.escape(SECTION_ORDER)}$"):
        _read_nav(tmp_path, nav)


# input:    | DEFINE {
#           |   Include "define.inc"
#           | }                          (no EVENTS block)
# expected: -> DeckFormatError "Both a DEFINE and an EVENTS block must be defined in
#              the deck."
@pytest.mark.parametrize(
    "nav",
    ["", 'DEFINE {\n  Include "define.inc"\n}\n', "EVENTS {\n}\n"],
    ids=["empty_deck", "no_events", "no_define"],
)
def test_a_deck_has_both_blocks(tmp_path, nav):
    with pytest.raises(DeckFormatError, match=f"^{re.escape(BOTH_SECTIONS)}$"):
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
# expected: -> FileNotFoundError "Error in deck file, line 2: Include file
#              '.../missing.inc' not found."
def test_a_missing_include_is_named_with_its_deck_line(tmp_path):
    message = (
        f"Error in deck file, line 2: Include file '{tmp_path / 'missing.inc'}' "
        "not found."
    )

    with pytest.raises(FileNotFoundError, match=f"^{re.escape(message)}$"):
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


# input:    | e.g. Fleet "n" { }   in DEFINE, then again in EVENTS
# expected: -> accepted in both; EVENTS re-opens the same Fleet "n" instead of
#              making a new one
@pytest.mark.parametrize(("keyword", "section"), _keyword_cases(allowed=True))
def test_a_keyword_is_accepted_in_its_sections(keyword, section):
    parser = Parser()
    statement = _statement(keyword)

    if keyword in NODE_GROUP:
        # EVENTS creates no node, so it re-opens one DEFINE declared
        _walk(parser, DEFINE, statement)
        node = node_group(parser.nodes, keyword)["n"]
        if section == EVENTS:
            _walk(parser, EVENTS, statement)

        assert node_group(parser.nodes, keyword) == {"n": node}
        assert node.type == keyword

    elif keyword in GENERAL_NODE_GROUP:
        _walk(parser, section, statement)

        general_node = getattr(
            parser._declared_general_nodes, GENERAL_NODE_GROUP[keyword]
        )
        assert general_node is not None

    else:
        _walk(parser, DEFINE, "")
        _walk(parser, section, "Start\n" + statement if keyword != START else statement)


# input:    | EVENTS: Start
#           |         Date "01-01-2030"
#           |         End
# expected: -> dates = [2026-01-01 (the StartDate), 2030-01-01]
def test_a_timeline_read_in_events_dates_the_deck(read_deck):
    parser = read_deck(events='Start\nDate "01-01-2030"\nEnd\n')

    np.testing.assert_array_equal(
        parser.dates, np.array(["2026-01-01", "2030-01-01"], dtype="datetime64[D]")
    )


# input:    | e.g. Fuel "n" { }   in EVENTS,  or  Start   in DEFINE
# expected: -> DeckKeywordError "Error in deck file, line 2, include file
#              '.../events.inc', line 1: 'Fuel' is not an allowed keyword in
#              section EVENTS."
@pytest.mark.parametrize(("keyword", "section"), _keyword_cases(allowed=False))
def test_a_keyword_is_rejected_outside_its_sections(
    tmp_path, read_deck, keyword, section
):
    # an EVENTS statement read before any Start is processed on the spot
    if section == DEFINE:
        location = f"line 1, include file '{tmp_path / 'define.inc'}', line 5"
        deck = {"define": _statement(keyword)}
    else:
        location = f"line 2, include file '{tmp_path / 'events.inc'}', line 1"
        deck = {"events": _statement(keyword)}

    message = (
        f"Error in deck file, {location}: '{keyword}' is not an allowed keyword in "
        f"section {section.name}."
    )

    with pytest.raises(DeckKeywordError, match=f"^{re.escape(message)}$"):
        read_deck(**deck)


# input:    | Foo "x" {
#           | }
# expected: -> DeckKeywordError "Error in deck file, line 1, include file
#              '.../define.inc', line 5: 'Foo' is not a recognized keyword. Check the
#              attributes and commands for spelling"
@pytest.mark.parametrize(
    ("deck", "location"),
    [
        ({"define": 'Foo "x" {\n}\n'}, "line 1, include file '{define}', line 5"),
        ({"define": "Foo {\n}\n"}, "line 1, include file '{define}', line 5"),
        # a declaration queued in an event is checked when it is queued
        (
            {"events": 'Start\nFoo "x" {\n}\nEnd\n'},
            "line 2, include file '{events}', line 2",
        ),
    ],
    ids=["named", "general", "queued_in_events"],
)
def test_an_unknown_keyword_is_rejected(tmp_path, read_deck, deck, location):
    location = location.format(
        define=tmp_path / "define.inc", events=tmp_path / "events.inc"
    )
    message = (
        f"Error in deck file, {location}: \n'Foo' is not a recognized keyword. "
        "Check the attributes and commands for spelling"
    )

    with pytest.raises(DeckKeywordError, match=f"^{re.escape(message)}$"):
        read_deck(**deck)
