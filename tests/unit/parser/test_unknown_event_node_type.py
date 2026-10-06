# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""An unknown node type queued in EVENTS is rejected when the deck is read."""

from __future__ import annotations

import pytest

from navigate.exceptions import DeckKeywordError

EVENTS = """
Start
Date "01-01-2027"
Foo "x" {
    A = 1
}
End
"""

NAMED_GENERAL_NODE = """
ModelDefinition "x" {
}
"""

EVENTS_NAMED_GENERAL_NODE = f"""
Start
Date "01-01-2027"
{NAMED_GENERAL_NODE.strip()}
End
"""


def test_an_unknown_node_type_queued_in_events_is_rejected(read_deck):
    with pytest.raises(
        DeckKeywordError,
        match=(
            r"^Error in deck file, line 2, include file '.*events\.inc', line 4: \n"
            r"'Foo' is not a recognized keyword\. "
            r"Check the attributes and commands for spelling$"
        ),
    ):
        read_deck(events=EVENTS)


@pytest.mark.parametrize(
    ("define", "events", "location"),
    [
        (
            "",
            EVENTS_NAMED_GENERAL_NODE,
            r"line 2, include file '.*events\.inc', line 4",
        ),
        (NAMED_GENERAL_NODE, None, r"line 1, include file '.*define\.inc', line 6"),
    ],
    ids=["events", "define"],
)
def test_a_named_general_node_is_rejected(read_deck, define, events, location):
    with pytest.raises(
        DeckKeywordError,
        match=(
            rf"^Error in deck file, {location}: "
            r"'ModelDefinition' is a general node and is declared without a name\.$"
        ),
    ):
        read_deck(define, events=events)
