# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the Lark-based parser: grammar, transformer, and helpers."""

from __future__ import annotations

import re

import numpy as np
import pytest

from navigate.core import Expression
from navigate.core.table_data import _DATE_FORMAT_ERROR
from navigate.exceptions import DeckFormatError
from navigate.parser._lark_parser import (
    Command,
    CopyStatement,
    DateStatement,
    DefineBlock,
    EndTimeline,
    EventsBlock,
    GeneralNodeDeclaration,
    ImportStatement,
    IncludeDirective,
    LoadModuleDirective,
    NodeDeclaration,
    StartTimeline,
    TableData,
    parse_deck_content,
    parse_include_content,
    parse_table_cells,
    string_to_date,
)
from navigate.parser._node_reference import NodeReference, WildcardNodeReference


# ═════════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════════
def _body(text: str) -> list:
    """Parse a single node declaration and return its body items."""
    return parse_include_content(text)[0].body


def _val(text: str):
    """Parse a single assignment inside a Vessel and return its value."""
    return _body(f'Vessel "v" {{ {text} }}')[0].value


# ═════════════════════════════════════════════════════════════════════════════════
# string_to_date
# ═════════════════════════════════════════════════════════════════════════════════
class TestStringToDate:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("01-01-2020", np.datetime64("2020-01-01")),
            ("15/06/2030", np.datetime64("2030-06-15")),
            ("2020-01-01", np.datetime64("2020-01-01")),
            ('  "01-01-2020"  ', np.datetime64("2020-01-01")),
        ],
        ids=[
            "dash_format",
            "slash_format",
            "iso_format",
            "strips_whitespace_and_quotes",
        ],
    )
    def test_parses_valid_formats(self, raw, expected):
        assert string_to_date(raw, _DATE_FORMAT_ERROR) == expected

    def test_rejects_invalid_input(self):
        # every production caller passes its own msg= with deck context; this
        # passes the same message they use for a rejection, naming the
        # accepted formats
        with pytest.raises(ValueError, match=f"^{re.escape(_DATE_FORMAT_ERROR)}$"):
            string_to_date("99-99-9999", _DATE_FORMAT_ERROR)


# ═════════════════════════════════════════════════════════════════════════════════
# Deck-level parsing (.nav) — DEFINE / EVENTS / Include / Load
# ═════════════════════════════════════════════════════════════════════════════════
class TestDeckParsing:
    def test_define_and_events_blocks(self):
        blocks = parse_deck_content(
            'DEFINE {\n  Include "nav.inc"\n  Load DefaultEmission\n}\n'
            "EVENTS {\n  Load DefaultTimeStepYearly\n}"
        )
        assert len(blocks) == 2
        define, events = blocks
        assert isinstance(define, DefineBlock)
        assert isinstance(define.directives[0], IncludeDirective)
        assert define.directives[0].path == "nav.inc"
        assert isinstance(define.directives[1], LoadModuleDirective)
        assert define.directives[1].name == "DefaultEmission"
        assert isinstance(events, EventsBlock)
        assert events.directives[0].name == "DefaultTimeStepYearly"


# ═════════════════════════════════════════════════════════════════════════════════
# Include-level statements (.inc)
# ═════════════════════════════════════════════════════════════════════════════════
class TestStatements:
    # ── node declarations ──────────────────────────────────────────
    def test_named_node(self):
        statements = parse_include_content('Vessel "my_ship" { Lifetime = 25 }')
        declaration = statements[0]
        assert isinstance(declaration, NodeDeclaration)
        assert declaration.node_type == "Vessel"
        assert declaration.name == "my_ship"
        assert declaration.body[0].attribute == "Lifetime"
        assert declaration.body[0].value == 25.0

    def test_general_node(self):
        statements = parse_include_content("ModelDefinition { Attribute = TRUE }")
        declaration = statements[0]
        assert isinstance(declaration, GeneralNodeDeclaration)
        assert declaration.node_type == "ModelDefinition"
        assert declaration.body[0].value == "TRUE"

    # ── copy / import ───────────────────────────────────────────────
    def test_copy_statement(self):
        s = parse_include_content('Copy Vessel "original" "copy"')[0]
        assert isinstance(s, CopyStatement)
        assert s.node_type == "Vessel"
        assert s.copy_from == "original"
        assert s.copy_to == "copy"

    def test_import_statement(self):
        s = parse_include_content('Import Vessel "ship"')[0]
        assert isinstance(s, ImportStatement)
        assert s.node_type == "Vessel"
        assert s.name == "ship"

    # ── statement type recognition ──────────────────────────────────
    @pytest.mark.parametrize(
        ("text", "index", "expected_type"),
        [
            ('Date "01-01-2025"', 0, DateStatement),
            ("Start\nEnd", 0, StartTimeline),
            ("Start\nEnd", 1, EndTimeline),
        ],
        ids=["date", "start", "end"],
    )
    def test_statement_type_recognized(self, text, index, expected_type):
        assert isinstance(parse_include_content(text)[index], expected_type)

    # ── comments and source location, in decks and includes alike ──
    @pytest.mark.parametrize(
        ("parse", "text", "children"),
        [
            (
                parse_include_content,
                '# comment\nVessel "v" {\n  # another\n  Lifetime = 25 # inline\n}',
                lambda statement: statement.body,
            ),
            (
                parse_deck_content,
                '# comment\nDEFINE {\n  # another\n  Include "f.inc" # inline\n}',
                lambda block: block.directives,
            ),
        ],
        ids=["include", "deck"],
    )
    def test_comments_are_skipped_and_lines_located(self, parse, text, children):
        statements = parse(text, file="test.inc")
        assert len(statements) == 1
        [statement] = statements
        [child] = children(statement)

        assert (statement.source.file, statement.source.line) == ("test.inc", 2)
        assert (child.source.file, child.source.line) == ("test.inc", 4)


