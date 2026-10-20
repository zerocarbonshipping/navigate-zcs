# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The EVENTS timeline: which dates exist and which statements run at each.

Every `Start` and `Date` read is a time step, and a node block applies at the
last date read before it in its file; `read_events` replays a date's blocks in
order. The start date is always on the timeline, and the `Start` blocks run
before anything dated on it. Dates need no order, may not precede the start
date, and a default file may not hold one.
"""

from __future__ import annotations

import numpy as np
import pytest

from helpers.parser_decks import FLEET, FUEL, line_of, write_library
from navigate.exceptions import DeckError
from navigate.parser.parser import Parser


def _efficiency(value):
    return f'Converter "propulsion" {{ Efficiency = {value} }}\n'


def _run(parser):
    """Step through the timeline, returning each date and the efficiency after it."""
    converter = parser.nodes.converters["propulsion"]
    steps = []
    for date in parser.dates:
        parser.read_events(date)
        steps.append((str(date), converter.efficiency.get()))
    return steps


def _read_with_events(tmp_path, *events_files):
    """Read FLEET + FUEL with one EVENTS include per given file content."""
    (tmp_path / "define.inc").write_text(
        'ModelDefinition {\n    StartDate = "01-01-2026"\n}\n' + FLEET + FUEL
    )
    includes = ""
    for index, content in enumerate(events_files):
        (tmp_path / f"events_{index}.inc").write_text(content)
        includes += f'    Include "events_{index}.inc"\n'
    deck = tmp_path / "deck.nav"
    deck.write_text(f'DEFINE {{ Include "define.inc" }}\nEVENTS {{\n{includes}}}\n')

    parser = Parser()
    parser.read_deck(deck, data_dir=tmp_path / "data")
    return parser


# input:    | Start
#           | Converter "propulsion" { Efficiency = 0.4 }
#           | Date "01-01-2028"
#           | Converter "propulsion" { Efficiency = 0.3 }
#           | End
# expected: -> 2026-01-01 reads 0.4, 2028-01-01 reads 0.3; the End of older
#              decks is accepted and changes nothing
def test_each_date_replays_its_events_in_order(read_deck):
    events = (
        "Start\n"
        + _efficiency(0.4)
        + 'Date "01-01-2028"\n'
        + _efficiency(0.3)
        + "End\n"
    )

    parser = read_deck(FLEET + FUEL, events=events)

    assert _run(parser) == [("2026-01-01", 0.4), ("2028-01-01", 0.3)]


# input:    | Date "01-01-2027"
#           | Converter "propulsion" { Efficiency = 0.3 }
# expected: -> steps 2026-01-01 (still 0.5) and 2027-01-01 (0.3)
def test_the_start_date_is_on_the_timeline_without_a_start_statement(read_deck):
    events = 'Date "01-01-2027"\n' + _efficiency(0.3)

    parser = read_deck(FLEET + FUEL, events=events)

    assert _run(parser) == [("2026-01-01", 0.5), ("2027-01-01", 0.3)]


# input:    | Date "01-01-2026"   Converter "propulsion" { Efficiency = 0.3 }
#           | Start               Converter "propulsion" { Efficiency = 0.4 }
# expected: -> one step, 2026-01-01 reading 0.3: Start sets 0.4 first, then
#              the dated event sets 0.3
def test_start_events_run_before_events_dated_on_the_start_date(read_deck):
    # the dated event comes first in the file, but the Start one replays first
    events = 'Date "01-01-2026"\n' + _efficiency(0.3) + "Start\n" + _efficiency(0.4)

    parser = read_deck(FLEET + FUEL, events=events)

    assert _run(parser) == [("2026-01-01", 0.3)]


# input:    | Date "01/01/2027"   (also "01-01-2027" and "2027-01-01")
# expected: -> dates are 2026-01-01 and 2027-01-01
@pytest.mark.parametrize("date", ["01-01-2027", "01/01/2027", "2027-01-01"])
def test_a_date_statement_takes_each_date_format(read_deck, date):
    parser = read_deck(FLEET + FUEL, events=f'Date "{date}"\n')

    assert list(parser.dates) == [
        np.datetime64("2026-01-01"),
        np.datetime64("2027-01-01"),
    ]


# input:    | events_0.inc: Date "01-01-2028"   Efficiency = 0.2
#           |               Date "01-01-2027"   Efficiency = 0.3
#           | events_1.inc: Date "01-01-2029"   Efficiency = 0.1
# expected: -> steps 2026 (0.5), 2027 (0.3), 2028 (0.2), 2029 (0.1): the dates
#              of every file merge into one sorted timeline, in any order
def test_dates_of_separate_files_merge_into_one_sorted_timeline(tmp_path):
    parser = _read_with_events(
        tmp_path,
        'Date "01-01-2028"\n'
        + _efficiency(0.2)
        + 'Date "01-01-2027"\n'
        + _efficiency(0.3),
        'Date "01-01-2029"\n' + _efficiency(0.1),
    )

    assert _run(parser) == [
        ("2026-01-01", 0.5),
        ("2027-01-01", 0.3),
        ("2028-01-01", 0.2),
        ("2029-01-01", 0.1),
    ]


# input:    | StartDate = "01-01-2026"   and in EVENTS   Date "01-01-2025"
# expected: -> DeckError "Inconsistent timeline detected: ... Date '2025-01-01'
#              is before start date '2026-01-01' ..."
def test_a_date_before_the_start_date_is_rejected(read_deck):
    with pytest.raises(DeckError) as error:
        read_deck(FLEET + FUEL, events='Date "01-01-2025"\n')

    assert str(error.value) == (
        "Inconsistent timeline detected:\n"
        "\t- Date '2025-01-01' is before start date '2026-01-01'\n"
        "All defined dates must be later than the start date."
    )


# input:    | Converter "propulsion" { Efficiency = 0.3 }
#           | Date "01-01-2027"
# expected: -> DeckError "...events.inc', line 1: A node block under EVENTS must
#              follow a Start or Date keyword."
def test_a_block_before_any_date_is_rejected(read_deck):
    events = _efficiency(0.3) + 'Date "01-01-2027"\n'

    with pytest.raises(
        DeckError,
        match=(
            r"events\.inc', line 1: A node block under EVENTS must follow a Start "
            r"or Date keyword\.$"
        ),
    ):
        read_deck(FLEET + FUEL, events=events)


# input:    | EVENTS: Date "01-01-2027"   Efficiency = Variable("lib")
#           | defaults/Variable/lib.inc:
#           |   Date "01-01-2030"
#           |   Variable "lib" { Value = 0.4 }
# expected: -> DeckError "... lib.inc', line 1: 'Date' is not allowed in the
#              DEFINE section." when the deck is read: a library file is read
#              under DEFINE, whichever section references it
def test_a_default_file_touching_the_timeline_is_rejected(tmp_path, read_deck):
    library = write_library(
        tmp_path / "data",
        "Variable",
        {"lib": 'Date "01-01-2030"\nVariable "lib" { Value = 0.4 }\n'},
    )
    events = 'Date "01-01-2027"\n' + _efficiency('Variable("lib")')

    library_file = tmp_path / "data/defaults/Variable/lib.inc"
    with pytest.raises(DeckError) as error:
        read_deck(FLEET + FUEL, events=events, data_dir=library)

    assert str(error.value) == (
        f"Error in deck file, line 2, include file '{library_file}', line "
        f"{line_of(library_file, 'Date')}: 'Date' is not allowed in the DEFINE "
        "section."
    )
