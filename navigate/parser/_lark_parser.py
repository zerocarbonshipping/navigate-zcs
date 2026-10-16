# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Lark-based parser for the Navigate DSL.

Provides the single source of truth for both .nav (deck) and .inc (include)
file syntax.  The grammar lives in ``grammar.lark``; this module contains:

* AST dataclasses for deck directives and include statements
* ``_NavTransformer`` and its two start-rule subclasses - convert Lark
  parse-trees into AST nodes
* ``parse_include_content()`` / ``parse_deck_content()`` - public API
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from importlib.resources import files
from typing import TYPE_CHECKING

from lark import Lark, Token, Transformer, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedToken, VisitError

from navigate.core import Expression
from navigate.core.table_data import TableData, parse_table_cells, string_to_date
from navigate.exceptions import DeckFormatError
from navigate.parser._node_reference import NodeReference, WildcardNodeReference
from navigate.util import name_contains_wildcards

if TYPE_CHECKING:
    from collections.abc import Sequence

    import numpy as np
    from lark.tree import Meta

    from navigate.core.node import Node


@dataclass(frozen=True)
class SourceLocation:
    """Immutable source-location tag attached to every AST node."""

    file: str = ""
    line: int = 0


# deck-level AST (.nav) ----------------------------------------------------------------


@dataclass
class IncludeDirective:
    """``INCLUDE "path/to/file.inc"``."""

    path: str
    source: SourceLocation = field(default_factory=SourceLocation)


@dataclass
class LoadModuleDirective:
    """``Load ModuleName``."""

    name: str
    source: SourceLocation = field(default_factory=SourceLocation)


type Directive = IncludeDirective | LoadModuleDirective


@dataclass
class DefineBlock:
    """``DEFINE { ... }`` block."""

    directives: list[Directive]
    source: SourceLocation = field(default_factory=SourceLocation)


@dataclass
class EventsBlock:
    """``EVENTS { ... }`` block."""

    directives: list[Directive]
    source: SourceLocation = field(default_factory=SourceLocation)


type DeckBlock = DefineBlock | EventsBlock


# include-level AST (.inc) -------------------------------------------------------------


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


@dataclass
class CopyStatement:
    """``Copy Vessel "copy_from" "copy_to"``."""

    node_type: str
    copy_from: str
    copy_to: str
    source: SourceLocation = field(default_factory=SourceLocation)


@dataclass
class ImportStatement:
    """``Import Vessel "name"``."""

    node_type: str
    name: str
    source: SourceLocation = field(default_factory=SourceLocation)


@dataclass
class DateStatement:
    """``Date "01-01-2025"``."""

    date_string: str
    source: SourceLocation = field(default_factory=SourceLocation)


@dataclass
class StartTimeline:
    """``Start`` keyword."""

    source: SourceLocation = field(default_factory=SourceLocation)


@dataclass
class EndTimeline:
    """``End`` keyword."""

    source: SourceLocation = field(default_factory=SourceLocation)


@dataclass
class Assignment:
    """``Attribute = value``."""

    attribute: str
    value: DeckValue
    source: SourceLocation = field(default_factory=SourceLocation)


@dataclass
class Command:
    """``set_something(arg1, arg2)``."""

    name: str
    args: list[DeckValue] = field(default_factory=list)
    source: SourceLocation = field(default_factory=SourceLocation)


# a value as the deck writes it, before any node reference names a node
type DeckValue = (
    float
    | str
    | np.datetime64
    | NodeReference
    | WildcardNodeReference
    | Expression
    | TableData
    | list[DeckValue]
)

# a Table block is an assignment too
type BodyItem = Assignment | Command

# the statements that act on nodes: read as they come, or queued in an event
# until its date
type EventStatement = (
    NodeDeclaration | GeneralNodeDeclaration | CopyStatement | ImportStatement
)

# a deck value once every node reference names its node; a wildcard waits for
# the registry to hold every node it may match, and its expansion stays this
# type, as a wildcard-free value is one too
type MaterializedValue = (
    float
    | str
    | np.datetime64
    | Node
    | WildcardNodeReference
    | Expression
    | TableData
    | list[MaterializedValue]
)

# the include parser's start rule ("start") yields one of these per top-level
# statement; the deck parser's start rule ("deck") yields DeckBlock instead,
# handled directly where it is used
type Statement = EventStatement | DateStatement | StartTimeline | EndTimeline


# lark transformer ---------------------------------------------------------------------


