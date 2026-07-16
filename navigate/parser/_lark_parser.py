# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Lark-based parser for the Navigate DSL.

Provides the single source of truth for both .nav (deck) and .inc (include)
file syntax.  The grammar lives in ``grammar.lark``; this module contains:

* AST dataclasses for deck directives and include statements
* ``NavTransformer`` — converts Lark parse-trees into AST nodes
* ``parse_include_content()`` / ``parse_deck_content()`` — public API
"""
import re
from dataclasses import dataclass, field
from importlib.resources import files
from typing import Any, List

from lark import Lark, Transformer, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedToken

from navigate.calculator._table_data import (
    SourceLoc,
    TableData,
    parse_table_cells,
    string_to_date,
)
from navigate.core import Expression, NodeReference
from navigate.core.node_reference import WildcardNodeReference
from navigate.exceptions import DeckFormatError
from navigate.util import name_contains_wildcards

# ═════════════════════════════════════════════════════════════════════════
# AST — deck level (.nav)
# ═════════════════════════════════════════════════════════════════════════


@dataclass
class IncludeDirective:
    """``INCLUDE "path/to/file.inc"``."""

    path: str
    source: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class LoadModuleDirective:
    """``Load ModuleName``."""

    name: str
    source: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class DefineBlock:
    """``DEFINE { ... }`` block."""

    directives: list
    source: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class EventsBlock:
    """``EVENTS { ... }`` block."""

    directives: list
    source: SourceLoc = field(default_factory=SourceLoc)


# ═════════════════════════════════════════════════════════════════════════
# AST — include level (.inc)
# ═════════════════════════════════════════════════════════════════════════


@dataclass
class NodeDecl:
    """Named node declaration, e.g. ``Vessel "my_ship" { ... }``."""

    node_type: str
    name: str
    body: list
    source: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class GeneralNodeDecl:
    """Singleton node declaration, e.g. ``ModelDefinition { ... }``."""

    node_type: str
    body: list
    source: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class CopyStmt:
    """``Copy Vessel "source" "target"``."""

    node_type: str
    src: str
    dst: str
    source: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class ImportStmt:
    """``Import Vessel "name"``."""

    node_type: str
    name: str
    source: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class DateStmt:
    """``Date "01-01-2025"``."""

    date_string: str
    source: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class StartTimeline:
    """``Start`` keyword."""

    source: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class EndTimeline:
    """``End`` keyword."""

    source: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class Assignment:
    """``Attribute = value``."""

    attribute: str
    value: Any
    source: SourceLoc = field(default_factory=SourceLoc)


@dataclass
class Command:
    """``set_something(arg1, arg2)``."""

    name: str
    args: list = field(default_factory=list)
    source: SourceLoc = field(default_factory=SourceLoc)


# ═════════════════════════════════════════════════════════════════════════
# Lark Transformer
# ═════════════════════════════════════════════════════════════════════════


# noinspection PyMethodMayBeStatic
@v_args(meta=True)
class NavTransformer(Transformer):
    """Convert Lark parse trees to Navigate AST nodes.

    The ``file`` attribute is set before each transform call so that
    every produced ``SourceLoc`` carries the originating file path.
    """

    file: str = ""

    def _loc(self, meta) -> SourceLoc:
        return SourceLoc(file=self.file, line=meta.line)

    @staticmethod
    def _check_one_stmt_per_line(stmts: list) -> None:
        seen_lines: dict = {}
        for stmt in stmts:
            loc = getattr(stmt, 'source', None)
            if loc and loc.line in seen_lines:
                raise DeckFormatError(
                    f"Line {loc.line}: Multiple statements on the same line. "
                    f"Each statement must be on its own line."
                )
            if loc:
                seen_lines[loc.line] = True

    # ── deck ──────────────────────────────────────────────────────

    def deck(self, meta, items):
        self._check_one_stmt_per_line(list(items))
        return list(items)

    def define_block(self, meta, items):
        return DefineBlock(list(items), source=self._loc(meta))

    def events_block(self, meta, items):
        return EventsBlock(list(items), source=self._loc(meta))

    def include_directive(self, meta, items):
        path = str(items[0])[1:-1]
        return IncludeDirective(path, source=self._loc(meta))

    def load_module(self, meta, items):
        name = str(items[0])
        return LoadModuleDirective(name, source=self._loc(meta))

    # ── include statements ────────────────────────────────────────

    def start(self, meta, items):
        stmts = list(items)
        self._check_one_stmt_per_line(stmts)
        return stmts

    def node_decl(self, meta, items):
        body = list(items[2:])
        self._check_one_stmt_per_line(body)
        return NodeDecl(str(items[0]), str(items[1])[1:-1], body, source=self._loc(meta))

    def general_node_decl(self, meta, items):
        body = list(items[1:])
        self._check_one_stmt_per_line(body)
        return GeneralNodeDecl(str(items[0]), body, source=self._loc(meta))

    def copy_stmt(self, meta, items):
        return CopyStmt(str(items[0]), str(items[1])[1:-1], str(items[2])[1:-1], source=self._loc(meta))

    def import_stmt(self, meta, items):
        return ImportStmt(str(items[0]), str(items[1])[1:-1], source=self._loc(meta))

    def date_stmt(self, meta, items):
        return DateStmt(str(items[0])[1:-1], source=self._loc(meta))

    def start_timeline(self, meta, items):
        return StartTimeline(source=self._loc(meta))

    def end_timeline(self, meta, items):
        return EndTimeline(source=self._loc(meta))

    # ── node body ─────────────────────────────────────────────────

    def assignment(self, meta, items):
        return Assignment(str(items[0]), items[1], source=self._loc(meta))

    def command(self, meta, items):
        name = str(items[0])
        args = items[1] if len(items) > 1 else []
        return Command(name, args, source=self._loc(meta))

    def arg_list(self, meta, items):
        return list(items)

    def table_block(self, meta, items):
        return Assignment("Table", TableData(parse_table_cells(str(items[0])), source=self._loc(meta)),
                          source=self._loc(meta))

    # ── values ────────────────────────────────────────────────────

    def number(self, meta, items):
        return float(items[0])

    def node_ref(self, meta, items):
        node_type = str(items[0])
        name = str(items[1])[1:-1]
        if name_contains_wildcards(name):
            return WildcardNodeReference(node_type, name)
        return NodeReference(node_type, name)

    def expression(self, meta, items):
        return Expression(str(items[0])[1:-1])

    def wildcard_value(self, meta, items):
        return str(items[0])

    def ident_value(self, meta, items):
        return str(items[0])

    def string_value(self, meta, items):
        s = str(items[0])[1:-1]
        if re.match(r'^\d{2}([-/])\d{2}\1\d{4}$', s):
            return string_to_date(s, msg="Error in date: Must be dd-mm-yyyy or dd/mm/yyyy.")
        return s

    def list_value(self, meta, items):
        return list(items)

    def table_value(self, meta, items):
        return TableData(parse_table_cells(str(items[0])), source=self._loc(meta))

    def template_value(self, meta, items):
        return str(items[0])


# ═════════════════════════════════════════════════════════════════════════
# Public API
# ═════════════════════════════════════════════════════════════════════════

_GRAMMAR_TEXT = (files("navigate.parser") / "grammar.lark").read_text(encoding="utf-8")

_inc_parser = Lark(_GRAMMAR_TEXT, parser='lalr', propagate_positions=True, maybe_placeholders=False, start='start')
_deck_parser = Lark(_GRAMMAR_TEXT, parser='lalr', propagate_positions=True, maybe_placeholders=False, start='deck')

_transformer = NavTransformer()

_FRIENDLY = {
    "NAME": "a name", "NODE_TYPE": "a node type", "TABLE_BLOCK": "a Table = [...] block",
    "RBRACE": "'}'", "LBRACE": "'{'", "QUOTED_STRING": "a quoted string",
    "SIGNED_NUMBER": "a number", "EXPRESSION": "an expression", "TEMPLATE": "a template",
    "COMMA": "','", "RPAR": "')'", "LPAR": "'('", "EQUAL": "'='",
    "LSQB": "'['", "RSQB": "']'", "COLON": "':'", "SEMICOLON": "';'",
}


def _format_parse_error(e, source: str, file: str) -> str:
    lines = source.splitlines()
    parts = []
    if file:
        parts.append(f"In file '{file}'")
    if isinstance(e, (UnexpectedToken, UnexpectedCharacters)):
        line_no = getattr(e, 'line', 0)
        col = getattr(e, 'column', 0)
        if 1 <= line_no <= len(lines):
            src_line = lines[line_no - 1]
            parts.append(f"line {line_no}:\n\n  {line_no} | {src_line}\n  {' ' * len(str(line_no))} | {' ' * (col - 1)}^")
    if isinstance(e, UnexpectedToken):
        tok = _FRIENDLY.get(e.token.type, repr(e.token.value))
        expected = [_FRIENDLY.get(x, x) for x in sorted(e.expected)]
        if len(expected) > 1:
            exp_str = ', '.join(expected[:-1]) + ' or ' + expected[-1]
        else:
            exp_str = expected[0]
        parts.append(f"\nUnexpected {tok} — expected {exp_str}")
    else:
        parts.append(str(e))
    return ", ".join(parts[:2]) + "".join(parts[2:])


def _parse(parser, text: str, file: str):
    _transformer.file = file
    try:
        tree = parser.parse(text)
    except (UnexpectedToken, UnexpectedCharacters) as e:
        raise DeckFormatError(_format_parse_error(e, text, file)) from e
    return _transformer.transform(tree)


def parse_include_content(text: str, file: str = "") -> List:
    return _parse(_inc_parser, text, file)


def parse_deck_content(text: str, file: str = "") -> List:
    return _parse(_deck_parser, text, file)
