# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The syntax of the Navigate DSL: the AST ``grammar.lark`` is read into.

Nothing here knows what a node is: a reference is a type and a name, and an
expression is the evaluator tree of ``core.expression`` with references as its
leaves. The build phase binds both once every declaration is known.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

import numpy as np
from lark import Lark, Token, Transformer, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedToken, VisitError
from lark.lexer import PatternStr

from navigate.core.expression import (
    BinaryOperation,
    Constant,
    NodeReference,
    UnaryOperation,
    node_references,
)
from navigate.core.table_data import TableData
from navigate.exceptions import DeckError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from lark.tree import Meta

    from navigate.core.expression import Evaluable
    from navigate.core.table_data import Cell


@dataclass(frozen=True)
class SourceLocation:
    """Where a statement was written: file and line, and the deck line that read it."""

    file: str = ""
    line: int = 0
    deck_line: int = 0

    def prefix(self) -> str:
        """Spell the location the way every deck error opens."""
        parts = []
        if self.deck_line:
            parts.append(f"Error in deck file, line {self.deck_line}")
        if self.file:
            parts.append(f"include file '{self.file}', line {self.line}")
        return ", ".join(parts) if parts else "Parser error"

    def error(self, message: str) -> DeckError:
        """Build the deck error for a one-sentence message written here."""
        return DeckError(f"{self.prefix()}: {message}")


# deck-level AST (.nav) ----------------------------------------------------------------


@dataclass
class IncludeDirective:
    """``Include "path/to/file.inc"``."""

    path: str
    source: SourceLocation = field(default_factory=SourceLocation)


@dataclass
class LoadModuleDirective:
    """``Load ModuleName``."""

    name: str
    source: SourceLocation = field(default_factory=SourceLocation)


type Directive = IncludeDirective | LoadModuleDirective


@dataclass
class Deck:
    """A parsed .nav file: the directives of its DEFINE block and its EVENTS block."""

    define: list[Directive]
    events: list[Directive]


# values -------------------------------------------------------------------------------


@dataclass(frozen=True)
class ExpressionSyntax:
    """An expression as written in a deck, ``<...>``, parsed but not yet bound."""

    text: str
    root: Evaluable

    def __repr__(self) -> str:
        return self.text


# a value as the deck writes it, before any reference names a node
type DeckValue = (
    float
    | str
    | np.datetime64
    | NodeReference
    | ExpressionSyntax
    | TableData
    | list[DeckValue]
)


# include-level AST (.inc) -------------------------------------------------------------


@dataclass
class Assignment:
    """``Attribute = value``; a ``Table = [...]`` block is one too."""

    attribute: str
    value: DeckValue
    source: SourceLocation = field(default_factory=SourceLocation)

    @property
    def name(self) -> str:
        """The attribute set, named as a command's name is."""
        return self.attribute


@dataclass
class Command:
    """``set_something(arg1, arg2)``."""

    name: str
    args: list[DeckValue] = field(default_factory=list)
    source: SourceLocation = field(default_factory=SourceLocation)


type BodyItem = Assignment | Command


def item_references(item: BodyItem) -> Iterator[tuple[NodeReference, bool]]:
    """Yield each node reference an item holds, and whether it is in an expression."""
    values = [item.value] if isinstance(item, Assignment) else item.args
    for value in values:
        yield from _references(value)


def _references(value: DeckValue) -> Iterator[tuple[NodeReference, bool]]:
    if isinstance(value, NodeReference):
        yield value, False

    elif isinstance(value, list):
        for element in value:
            yield from _references(element)

    elif isinstance(value, ExpressionSyntax):
        for reference in node_references(value.root):
            yield reference, True


@dataclass
class NodeDeclaration:
    """Named node declaration, e.g. ``Vessel "my_ship" { ... }``."""

    node_type: str
    name: str
    body: list[BodyItem]
    source: SourceLocation = field(default_factory=SourceLocation)


@dataclass
class GeneralNodeDeclaration:
    """Singleton node declaration, e.g. ``ModelDefinition { ... }``."""

    node_type: str
    body: list[BodyItem]
    source: SourceLocation = field(default_factory=SourceLocation)

    @property
    def keyword(self) -> str:
        """The keyword opening the statement: the general node's type."""
        return self.node_type


@dataclass
class CopyStatement:
    """``Copy Vessel "copy_from" "copy_to"``."""

    keyword: ClassVar[str] = "Copy"

    node_type: str
    copy_from: str
    copy_to: str
    source: SourceLocation = field(default_factory=SourceLocation)


