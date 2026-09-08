# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the Lark-based parser: grammar, transformer, and helpers."""
import numpy as np
import pytest
from lark.exceptions import VisitError

from navigate.core import Expression, NodeReference
from navigate.core.node_reference import WildcardNodeReference
from navigate.exceptions import DeckFormatError
from navigate.parser._lark_parser import (
    Assignment,
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

    @pytest.mark.parametrize("raw, expected", [
        ('01-01-2020', np.datetime64('2020-01-01')),
        ('15/06/2030', np.datetime64('2030-06-15')),
        ('2020-01-01', np.datetime64('2020-01-01')),
        ('  "01-01-2020"  ', np.datetime64('2020-01-01')),
    ], ids=['dash_format', 'slash_format', 'iso_format', 'strips_whitespace_and_quotes'])
    def test_parses_valid_formats(self, raw, expected):
        assert string_to_date(raw) == expected

    @pytest.mark.parametrize("raw", [
        '01012020',
        '99-99-9999',
    ], ids=['no_separator', 'invalid_date'])
    def test_rejects_invalid_input(self, raw):
        with pytest.raises(ValueError):
            string_to_date(raw)


# ═════════════════════════════════════════════════════════════════════════════════
# Deck-level parsing (.nav) — DEFINE / EVENTS / Include / Load
# ═════════════════════════════════════════════════════════════════════════════════
class TestDeckParsing:

    def test_define_block(self):
        blocks = parse_deck_content('DEFINE {\n  Include "nav.inc"\n  Load DefaultEmission\n}')
        assert len(blocks) == 1
        b = blocks[0]
        assert isinstance(b, DefineBlock)
        assert isinstance(b.directives[0], IncludeDirective)
        assert b.directives[0].path == 'nav.inc'
        assert isinstance(b.directives[1], LoadModuleDirective)
        assert b.directives[1].name == 'DefaultEmission'

    def test_events_block(self):
        blocks = parse_deck_content('EVENTS {\n  Load DefaultTimeStepYearly\n}')
        assert len(blocks) == 1
        assert isinstance(blocks[0], EventsBlock)
        assert blocks[0].directives[0].name == 'DefaultTimeStepYearly'

    def test_empty_blocks(self):
        blocks = parse_deck_content('DEFINE { }\nEVENTS { }')
        assert len(blocks) == 2
        assert blocks[0].directives == []
        assert blocks[1].directives == []

    def test_source_location_carries_file(self):
        blocks = parse_deck_content('DEFINE { Include "f.inc" }', file="my.nav")
        assert blocks[0].source.file == "my.nav"
        assert blocks[0].directives[0].source.file == "my.nav"

    def test_comments_ignored(self):
        text = '# comment\nDEFINE {\n  # another\n  Include "f.inc"\n}'
        blocks = parse_deck_content(text)
        assert len(blocks[0].directives) == 1

    def test_old_simulation_nav_rejected(self):
        with pytest.raises(DeckFormatError):
            parse_deck_content('SIMULATION NAV { }')


# ═════════════════════════════════════════════════════════════════════════════════
# Include-level statements (.inc)
# ═════════════════════════════════════════════════════════════════════════════════
class TestStatements:

    # ── node declarations ──────────────────────────────────────────
    def test_named_node(self):
        statements = parse_include_content('Vessel "my_ship" { Lifetime = 25 }')
        declaration = statements[0]
        assert isinstance(declaration, NodeDeclaration)
        assert declaration.node_type == 'Vessel'
        assert declaration.name == 'my_ship'
        assert declaration.body[0].attribute == 'Lifetime'
        assert declaration.body[0].value == 25.0

    def test_general_node(self):
        statements = parse_include_content('ModelDefinition { Attribute = TRUE }')
        declaration = statements[0]
        assert isinstance(declaration, GeneralNodeDeclaration)
        assert declaration.node_type == 'ModelDefinition'
        assert declaration.body[0].value == 'TRUE'

    def test_empty_body(self):
        statements = parse_include_content('Vessel "v" { }')
        assert statements[0].body == []

    # ── copy / import ───────────────────────────────────────────────
    def test_copy_statement(self):
        s = parse_include_content('Copy Vessel "original" "copy"')[0]
        assert isinstance(s, CopyStatement)
        assert s.node_type == 'Vessel'
        assert s.copy_from == 'original'
        assert s.copy_to == 'copy'

    def test_import_statement(self):
        s = parse_include_content('Import Vessel "ship"')[0]
        assert isinstance(s, ImportStatement)
        assert s.node_type == 'Vessel'
        assert s.name == 'ship'

    # ── statement type recognition ──────────────────────────────────
    @pytest.mark.parametrize("text, index, expected_type", [
        ('Date "01-01-2025"', 0, DateStatement),
        ('Start\nEnd', 0, StartTimeline),
        ('Start\nEnd', 1, EndTimeline),
    ], ids=['date', 'start', 'end'])
    def test_statement_type_recognized(self, text, index, expected_type):
        assert isinstance(parse_include_content(text)[index], expected_type)

    # ── multiple statements ────────────────────────────────────────
    def test_multiple_statements(self):
        text = 'Vessel "a" { Lifetime = 25 }\nDate "01-01-2030"\nVessel "a" { Lifetime = 30 }'
        assert len(parse_include_content(text)) == 3

    def test_empty_input(self):
        assert parse_include_content('') == []

    def test_comments_ignored(self):
        statements = parse_include_content('# comment\nVessel "v" { Lifetime = 25 } # inline')
        assert len(statements) == 1

    # ── source location ───────────────────────────────────────────
    def test_source_location_on_nodes(self):
        statements = parse_include_content('Vessel "v" {\n  Lifetime = 25\n}', file="test.inc")
        assert statements[0].source.file == "test.inc"
        assert statements[0].source.line == 1
        assert statements[0].body[0].source.file == "test.inc"
        assert statements[0].body[0].source.line == 2


# ═════════════════════════════════════════════════════════════════════════════════
# Values — all types that can appear on the RHS of an assignment
# ═════════════════════════════════════════════════════════════════════════════════
class TestValues:

    @pytest.mark.parametrize("source, check", [
        ('Value = 25', lambda v: v == 25.0),
        ('Value = -0.5', lambda v: v == -0.5),
        ('Value = 1.5E-3', lambda v: v == pytest.approx(0.0015)),
        ('Value = INF', lambda v: v == float('inf')),
        ('Value = -INF', lambda v: v == float('-inf')),
        ('Route = Route("main")', lambda v: isinstance(v, NodeReference)),
        ('Value = <1 + Forecast("x")>', lambda v: isinstance(v, Expression)),
        ('Dir = "output"', lambda v: v == 'output'),
        ('StartDate = "01-01-2025"', lambda v: v == np.datetime64('2025-01-01')),
        ('FuelType = OIL', lambda v: v == 'OIL'),
        ('Mode = TRANSPORT_NOMINAL', lambda v: v == 'TRANSPORT_NOMINAL'),
        ('Price = BunkerIntensityPrice', lambda v: v == 'BunkerIntensityPrice'),
        ('Ports = [Port("a"), Port("b")]',
         lambda v: isinstance(v, list) and len(v) == 2 and all(isinstance(p, NodeReference) for p in v)),
        ('Items = []', lambda v: v == []),
        ('Capacity = %plant_capacity%', lambda v: v == '%plant_capacity%'),
        ('Curve = Table = [ 2020 0.5\n2030 1.0\n]',
         lambda v: isinstance(v, TableData) and v.rows == [[2020.0, 0.5], [2030.0, 1.0]]),
    ], ids=[
        'integer', 'negative', 'scientific', 'inf', 'negative_inf', 'node_reference', 'expression', 'string',
        'date_string_auto_converted', 'ident_uppercase', 'ident_with_underscore', 'ident_titlecase',
        'list_of_node_references', 'empty_list', 'template', 'table_as_value',
    ])
    def test_value_parsing(self, source, check):
        assert check(_val(source))


# ═════════════════════════════════════════════════════════════════════════════════
# Commands
# ═════════════════════════════════════════════════════════════════════════════════
class TestCommands:

    @pytest.mark.parametrize("source, expected_name, check_args", [
        ('set_bunkering_allowed("LSFO", TRUE)', 'set_bunkering_allowed',
         lambda args: args == ['LSFO', 'TRUE']),
        ('set_cost("fuel", 100.0)', 'set_cost',
         lambda args: args == ['fuel', 100.0]),
        ('set_process(Process("proc"), 500)', 'set_process',
         lambda args: isinstance(args[0], NodeReference) and args[1] == 500),
    ], ids=['strings', 'number', 'node_reference'])
    def test_command_args_parsed(self, source, expected_name, check_args):
        cmd = _body(f'Vessel "v" {{ {source} }}')[0]
        assert isinstance(cmd, Command)
        assert cmd.name == expected_name
        assert check_args(cmd.args)


# ═════════════════════════════════════════════════════════════════════════════════
# Tables
# ═════════════════════════════════════════════════════════════════════════════════
class TestTables:

    def test_table_block_in_body(self):
        item = _body('Vessel "v" { Table = [ 2020 0.5\n2030 1.0\n] }')[0]
        assert isinstance(item, Assignment)
        assert item.attribute == 'Table'
        assert isinstance(item.value, TableData)
        assert item.value.rows == [[2020.0, 0.5], [2030.0, 1.0]]

    @pytest.mark.parametrize("source, expected_rows", [
        ('Table = [ 2020 0.5\n2030 1.0\n]',
         [[2020.0, 0.5], [2030.0, 1.0]]),
        ('Table = [ # header\n2020 0.5 # inline\n2030 1.0\n]',
         [[2020.0, 0.5], [2030.0, 1.0]]),
        ('Table = [ "01-01-2020" 100\n"01-01-2030" 200\n]',
         [['01-01-2020', 100.0], ['01-01-2030', 200.0]]),
        ('Table = [\n]', []),
        ('Table = [ "col_a" "col_b"\n1.0 2.0\n3.0 4.0\n]',
         [['col_a', 'col_b'], [1.0, 2.0], [3.0, 4.0]]),
    ], ids=['basic', 'with_comments', 'quoted_dates', 'empty', '2d_with_headers'])
    def test_parse_table_cells(self, source, expected_rows):
        assert parse_table_cells(source) == expected_rows


# ═════════════════════════════════════════════════════════════════════════════════
# Casing rules — NODE_TYPE requires Title case, NAME accepts any
# ═════════════════════════════════════════════════════════════════════════════════
class TestCasingRules:

    # ── node types must start uppercase ────────────────────────────
    @pytest.mark.parametrize("source", [
        'vessel "v" { }',
        '_Vessel "v" { }',
    ], ids=['lowercase', 'underscore_start'])
    def test_invalid_node_type_rejected(self, source):
        with pytest.raises(DeckFormatError):
            parse_include_content(source)

    # ── digits in node types; attributes and commands accept any casing ──
    @pytest.mark.parametrize("source, extract, expected", [
        ('Vessel2 "v" { }', lambda s: s[0].node_type, 'Vessel2'),
        ('Vessel "v" { lifetime = 25 }', lambda s: s[0].body[0].attribute, 'lifetime'),
        ('Vessel "v" { Lifetime = 25 }', lambda s: s[0].body[0].attribute, 'Lifetime'),
        ('Vessel "v" { co2_factor = 0.5 }', lambda s: s[0].body[0].attribute, 'co2_factor'),
        ('Vessel "v" { set_fuel("oil") }', lambda s: s[0].body[0].name, 'set_fuel'),
        ('Vessel "v" { SetFuel("oil") }', lambda s: s[0].body[0].name, 'SetFuel'),
    ], ids=['digits_in_node_type', 'lowercase_attribute', 'uppercase_attribute',
            'attribute_with_digits', 'lowercase_command', 'titlecase_command'])
    def test_casing_accepted(self, source, extract, expected):
        assert extract(parse_include_content(source)) == expected


# ═════════════════════════════════════════════════════════════════════════════════
# One statement per line enforcement
# ═════════════════════════════════════════════════════════════════════════════════
class TestOneStatementPerLine:

    @pytest.mark.parametrize("parse_fn, source", [
        (parse_include_content, 'Vessel "a" { } Vessel "b" { }'),
        (parse_include_content, 'Vessel "v" { A = 1 B = 2 }'),
        (parse_deck_content, 'DEFINE { } EVENTS { }'),
    ], ids=['two_statements', 'two_body_items', 'two_deck_blocks'])
    def test_rejects_multiple_statements_per_line(self, parse_fn, source):
        with pytest.raises(VisitError, match="same line"):
            parse_fn(source)

    @pytest.mark.parametrize("get_items", [
        lambda: parse_include_content('Vessel "a" { }\nVessel "b" { }'),
        lambda: _body('Vessel "v" {\n  A = 1\n  B = 2\n}'),
    ], ids=['statements', 'body_items'])
    def test_accepts_one_statement_per_line(self, get_items):
        assert len(get_items()) == 2


# ═════════════════════════════════════════════════════════════════════════════════
# Rejection of invalid syntax
# ═════════════════════════════════════════════════════════════════════════════════
class TestSyntaxErrors:

    @pytest.mark.parametrize("source", [
        'Vessel "ship" Lifetime = 25',
        'Vessel ship { Lifetime = 25 }',
        'Vessel "v" { Attr == 1.0 }',
        'Vessel "v" { Attr = ??? }',
    ], ids=['missing_braces', 'missing_quotes_on_name', 'double_equals', 'unrecognized_rhs'])
    def test_invalid_syntax_rejected(self, source):
        with pytest.raises(DeckFormatError):
            parse_include_content(source)

    def test_wildcard_in_node_reference_produces_wildcard_reference(self):
        statements = parse_include_content('Vessel "v" { Route = Route("r_*") }')
        assignment = statements[0].body[0]
        assert isinstance(assignment.value, WildcardNodeReference)
        assert assignment.value.pattern == "r_*"
        assert assignment.value.type == "Route"

    def test_unquoted_wildcard_in_command(self):
        cmd = _body('Vessel "v" { set_slip_fraction(M*, 0.03) }')[0]
        assert cmd.name == "set_slip_fraction"
        assert cmd.args == ["M*", 0.03]

    def test_bare_star_in_command(self):
        cmd = _body('Vessel "v" { set_energy_saving(*, 0.03) }')[0]
        assert cmd.args == ["*", 0.03]


class TestReferenceScanExclude:
    """Every exclude entry must name a real node attribute, so stale entries
    cannot accumulate silently in the reference-resolution scan."""

    def test_entries_are_real_node_attributes(self):
        from navigate.parser._keywords import NODE_CLASS
        from navigate.parser.parser import REFERENCE_SCAN_EXCLUDE

        attributes = set().union(*(vars(cls('x')).keys() for cls in NODE_CLASS.values()))
        for entry in REFERENCE_SCAN_EXCLUDE:
            assert entry in attributes, entry