@v_args(meta=True, inline=True)
class _NavTransformer[ReturnT](Transformer[Token, ReturnT]):
    """
    Convert Lark parse trees to Navigate AST nodes.

    Holds the rules shared by the deck and include grammars; a subclass per
    start rule adds the one entry-point method fixing ``ReturnT``, and is
    built fresh for each parse so its ``file`` cannot leak between calls.
    Each rule method takes a rule's children as positional arguments, which
    type each child by its place in the rule.

    Parameters
    ----------
    file
        Path reported in every ``SourceLocation`` this instance produces.
    """

    def __init__(self, file: str) -> None:
        super().__init__()
        self.file: str = file

    def _loc(self, meta: Meta) -> SourceLocation:
        return SourceLocation(file=self.file, line=meta.line)

    @staticmethod
    def _check_one_statement_per_line(
        statements: Sequence[DeckBlock | Statement | BodyItem],
    ) -> None:
        seen_lines: set[int] = set()
        for statement in statements:
            line = statement.source.line
            if line in seen_lines:
                raise DeckFormatError(
                    f"Line {line}: Multiple statements on the same line. "
                    f"Each statement must be on its own line."
                )

            seen_lines.add(line)

    # deck -----------------------------------------------------------------------------

    def define_block(self, meta: Meta, *directives: Directive) -> DefineBlock:
        return DefineBlock(list(directives), source=self._loc(meta))

    def events_block(self, meta: Meta, *directives: Directive) -> EventsBlock:
        return EventsBlock(list(directives), source=self._loc(meta))

    def include_directive(self, meta: Meta, path: Token) -> IncludeDirective:
        return IncludeDirective(str(path)[1:-1], source=self._loc(meta))

    def load_module(self, meta: Meta, name: Token) -> LoadModuleDirective:
        return LoadModuleDirective(str(name), source=self._loc(meta))

    # include statements ---------------------------------------------------------------

    def node_declaration(
        self, meta: Meta, node_type: Token, name: Token, *body_items: BodyItem
    ) -> NodeDeclaration:
        body = list(body_items)
        self._check_one_statement_per_line(body)
        return NodeDeclaration(
            str(node_type), str(name)[1:-1], body, source=self._loc(meta)
        )

    def general_node_declaration(
        self, meta: Meta, node_type: Token, *body_items: BodyItem
    ) -> GeneralNodeDeclaration:
        body = list(body_items)
        self._check_one_statement_per_line(body)
        return GeneralNodeDeclaration(str(node_type), body, source=self._loc(meta))

    def copy_statement(
        self, meta: Meta, node_type: Token, copy_from: Token, copy_to: Token
    ) -> CopyStatement:
        return CopyStatement(
            str(node_type),
            str(copy_from)[1:-1],
            str(copy_to)[1:-1],
            source=self._loc(meta),
        )

    def import_statement(
        self, meta: Meta, node_type: Token, name: Token
    ) -> ImportStatement:
        return ImportStatement(str(node_type), str(name)[1:-1], source=self._loc(meta))

    def date_statement(self, meta: Meta, date: Token) -> DateStatement:
        return DateStatement(str(date)[1:-1], source=self._loc(meta))

    def start_timeline(self, meta: Meta) -> StartTimeline:
        return StartTimeline(source=self._loc(meta))

    def end_timeline(self, meta: Meta) -> EndTimeline:
        return EndTimeline(source=self._loc(meta))

    # node body ------------------------------------------------------------------------

    def assignment(self, meta: Meta, attribute: Token, value: DeckValue) -> Assignment:
        return Assignment(str(attribute), value, source=self._loc(meta))

    def command(self, meta: Meta, name: Token, arguments: list[DeckValue]) -> Command:
        return Command(str(name), arguments, source=self._loc(meta))

    def arguments(self, meta: Meta, *values: DeckValue) -> list[DeckValue]:
        return list(values)

    def table_block(self, meta: Meta, table: Token) -> Assignment:
        return Assignment(
            "Table", TableData(parse_table_cells(str(table))), source=self._loc(meta)
        )

    # values ---------------------------------------------------------------------------

    def number(self, meta: Meta, number: Token) -> float:
        return float(number)

    def node_reference(
        self, meta: Meta, node_type: Token, name: Token
    ) -> NodeReference | WildcardNodeReference:
        name_text = str(name)[1:-1]
        if name_contains_wildcards(name_text):
            return WildcardNodeReference(str(node_type), name_text)

        return NodeReference(str(node_type), name_text)

    def expression(self, meta: Meta, expression: Token) -> Expression:
        text = str(expression)[1:-1]
        try:
            return Expression(text)
        except (ValueError, NotImplementedError) as error:
            if self.file:
                message = f"In file '{self.file}', line {meta.line}: {error}"
            else:
                message = f"Line {meta.line}: {error}"
            raise DeckFormatError(message) from None

    def wildcard_value(self, meta: Meta, wildcard: Token) -> str:
        return str(wildcard)

    def ident_value(self, meta: Meta, identifier: Token) -> str:
        return str(identifier)

    def string_value(self, meta: Meta, string: Token) -> str | np.datetime64:
        text = str(string)[1:-1]
        if re.match(r"^\d{2}([-/])\d{2}\1\d{4}$", text):
            return string_to_date(
                text, msg="Error in date: Must be dd-mm-yyyy or dd/mm/yyyy."
            )

        return text

    def list_value(self, meta: Meta, *values: DeckValue) -> list[DeckValue]:
        return list(values)

    def table_value(self, meta: Meta, table: Token) -> TableData:
        return TableData(parse_table_cells(str(table)))

    def template_value(self, meta: Meta, template: Token) -> str:
        return str(template)


