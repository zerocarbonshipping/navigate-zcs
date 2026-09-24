# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Node, the base class of every DSL node the parser builds from a deck."""

from __future__ import annotations

from typing import TYPE_CHECKING, final

from navigate.core.node_type import TypeCheckMixin

if TYPE_CHECKING:
    from navigate.parser._commands import CommandReference


class Node(TypeCheckMixin):
    """Base class of the DSL nodes: a name, a type tag and a command queue."""

    def __init__(self, name: str, type_: str) -> None:
        super().__init__(type_)

        self.name: str = name  # name the deck gives the node

        # internal variables -----------------------------------------------------------
        self.command_references: list[CommandReference] = []  # parser command queue

    def __repr__(self) -> str:
        return f'{self.type}("{self.name}")'

    def add_command_reference(self, command_reference: CommandReference) -> None:
        """
        Queue a command reference for the parser to execute.

        Parameters
        ----------
        command_reference
            The reference to queue.
        """
        self.command_references.append(command_reference)

    def clear_command_references(self) -> None:
        """Empty the command-reference queue."""
        self.command_references = []

    @final
    def initialize(self) -> None:
        """Bring the node to a usable state, from the deck as first read."""
        self.check_requirements()
        self.apply_defaults()
        self.reinitialize()

    @final
    def reinitialize(self) -> None:
        """Re-run everything a re-read of the deck can invalidate."""
        self.apply_command_defaults()
        self.check_consistency()

    def check_requirements(self) -> None:
        """
        Raise where an attribute the node cannot run without is unassigned.

        Runs once, after the DEFINE block has been read.
        """

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

        Fills the unassigned entries of the dictionaries
        'initialize_dependencies' seeds, and resolves them into whatever
        internal form the node reads them through. Runs after the DEFINE
        block and again after every event read, because a SECTION_BOTH
        command can create a key mid-run.
        """

    def check_consistency(self) -> None:
        """
        Raise where attributes contradict each other, warn where one is unused.

        Runs after the DEFINE block and again after every event read, because
        most attributes are SECTION_BOTH.
        """
