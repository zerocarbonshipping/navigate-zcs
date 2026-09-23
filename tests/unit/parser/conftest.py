# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Deck scaffolding shared by the parser unit tests.

`write_deck` writes `define.inc`, optionally `events.inc`, and a `deck.nav`
wrapping them in DEFINE and EVENTS; `read_deck` writes that deck and parses
it. Both bind `tmp_path` themselves. `define_base` prefixes the DEFINE
include, `events` is the EVENTS include content or None for an empty EVENTS
block, `data_dir` is the assumptions tree, and `parser` reuses a Parser the
caller already holds.

Only a root node keeps what it references alive through the parser's
unreachable-node prune, so a deck exercising a non-root node hangs it under a
top-level `Emission`. That idiom stays in the modules that use it: they build
their deck text inside `@pytest.mark.parametrize`, which is evaluated at
import time, where a fixture cannot be called.
"""

from __future__ import annotations

import pytest

from navigate.parser.parser import Parser

MODEL_DEFINITION = """
ModelDefinition {
    StartDate = "01-01-2026"
}
"""


@pytest.fixture
def write_deck(tmp_path):
    """Write a deck into tmp_path and return its path."""

    def write(define, *, define_base=MODEL_DEFINITION, events=None):
        (tmp_path / "define.inc").write_text(define_base + define)

        events_block = "EVENTS { }\n"
        if events is not None:
            (tmp_path / "events.inc").write_text(events)
            events_block = 'EVENTS { Include "events.inc" }\n'

        deck = tmp_path / "deck.nav"
        deck.write_text('DEFINE { Include "define.inc" }\n' + events_block)
        return deck

    return write


@pytest.fixture
def read_deck(tmp_path, write_deck):
    """Write a deck into tmp_path, parse it, and return the parser."""

    def read(
        define="",
        *,
        define_base=MODEL_DEFINITION,
        events=None,
        data_dir=None,
        parser=None,
    ):
        deck = write_deck(define, define_base=define_base, events=events)

        # no assumptions tree: any unintended pull from the default library fails
        if data_dir is None:
            data_dir = tmp_path / "data"

        if parser is None:
            parser = Parser()

        parser.read_deck(deck, data_dir=data_dir)
        return parser

    return read
