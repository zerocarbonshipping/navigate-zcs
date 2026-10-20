# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from navigate.core.dsl import collect_deck_entries

if TYPE_CHECKING:
    from navigate.core.dsl import DeckEntry


class _GeneralNode:
    """Base class of the general nodes: one per deck, declared without a name."""

    # the general node keyword; each general node class sets its own
    type: ClassVar[str]
    # the deck attributes the class's marked setters declare; no commands
    deck_attributes: ClassVar[dict[str, DeckEntry]] = {}
    deck_commands: ClassVar[dict[str, DeckEntry]] = {}

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.deck_attributes, cls.deck_commands = collect_deck_entries(cls)

    def __repr__(self) -> str:
        return f"{type(self).__name__}"
