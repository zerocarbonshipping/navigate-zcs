# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.parser._lark_parser import SourceLoc


class Event:
    """A collection of AST statements associated with a timeline date.

    Parameters
    ----------
    source : SourceLoc
        Location of the Date/Start keyword that created this event.
    deck_line : int
        Line in the .nav file of the enclosing INCLUDE directive.
    """

    def __init__(self, source: SourceLoc, deck_line: int = 0):
        self._stmts: list = []
        self._source = source
        self._deck_line = deck_line

    def add_stmt(self, stmt):
        self._stmts.append(stmt)

    def get_stmts(self) -> list:
        return self._stmts

    @property
    def source(self) -> SourceLoc:
        return self._source

    @property
    def deck_line(self) -> int:
        return self._deck_line
