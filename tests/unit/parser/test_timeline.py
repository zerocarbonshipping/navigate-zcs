# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The EVENTS timeline: which dates exist and which statements run at each.

`Start` and `Date` open an event that queues the statements after it, and
`read_events` replays a date's events in order. The start date is
always on the timeline, and the `Start` events run before anything dated on
it. Dates must rise within each include file, may not precede the start date,
and a default file may not touch the timeline.
"""

from __future__ import annotations

import numpy as np
import pytest

from helpers.parser_decks import FLEET, FUEL, line_of, write_library
from navigate.exceptions import DeckFormatError
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
# expected: -> 2026-01-01 reads 0.4, 2028-01-01 reads 0.3, then the timeline ends
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
#           | End
# expected: -> steps 2026-01-01 (still 0.5) and 2027-01-01 (0.3)
def test_the_start_date_is_on_the_timeline_without_a_start_statement(read_deck):
    events = 'Date "01-01-2027"\n' + _efficiency(0.3) + "End\n"

    parser = read_deck(FLEET + FUEL, events=events)

    assert _run(parser) == [("2026-01-01", 0.5), ("2027-01-01", 0.3)]


# input:    | Date "01-01-2026"   Converter "propulsion" { Efficiency = 0.3 }   End
#           | Start               Converter "propulsion" { Efficiency = 0.4 }   End
# expected: -> one step, 2026-01-01 reading 0.3: Start sets 0.4 first, then
#              the dated event sets 0.3
def test_start_events_run_before_events_dated_on_the_start_date(read_deck):
    # the dated event comes first in the file, but the Start one replays first
    events = (
        'Date "01-01-2026"\n'
        + _efficiency(0.3)
        + "End\nStart\n"
        + _efficiency(0.4)
        + "End\n"
    )

    parser = read_deck(FLEET + FUEL, events=events)

    assert _run(parser) == [("2026-01-01", 0.3)]


# input:    | Date "01/01/2027"   (also "01-01-2027" and "2027-01-01")
# expected: -> dates are 2026-01-01 and 2027-01-01
@pytest.mark.parametrize("date", ["01-01-2027", "01/01/2027", "2027-01-01"])
def test_a_date_statement_takes_each_date_format(read_deck, date):
    parser = read_deck(FLEET + FUEL, events=f'Date "{date}"\nEnd\n')

    assert list(parser.dates) == [
        np.datetime64("2026-01-01"),
        np.datetime64("2027-01-01"),
    ]


# input:    | events_0.inc: Date "01-01-2028"   Efficiency = 0.2
#           | events_1.inc: Date "01-01-2027"   Efficiency = 0.3
# expected: -> steps 2026 (0.5), 2027 (0.3), 2028 (0.2)
def test_dates_of_separate_files_merge_into_one_sorted_timeline(tmp_path):
    parser = _read_with_events(
        tmp_path,
        'Date "01-01-2028"\n' + _efficiency(0.2) + "End\n",
        'Date "01-01-2027"\n' + _efficiency(0.3) + "End\n",
    )

    assert _run(parser) == [
        ("2026-01-01", 0.5),
        ("2027-01-01", 0.3),
        ("2028-01-01", 0.2),
    ]


# input:    | Date "01-01-2028"
#           | Date "01-01-2027"   (or "01-01-2028" again)
# expected: -> DeckFormatError "...events.inc', line 2: Dates must be ordered
#              chronologically within individual include files."
@pytest.mark.parametrize(
    "second", ["01-01-2027", "01-01-2028"], ids=["earlier", "equal"]
)
def test_a_date_not_after_the_previous_one_in_a_file_is_rejected(
    tmp_path, read_deck, second
):
    events = f'Date "01-01-2028"\nDate "{second}"\nEnd\n'

    with pytest.raises(
        DeckFormatError,
        match=(
            r"^Error in deck file, line 2, include file '.*events\.inc', line 2: "
            r"Dates must be ordered chronologically within individual include "
            r"files\.$"
        ),
    ):
        read_deck(FLEET + FUEL, events=events)


# input:    | StartDate = "01-01-2026"   and in EVENTS   Date "01-01-2025"
# expected: -> DeckFormatError "Inconsistent timeline detected: ... Date
#              '2025-01-01' is before start date '2026-01-01' ..."
def test_a_date_before_the_start_date_is_rejected(tmp_path, read_deck):
    events = 'Date "01-01-2025"\nEnd\n'

    with pytest.raises(DeckFormatError) as error:
        read_deck(FLEET + FUEL, events=events)

    events_file = tmp_path / "events.inc"
    assert str(error.value) == (
        "Inconsistent timeline detected:\n"
        f"\t- NAV file, line 2, include file '{events_file}', line 1: Date "
        "'2025-01-01' is before start date '2026-01-01'\n"
        "All defined dates must be later than the start date."
    )


# input:    | Date "01-01-2027"
#           | Start
# expected: -> DeckFormatError "...events.inc', line 2: Unable to start a new
#              timeline while one is in progress."
def test_a_start_inside_an_open_timeline_is_rejected(read_deck):
    events = 'Date "01-01-2027"\nStart\nEnd\n'

    with pytest.raises(
        DeckFormatError,
        match=(
            r"events\.inc', line 2: Unable to start a new timeline while one is "
            r"in progress\.$"
        ),
    ):
        read_deck(FLEET + FUEL, events=events)


# input:    | EVENTS: Date "01-01-2027"   Efficiency = Variable("lib")
#           | defaults/installation/Variable/lib.inc:
#           |   Date "01-01-2030"
#           |   Variable "lib" { Value = 0.4 }
# expected: -> DeckFormatError "Error while retrieving default, ... lib.inc',
#              line 1: Unable to alter timeline while retrieving default nodes."
def test_a_default_file_touching_the_timeline_is_rejected(tmp_path, read_deck):
    # the EVENTS reference pulls the Variable when its date comes up, so the
    # default file is read in EVENTS, where Date is a known keyword
    library = write_library(
        tmp_path / "data",
        "Variable",
        installation={"lib": 'Date "01-01-2030"\nVariable "lib" { Value = 0.4 }\n'},
    )
    events = 'Date "01-01-2027"\n' + _efficiency('Variable("lib")') + "End\n"
    parser = read_deck(FLEET + FUEL, events=events, data_dir=library)

    library_file = tmp_path / "data/defaults/installation/Variable/lib.inc"
    with pytest.raises(DeckFormatError) as error:
        parser.read_events(parser.dates[1])

    assert str(error.value) == (
        f"Error while retrieving default, include file '{library_file}', line "
        f"{line_of(library_file, 'Date')}: Unable to alter timeline while "
        "retrieving default nodes."
    )
