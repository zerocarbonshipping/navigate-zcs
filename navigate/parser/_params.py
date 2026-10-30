# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The %NAME% placeholders of a deck's files and the values a run fills them with.

Each file is filled in as text before the grammar reads it, so a value may stand
anywhere the file could spell it: a number, an expression's operand, a table
cell, a list's items or part of a quoted path. Comments are left as written.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from navigate.parser._syntax import SourceLocation

if TYPE_CHECKING:
    from collections.abc import Mapping

_PLACEHOLDER = re.compile(r"%([A-Za-z_][A-Za-z0-9_]*)%")

# a '#' inside a quoted string opens no comment, so the strings are matched too
_STRING_OR_COMMENT = re.compile(r'"[^"]*"|#[^\n]*')


class Params:
    """
    Fill the placeholders of a deck's files, and record which values were used.

    Parameters
    ----------
    values
        Value of each placeholder name, as text.
    """

    def __init__(self, values: Mapping[str, str]) -> None:
        self._values: dict[str, str] = dict(values)
        self._used: set[str] = set()

    def fill(self, text: str, file: str, deck_line: int) -> str:
        """
        Return a file's text with every placeholder outside its comments replaced.

        Parameters
        ----------
        text
            Content of the file.
        file
            Path of the file, named in the error.
        deck_line
            Line of the deck directive that read the file; 0 for the deck itself.

        Returns
        -------
        str
            The text with each placeholder's value in its place.

        Raises
        ------
        DeckError
            At the first placeholder whose name has no value.
        """
        if "%" not in text:
            return text

        comments = [
            match.span()
            for match in _STRING_OR_COMMENT.finditer(text)
            if match.group().startswith("#")
        ]

        def replace(match: re.Match[str]) -> str:
            if any(start <= match.start() < end for start, end in comments):
                return match.group()

            name = match.group(1)
            if name not in self._values:
                line = text.count("\n", 0, match.start()) + 1
                source = (
                    SourceLocation(file, line, deck_line)
                    if deck_line
                    else SourceLocation(deck_line=line)
                )
                raise source.error(
                    f"'{match.group()}' has no value; give it with --set {name}=VALUE."
                )

            self._used.add(name)
            return self._values[name]

        return _PLACEHOLDER.sub(replace, text)

    def unused(self) -> list[str]:
        """Return the names given a value that no file filled in so far, in order."""
        return [name for name in self._values if name not in self._used]