@dataclass
class ImportStatement:
    """``Import Vessel "name"``."""

    keyword: ClassVar[str] = "Import"

    node_type: str
    name: str
    source: SourceLocation = field(default_factory=SourceLocation)


@dataclass
class DateStatement:
    """``Date "01-01-2025"``."""

    keyword: ClassVar[str] = "Date"

    date: np.datetime64
    source: SourceLocation = field(default_factory=SourceLocation)


@dataclass
class StartTimeline:
    """``Start`` keyword: the model definition's start date."""

    keyword: ClassVar[str] = "Start"

    source: SourceLocation = field(default_factory=SourceLocation)


@dataclass
class EndTimeline:
    """``End`` keyword, accepted for older decks; it has no effect."""

    keyword: ClassVar[str] = "End"

    source: SourceLocation = field(default_factory=SourceLocation)


type Statement = (
    NodeDeclaration
    | GeneralNodeDeclaration
    | CopyStatement
    | ImportStatement
    | DateStatement
    | StartTimeline
    | EndTimeline
)


# lark transformer ---------------------------------------------------------------------


@v_args(inline=True)
class _NavTransformer(Transformer[Token, object]):
    """Turn a parse tree into the AST: tokens into values, rules into nodes."""

    def __init__(self, text: str, file: str, deck_line: int) -> None:
        super().__init__()
        self._text = text
        self._file = file
        self._deck_line = deck_line

    def _source(self, line: int) -> SourceLocation:
        return SourceLocation(self._file, line, self._deck_line)

    def __default_token__(self, token: Token) -> object:
        match token.type:
            case "QUOTED_STRING":
                return token[1:-1]
            case "SIGNED_NUMBER" | "NUMBER":
                return float(token)
            case "DATE":
                return self._date(token)
            case _:
                return str(token)

    def _date(self, token: Token) -> np.datetime64:
        # numpy reads only the ISO form, so a day-first dd-mm-yyyy or dd/mm/yyyy date
        # is reordered, and numpy refuses a day the calendar lacks
        day_first = re.fullmatch(r'"(\d{2})[-/](\d{2})[-/](\d{4})"', token)
        iso = "-".join(reversed(day_first.groups())) if day_first else token.strip('"')
        try:
            return np.datetime64(iso, "D")
        except ValueError:
            source = self._source(token.line or 0)
            raise source.error(f"{token} is not a calendar date.") from None

    def _as_list(self, *children: object) -> list[object]:
        return list(children)

    # rules whose value is the list of their children
    define_block = events_block = include_file = _as_list
    arguments = list_value = table_row = _as_list

    def deck(self, define: list[Directive], events: list[Directive]) -> Deck:
        return Deck(define, events)

    @v_args(meta=True, inline=True)
    def include_directive(self, meta: Meta, path: str) -> IncludeDirective:
        return IncludeDirective(path, self._source(meta.line))

    @v_args(meta=True, inline=True)
    def load_module(self, meta: Meta, name: str) -> LoadModuleDirective:
        return LoadModuleDirective(name, self._source(meta.line))

    @v_args(meta=True, inline=True)
    def node_declaration(
        self, meta: Meta, node_type: str, name: str, *body: BodyItem
    ) -> NodeDeclaration:
        return NodeDeclaration(node_type, name, list(body), self._source(meta.line))

    @v_args(meta=True, inline=True)
    def general_node_declaration(
        self, meta: Meta, node_type: str, *body: BodyItem
    ) -> GeneralNodeDeclaration:
        return GeneralNodeDeclaration(node_type, list(body), self._source(meta.line))

    @v_args(meta=True, inline=True)
    def copy_statement(
        self, meta: Meta, node_type: str, copy_from: str, copy_to: str
    ) -> CopyStatement:
        return CopyStatement(node_type, copy_from, copy_to, self._source(meta.line))

    @v_args(meta=True, inline=True)
    def import_statement(
        self, meta: Meta, node_type: str, name: str
    ) -> ImportStatement:
        return ImportStatement(node_type, name, self._source(meta.line))

    @v_args(meta=True, inline=True)
    def date_statement(self, meta: Meta, date: np.datetime64) -> DateStatement:
        return DateStatement(date, self._source(meta.line))

    @v_args(meta=True, inline=True)
    def start_timeline(self, meta: Meta) -> StartTimeline:
        return StartTimeline(self._source(meta.line))

    @v_args(meta=True, inline=True)
    def end_timeline(self, meta: Meta) -> EndTimeline:
        return EndTimeline(self._source(meta.line))

    @v_args(meta=True, inline=True)
    def assignment(self, meta: Meta, attribute: str, value: DeckValue) -> Assignment:
        return Assignment(attribute, value, self._source(meta.line))

    @v_args(meta=True, inline=True)
    def table_assignment(self, meta: Meta, *rows: list[Cell]) -> Assignment:
        return Assignment("Table", TableData(list(rows)), self._source(meta.line))

    @v_args(meta=True, inline=True)
    def command(self, meta: Meta, name: str, arguments: list[DeckValue]) -> Command:
        return Command(name, arguments, self._source(meta.line))

    def node_reference(self, node_type: str, name: str) -> NodeReference:
        return NodeReference(node_type, name)

    @v_args(meta=True, inline=True)
    def expression(self, meta: Meta, root: Evaluable) -> ExpressionSyntax:
        # the rule spans its brackets, so the spelling sits between them
        text = self._text[meta.start_pos + 1 : meta.end_pos - 1].strip()
        return ExpressionSyntax(text, root)

    def binary_operation(
        self, left: Evaluable, symbol: str, right: Evaluable
    ) -> BinaryOperation:
        return BinaryOperation(symbol, left, right)

    def unary_operation(self, symbol: str, operand: Evaluable) -> UnaryOperation:
        return UnaryOperation(symbol, operand)

    def constant(self, value: float) -> Constant:
        return Constant(value)

    def infinity(self) -> Constant:
        return Constant(math.inf)