@v_args(meta=True, inline=True)
class _DeckTransformer(_NavTransformer[list[DeckBlock]]):
    """Transform a parsed .nav deck's top rule into its DEFINE/EVENTS blocks."""

    def deck(self, meta: Meta, *blocks: DeckBlock) -> list[DeckBlock]:
        deck_blocks = list(blocks)
        self._check_one_statement_per_line(deck_blocks)
        return deck_blocks


@v_args(meta=True, inline=True)
class _IncludeTransformer(_NavTransformer[list[Statement]]):
    """Transform a parsed .inc file's top rule into its statements."""

    def start(self, meta: Meta, *statements: Statement) -> list[Statement]:
        include_statements = list(statements)
        self._check_one_statement_per_line(include_statements)
        return include_statements


# public API ---------------------------------------------------------------------------

_GRAMMAR_TEXT = (files("navigate.parser") / "grammar.lark").read_text(encoding="utf-8")

_inc_parser = Lark(
    _GRAMMAR_TEXT,
    parser="lalr",
    propagate_positions=True,
    maybe_placeholders=False,
    start="start",
)
_deck_parser = Lark(
    _GRAMMAR_TEXT,
    parser="lalr",
    propagate_positions=True,
    maybe_placeholders=False,
    start="deck",
)

_FRIENDLY = {
    "NAME": "a name",
    "NODE_TYPE": "a node type",
    "TABLE_BLOCK": "a Table = [...] block",
    "RBRACE": "'}'",
    "LBRACE": "'{'",
    "QUOTED_STRING": "a quoted string",
    "SIGNED_NUMBER": "a number",
    "EXPRESSION": "an expression",
    "TEMPLATE": "a template",
    "COMMA": "','",
    "RPAR": "')'",
    "LPAR": "'('",
    "EQUAL": "'='",
    "LSQB": "'['",
    "RSQB": "']'",
    "COLON": "':'",
    "SEMICOLON": "';'",
}


def _format_parse_error(
    error: UnexpectedToken | UnexpectedCharacters, source: str, file: str
) -> str:
    """
    Build the message of a syntax error, pointing at its line and column.

    Parameters
    ----------
    error
        The error Lark raised.
    source
        The text that was parsed.
    file
        Path of the parsed file, or an empty string for text read from no file.

    Returns
    -------
    str
        The message, naming the file, quoting the line, and stating what was
        expected where Lark knows it.
    """
    lines = source.splitlines()
    parts = []
    if file:
        parts.append(f"In file '{file}'")

    line_no = error.line
    if 1 <= line_no <= len(lines):
        source_line = lines[line_no - 1]
        parts.append(
            f"line {line_no}:\n\n  {line_no} | {source_line}\n  "
            f"{' ' * len(str(line_no))} | {' ' * (error.column - 1)}^"
        )

    if isinstance(error, UnexpectedToken):
        token = _FRIENDLY.get(error.token.type, repr(error.token.value))
        expected = [_FRIENDLY.get(name, name) for name in sorted(error.expected)]
        if len(expected) > 1:
            expected_text = ", ".join(expected[:-1]) + " or " + expected[-1]
        else:
            expected_text = expected[0]
        parts.append(f"\nUnexpected {token} — expected {expected_text}")
    else:
        parts.append(str(error))

    return ", ".join(parts[:2]) + "".join(parts[2:])


def _parse[ReturnT](
    parser: Lark, transformer: _NavTransformer[ReturnT], text: str
) -> ReturnT:
    try:
        tree = parser.parse(text)
    except (UnexpectedToken, UnexpectedCharacters) as e:
        raise DeckFormatError(_format_parse_error(e, text, transformer.file)) from e

    try:
        return transformer.transform(tree)
    except VisitError as e:
        if isinstance(e.orig_exc, DeckFormatError):
            raise e.orig_exc from None

        raise


def parse_include_content(text: str, file: str = "") -> list[Statement]:
    """
    Parse the text of an include (.inc) file into its statements.

    Parameters
    ----------
    text
        The file's text.
    file
        Path reported in the statements' source locations and in errors.

    Returns
    -------
    list[Statement]
        The top-level statements, in file order.
    """
    return _parse(_inc_parser, _IncludeTransformer(file), text)


def parse_deck_content(text: str, file: str = "") -> list[DeckBlock]:
    """
    Parse the text of a deck (.nav) file into its DEFINE and EVENTS blocks.

    Parameters
    ----------
    text
        The file's text.
    file
        Path reported in the blocks' source locations and in errors.

    Returns
    -------
    list[DeckBlock]
        The blocks, in file order.
    """
    return _parse(_deck_parser, _DeckTransformer(file), text)
