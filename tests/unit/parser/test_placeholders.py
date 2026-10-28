# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Where a `--set` value fills in its `%NAME%` placeholder, and where it does not.

Every file a run reads is filled in as text before the grammar reads it: the
deck, so a value can choose the file an Include reads, and a default the library
supplies. A placeholder in a comment is left as written, so it needs no value; a
`#` inside a quoted string opens no comment, so a placeholder after it is filled.
"""

from __future__ import annotations

import pytest

from helpers.parser_decks import emission_holding, variable, write_library
from navigate.parser.parser import Parser

HOST = emission_holding('Variable("v")')


@pytest.fixture
def parse(tmp_path):
    """Parse a deck with the given --set values against the tree at tmp_path/data."""

    def read(deck, params):
        parser = Parser()
        parser.read_deck(deck, data_dir=tmp_path / "data", params=params)
        return parser

    return read


# input:    | DEFINE { Include "define.inc"  Include "%scenario%.inc" }
#           | --set scenario=high; high.inc sets v = 2.0, low.inc v = 1.0
# expected: -> v reads 2.0, from high.inc
def test_a_value_chooses_the_file_an_include_reads(tmp_path, parse):
    (tmp_path / "define.inc").write_text(
        'ModelDefinition {\n    StartDate = "01-01-2026"\n}\n'
    )
    (tmp_path / "high.inc").write_text(HOST + variable(Value=2.0))
    (tmp_path / "low.inc").write_text(HOST + variable(Value=1.0))
    deck = tmp_path / "deck.nav"
    deck.write_text(
        'DEFINE {\n    Include "define.inc"\n    Include "%scenario%.inc"\n}\n'
        "EVENTS { }\n"
    )

    parser = parse(deck, {"scenario": "high"})

    assert parser.nodes.variables["v"].get() == 2.0


# input:    | Emission "e" { GlobalWarmingPotential = Variable("v") }
#           | --set value=4.5; defaults/Variable/v.inc: Value = %value%
# expected: -> v is pulled from the library and reads 4.5
def test_a_value_fills_a_default_pulled_from_the_library(tmp_path, write_deck, parse):
    write_library(tmp_path / "data", "Variable", {"v": variable(Value="%value%")})

    parser = parse(write_deck(HOST), {"value": "4.5"})

    assert parser.nodes.variables["v"].get() == 4.5


# input:    | Variable "v" { Value = 1.0 }
#           | # scaled by %undefined% later
#           | no --set values
# expected: -> the deck is read and v reads 1.0
def test_a_placeholder_in_a_comment_needs_no_value(write_deck, parse):
    define = HOST + variable(Value=1.0) + "# scaled by %undefined% later\n"

    parser = parse(write_deck(define), {})

    assert parser.nodes.variables["v"].get() == 1.0


# input:    | Emission "e" { GlobalWarmingPotential = Variable("v#%n%") }
#           | Variable "v#%n%" { Value = 2.0 }   with --set n=1
# expected: -> the Variable is named "v#1": the '#' in the string opened no comment
def test_a_hash_inside_a_string_hides_no_placeholder(write_deck, parse):
    define = emission_holding('Variable("v#%n%")') + variable("v#%n%", Value=2.0)

    parser = parse(write_deck(define), {"n": "1"})

    assert list(parser.nodes.variables) == ["v#1"]