# public API ---------------------------------------------------------------------------

_PARSER = Lark.open_from_package(
    "navigate.parser",
    "grammar.lark",
    parser="lalr",
    propagate_positions=True,
    maybe_placeholders=False,
    start=["deck", "include_file"],
    cache=True,
)

# the text of each fixed-string terminal, e.g. LBRACE -> {
_LITERALS = {
    terminal.name: terminal.pattern.value
    for terminal in _PARSER.terminals
    if isinstance(terminal.pattern, PatternStr)
}


def _describe(terminal: str) -> str:
    """Name a terminal as a deck author reads it: its text, or its name in words."""
    if terminal == "$END":
        return "end of file"
    if terminal in _LITERALS:
        return f"'{_LITERALS[terminal]}'"
    return terminal.lower().replace("_", " ")


def _syntax_error(
    error: UnexpectedToken | UnexpectedCharacters,
    text: str,
    file: str,
    deck_line: int,
) -> DeckError:
    """Build the error for text the grammar refuses, quoting its line with a caret."""
    if isinstance(error, UnexpectedToken):
        token = error.token
        got = _describe(token.type) if token.type == "$END" else repr(str(token))
        expected = error.expected
    else:
        got = repr(error.char)
        expected = error.allowed

    *others, last = sorted(_describe(name) for name in expected) or ["nothing"]
    listed = f"{', '.join(others)} or {last}" if others else last

    if deck_line:
        where = SourceLocation(file, error.line, deck_line).prefix()
    elif file:
        where = f"In file '{file}', line {error.line}"
    else:
        where = f"Line {error.line}"

    context = error.get_context(text).rstrip("\n")
    return DeckError(f"{where}:\n\n{context}\nUnexpected {got} - expected {listed}")


def _parse(start: str, text: str, file: str, deck_line: int) -> object:
    # the LALR parser reports running out of input as an UnexpectedToken
    try:
        tree = _PARSER.parse(text, start=start)
    except (UnexpectedToken, UnexpectedCharacters) as error:
        raise _syntax_error(error, text, file, deck_line) from None

    # lark wraps an error a rule method raises; the deck error inside is the
    # one to report
    try:
        return _NavTransformer(text, file, deck_line).transform(tree)
    except VisitError as error:
        raise error.orig_exc from None


def parse_deck_content(text: str, file: str = "") -> Deck:
    """Parse the text of a deck (.nav) file; ``file`` is named in errors."""
    deck = _parse("deck", text, file, 0)
    assert isinstance(deck, Deck)
    return deck


def parse_include_content(
    text: str, file: str = "", deck_line: int = 0
) -> list[Statement]:
    """Parse the text of an include (.inc) file read through a deck directive."""
    statements = _parse("include_file", text, file, deck_line)
    assert isinstance(statements, list)
    return statements
