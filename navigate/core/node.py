# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Node, the base class of every DSL node the parser builds from a deck."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, final

from navigate.core.dsl import collect_deck_entries

if TYPE_CHECKING:
    from navigate.core.dsl import DeckEntries
    from navigate.util.types_ import DateArray, FloatArray


class Node:
    """Base class of the DSL nodes: a name and a type tag."""

    # the node type keyword; each concrete node class sets its own
    type: ClassVar[str]
    # the deck attributes and commands the class's marked methods declare
    deck_attributes: ClassVar[DeckEntries] = {}
    deck_commands: ClassVar[DeckEntries] = {}

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.deck_attributes, cls.deck_commands = collect_deck_entries(cls)

    def __init__(self, name: str) -> None:
        self.name: str = name

    def __repr__(self) -> str:
        return f'{self.type}("{self.name}")'

    @final
    def initialize(self) -> None:
        """Fill the defaults of the node, from the deck as first read."""
        self.apply_defaults()
        self.reinitialize()

    @final
    def reinitialize(self) -> None:
        """Re-fill what a re-read of the deck can invalidate."""
        self.apply_command_defaults()

    def apply_defaults(self) -> None:
        """
        Fill values whose default is derived from another attribute.

        A default belongs here when it is read off the size or the value of
        another attribute rather than being a constant. Runs once, after the
        DEFINE block has been read.
        """

    def apply_command_defaults(self) -> None:
        """
        Fill and resolve the dictionaries the DSL commands write.

        Fills the entries `initialize_dependencies` cannot seed with their
        default, such as the keys a command creates, and resolves the
        dictionaries into whatever internal form the node reads them
        through. Runs after the DEFINE block and again after every event
        read, because a SECTION_BOTH command can create a key mid-run.
        """

    def check_requirements(self) -> None:
        """
        Raise where an attribute the node cannot run without is unassigned.

        Holds what the required-attribute mark cannot say: an empty list, or an
        attribute required only under another. Run by the validate sweep of
        `core/lifecycle.py` after the defaults, after DEFINE and after every event.
        """

    def check_consistency(self) -> None:
        """
        Raise where attributes contradict each other, warn where one is unused.

        Run by the validate sweep of `core/lifecycle.py` after the defaults,
        after DEFINE and after every event, as most attributes are SECTION_BOTH.
        """

    def check_dynamic_consistency(self, times: FloatArray, dates: DateArray) -> None:
        """
        Raise where time-varying attributes contradict each other over the future.

        `check_consistency` sees only a node's cached values, so two attributes
        that agree now but cross later go unchecked; this hook sees the
        remaining timeline instead. Runs once per time step, before the
        expectations are calculated, called by the simulation rather than the
        parser: it is not part of the lifecycle sweeps.

        Parameters
        ----------
        times
            Remaining simulation times, in days since the start, as `.get()`
            takes them.
        dates
            Dates matching `times`, one per element.
        """
