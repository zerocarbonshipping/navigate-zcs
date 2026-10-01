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
