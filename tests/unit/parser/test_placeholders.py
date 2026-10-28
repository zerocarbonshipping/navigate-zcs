# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Which `%NAME%` placeholders a `--set` value fills in, and which it leaves.

A file is filled in as text before the grammar reads it, its comments excepted:
a placeholder in a comment is left as written and needs no value, while a `#`
inside a quoted string opens no comment, so a placeholder after it is filled.
"""

from __future__ import annotations

import pytest

from helpers.parser_decks import emission_holding, variable
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