# ═════════════════════════════════════════════════════════════════════════════════
# Values — all types that can appear on the RHS of an assignment
# ═════════════════════════════════════════════════════════════════════════════════
class TestValues:
    @pytest.mark.parametrize(
        ("source", "check"),
        [
            ("Value = -1.5E-3", lambda v: v == pytest.approx(-0.0015)),
            ("Value = INF", lambda v: v == float("inf")),
            ("Value = -INF", lambda v: v == float("-inf")),
            ('Route = Route("main")', lambda v: isinstance(v, NodeReference)),
            ('Value = <1 + Forecast("x")>', lambda v: isinstance(v, Expression)),
            ('Dir = "output"', lambda v: v == "output"),
            ('StartDate = "01-01-2025"', lambda v: v == np.datetime64("2025-01-01")),
            ("Price = BunkerIntensityPrice", lambda v: v == "BunkerIntensityPrice"),
            (
                'Ports = [Port("a"), Port("b")]',
                lambda v: (
                    isinstance(v, list)
                    and len(v) == 2
                    and all(isinstance(p, NodeReference) for p in v)
                ),
            ),
            ("Items = []", lambda v: v == []),
            ("Capacity = %plant_capacity%", lambda v: v == "%plant_capacity%"),
            (
                "Curve = Table = [ 2020 0.5\n2030 1.0\n]",
                lambda v: (
                    isinstance(v, TableData)
                    and v.rows == [[2020.0, 0.5], [2030.0, 1.0]]
                ),
            ),
        ],
        ids=[
            "negative_scientific",
            "inf",
            "negative_inf",
            "node_reference",
            "expression",
            "string",
            "date_string_auto_converted",
            "ident_titlecase",
            "list_of_node_references",
            "empty_list",
            "template",
            "table_as_value",
        ],
    )
    def test_value_parsing(self, source, check):
        assert check(_val(source))

    def test_invalid_expression_body_raises_deck_format_error(self):
        with pytest.raises(DeckFormatError) as exc_info:
            parse_include_content('Vessel "v" {\n  A = <1 +>\n}')

        message = str(exc_info.value)
        assert "line 2" in message.lower()
        assert "Error in expression" in message


# ═════════════════════════════════════════════════════════════════════════════════
# Commands
# ═════════════════════════════════════════════════════════════════════════════════
class TestCommands:
    @pytest.mark.parametrize(
        ("source", "expected_name", "check_args"),
        [
            (
                'set_bunkering_allowed("LSFO", TRUE)',
                "set_bunkering_allowed",
                lambda args: args == ["LSFO", "TRUE"],
            ),
            (
                'set_process(Process("proc"), 500)',
                "set_process",
                lambda args: isinstance(args[0], NodeReference) and args[1] == 500,
            ),
        ],
        ids=["strings", "node_reference"],
    )
    def test_command_args_parsed(self, source, expected_name, check_args):
        cmd = _body(f'Vessel "v" {{ {source} }}')[0]
        assert isinstance(cmd, Command)
        assert cmd.name == expected_name
        assert check_args(cmd.args)


