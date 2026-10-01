# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The event: the statements the parser queues under one timeline date."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.parser._lark_parser import EventStatement, SourceLocation


class Event:
    """
    A collection of AST statements associated with a timeline date.

    Parameters
    ----------
    source
        Location of the Date/Start keyword that created this event.
    deck_line
        Line in the .nav file of the enclosing INCLUDE directive.
    """

    def __init__(self, source: SourceLocation, deck_line: int = 0) -> None:
        self.statements: list[EventStatement] = []
        self._source: SourceLocation = source
        self._deck_line: int = deck_line

    def add_statement(self, statement: EventStatement) -> None:
        """
        Queue a statement, to be read when the event's date is reached.

        Parameters
        ----------
        statement
            The statement to queue.
        """
        self.statements.append(statement)

    @property
    def source(self) -> SourceLocation:
        """
        The location of the keyword that created the event.

        Returns
        -------
        SourceLocation
            The include-file location of the Date or Start keyword.
        """
        return self._source

    @property
    def deck_line(self) -> int:
        """
        The deck line of the INCLUDE directive the event was read under.

        Returns
        -------
        int
            The line in the .nav file.
        """
        return self._deck_line
