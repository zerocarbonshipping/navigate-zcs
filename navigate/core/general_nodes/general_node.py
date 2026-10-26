# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""GeneralNode, the base class of the general nodes the parser builds from a deck."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from navigate.core.dsl import collect_deck_entries

if TYPE_CHECKING:
    from navigate.core.dsl import DeckEntry


class GeneralNode:
    """Base class of the general nodes: at most one per deck, declared unnamed."""

    # the general node keyword; each general node class sets its own
    type: ClassVar[str]
    # the deck attributes the marked setters declare
    deck_attributes: ClassVar[dict[str, DeckEntry]] = {}

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.deck_attributes, _ = collect_deck_entries(cls)

    def __repr__(self) -> str:
        return self.type