# ═════════════════════════════════════════════════════════════════════════════════
# Tables
# ═════════════════════════════════════════════════════════════════════════════════
class TestTables:
    @pytest.mark.parametrize(
        ("source", "expected_rows"),
        [
            (
                "Table = [ # header\n2020 0.5 # inline\n2030 1.0\n]",
                [[2020.0, 0.5], [2030.0, 1.0]],
            ),
            (
                'Table = [ "01-01-2020" 100\n"01-01-2030" 200\n]',
                [["01-01-2020", 100.0], ["01-01-2030", 200.0]],
            ),
            ("Table = [\n]", []),
            (
                'Table = [ "col_a" "col_b"\n1.0 2.0\n3.0 4.0\n]',
                [["col_a", "col_b"], [1.0, 2.0], [3.0, 4.0]],
            ),
        ],
        ids=["with_comments", "quoted_dates", "empty", "2d_with_headers"],
    )
    def test_parse_table_cells(self, source, expected_rows):
        assert parse_table_cells(source) == expected_rows


# ═════════════════════════════════════════════════════════════════════════════════
# Casing rules — NODE_TYPE requires Title case, NAME accepts any
# ═════════════════════════════════════════════════════════════════════════════════
class TestCasingRules:
    # ── node types must start uppercase ────────────────────────────
    @pytest.mark.parametrize(
        "source",
        [
            'vessel "v" { }',
            '_Vessel "v" { }',
        ],
        ids=["lowercase", "underscore_start"],
    )
    def test_invalid_node_type_rejected(self, source):
        with pytest.raises(DeckFormatError):
            parse_include_content(source)

    # ── digits in node types; attributes and commands accept any casing ──
    @pytest.mark.parametrize(
        ("source", "extract", "expected"),
        [
            ('Vessel2 "v" { }', lambda s: s[0].node_type, "Vessel2"),
            (
                'Vessel "v" { lifetime = 25 }',
                lambda s: s[0].body[0].attribute,
                "lifetime",
            ),
            ('Vessel "v" { SetFuel("oil") }', lambda s: s[0].body[0].name, "SetFuel"),
        ],
        ids=[
            "digits_in_node_type",
            "lowercase_attribute",
            "titlecase_command",
        ],
    )
    def test_casing_accepted(self, source, extract, expected):
        assert extract(parse_include_content(source)) == expected


# ═════════════════════════════════════════════════════════════════════════════════
# One statement per line enforcement
# ═════════════════════════════════════════════════════════════════════════════════
class TestOneStatementPerLine:
    @pytest.mark.parametrize(
        ("parse_fn", "source"),
        [
            (parse_include_content, 'Vessel "a" { } Vessel "b" { }'),
            (parse_include_content, 'Vessel "v" { A = 1 B = 2 }'),
            (parse_deck_content, "DEFINE { } EVENTS { }"),
        ],
        ids=["two_statements", "two_body_items", "two_deck_blocks"],
    )
    def test_rejects_multiple_statements_per_line(self, parse_fn, source):
        with pytest.raises(DeckFormatError, match="same line"):
            parse_fn(source)


# ═════════════════════════════════════════════════════════════════════════════════
# Rejection of invalid syntax
# ═════════════════════════════════════════════════════════════════════════════════
class TestSyntaxErrors:
    @pytest.mark.parametrize(
        "source",
        [
            "Vessel ship { Lifetime = 25 }",
            'Vessel "v" { Attr = ??? }',
        ],
        ids=["missing_quotes_on_name", "unrecognized_rhs"],
    )
    def test_invalid_syntax_rejected(self, source):
        with pytest.raises(DeckFormatError):
            parse_include_content(source)

    def test_wildcard_in_node_reference_produces_wildcard_reference(self):
        statements = parse_include_content('Vessel "v" { Route = Route("r_*") }')
        assignment = statements[0].body[0]
        assert isinstance(assignment.value, WildcardNodeReference)
        assert assignment.value.name == "r_*"
        assert assignment.value.type == "Route"

    @pytest.mark.parametrize("pattern", ["M*", "*"], ids=["prefix", "bare_star"])
    def test_unquoted_wildcard_in_command(self, pattern):
        cmd = _body(f'Vessel "v" {{ set_slip_fraction({pattern}, 0.03) }}')[0]
        assert cmd.name == "set_slip_fraction"
        assert cmd.args == [pattern, 0.03]


class TestReferenceScanExclude:
    """
    Every exclude entry must name a real node attribute.

    This keeps stale entries from accumulating silently in the reference-resolution
    scan.
    """

    def test_entries_are_real_node_attributes(self):
        from navigate.parser._keywords import NODE_CLASS
        from navigate.parser.parser import REFERENCE_SCAN_EXCLUDE

        attributes = set().union(
            *(vars(cls("x")).keys() for cls in NODE_CLASS.values())
        )
        for entry in REFERENCE_SCAN_EXCLUDE:
            assert entry in attributes, entry
