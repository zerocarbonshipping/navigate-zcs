# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.parser._lark_parser import SourceLocation


class Event:
    """A collection of AST statements associated with a timeline date.

    Parameters
    ----------
    source : SourceLocation
        Location of the Date/Start keyword that created this event.
    deck_line : int
        Line in the .nav file of the enclosing INCLUDE directive.
    """

    def __init__(self, source: SourceLocation, deck_line: int = 0):
        self.statements: list = []
        self._source = source
        self._deck_line = deck_line

    def add_statement(self, statement):
        self.statements.append(statement)

    @property
    def source(self) -> SourceLocation:
        return self._source

    @property
    def deck_line(self) -> int:
        return self._deck_line
