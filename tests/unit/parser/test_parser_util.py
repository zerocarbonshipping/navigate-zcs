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
    CopyStmt,
    DateStmt,
    DefineBlock,
    EndTimeline,
    EventsBlock,
    GeneralNodeDecl,
    ImportStmt,
    IncludeDirective,
    LoadModuleDirective,
    NodeDecl,
    SourceLoc,
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
# SourceLoc
# ═════════════════════════════════════════════════════════════════════════════════
class TestSourceLoc:
    def test_immutable(self):
        loc = SourceLoc(file="test.inc", line=10, deck_line=5)
        with pytest.raises(AttributeError):
            loc.line = 20

    def test_defaults(self):
        loc = SourceLoc()
        assert loc.file == ""
        assert loc.line == 0
        assert loc.deck_line == 0


# ═════════════════════════════════════════════════════════════════════════════════
# string_to_date
# ═════════════════════════════════════════════════════════════════════════════════
class TestStringToDate:
    def test_dash_format(self):
        assert string_to_date('01-01-2020') == np.datetime64('2020-01-01')

    def test_slash_format(self):
        assert string_to_date('15/06/2030') == np.datetime64('2030-06-15')

    def test_invalid_no_separator(self):
        with pytest.raises(ValueError):
            string_to_date('01012020')

    def test_iso_format(self):
        assert string_to_date('2020-01-01') == np.datetime64('2020-01-01')

    def test_strips_whitespace_and_quotes(self):
        assert string_to_date('  "01-01-2020"  ') == np.datetime64('2020-01-01')

    def test_invalid_date(self):
        with pytest.raises(ValueError):
            string_to_date('99-99-9999')


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

    def test_define_and_events(self):
        text = 'DEFINE {\n  Include "nav.inc"\n}\nEVENTS {\n  Load DefaultTimeStepYearly\n}'
        blocks = parse_deck_content(text, file="test.nav")
        assert len(blocks) == 2
        assert isinstance(blocks[0], DefineBlock)
        assert isinstance(blocks[1], EventsBlock)

    def test_empty_blocks(self):
        blocks = parse_deck_content('DEFINE { }\nEVENTS { }')
        assert len(blocks) == 2
        assert blocks[0].directives == []
        assert blocks[1].directives == []

    def test_source_loc_carries_file(self):
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
        stmts = parse_include_content('Vessel "my_ship" { Lifetime = 25 }')
        decl = stmts[0]
        assert isinstance(decl, NodeDecl)
        assert decl.node_type == 'Vessel'
        assert decl.name == 'my_ship'
        assert decl.body[0].attribute == 'Lifetime'
        assert decl.body[0].value == 25.0

    def test_general_node(self):
        stmts = parse_include_content('ModelDefinition { Attribute = TRUE }')
        decl = stmts[0]
        assert isinstance(decl, GeneralNodeDecl)
        assert decl.node_type == 'ModelDefinition'
        assert decl.body[0].value == 'TRUE'

    def test_empty_body(self):
        stmts = parse_include_content('Vessel "v" { }')
        assert stmts[0].body == []

    # ── copy / import / date / timeline ────────────────────────────
    def test_copy_stmt(self):
        s = parse_include_content('Copy Vessel "original" "copy"')[0]
        assert isinstance(s, CopyStmt)
        assert s.node_type == 'Vessel'
        assert s.src == 'original'
        assert s.dst == 'copy'

    def test_import_stmt(self):
        s = parse_include_content('Import Vessel "ship"')[0]
        assert isinstance(s, ImportStmt)
        assert s.node_type == 'Vessel'
        assert s.name == 'ship'

    def test_date_stmt(self):
        assert isinstance(parse_include_content('Date "01-01-2025"')[0], DateStmt)

    def test_start_end_timeline(self):
        stmts = parse_include_content('Start\nEnd')
        assert isinstance(stmts[0], StartTimeline)
        assert isinstance(stmts[1], EndTimeline)

    # ── multiple statements ────────────────────────────────────────
    def test_multiple_statements(self):
        text = 'Vessel "a" { Lifetime = 25 }\nDate "01-01-2030"\nVessel "a" { Lifetime = 30 }'
        assert len(parse_include_content(text)) == 3

    def test_empty_input(self):
        assert parse_include_content('') == []

    def test_comments_ignored(self):
        stmts = parse_include_content('# comment\nVessel "v" { Lifetime = 25 } # inline')
        assert len(stmts) == 1

    # ── source location ───────────────────────────────────────────
    def test_source_loc_on_nodes(self):
        stmts = parse_include_content('Vessel "v" {\n  Lifetime = 25\n}', file="test.inc")
        assert stmts[0].source.file == "test.inc"
        assert stmts[0].source.line == 1
        assert stmts[0].body[0].source.file == "test.inc"
        assert stmts[0].body[0].source.line == 2


# ═════════════════════════════════════════════════════════════════════════════════
# Values — all types that can appear on the RHS of an assignment
# ═════════════════════════════════════════════════════════════════════════════════
class TestValues:

    # ── numbers ────────────────────────────────────────────────────
    def test_integer(self):
        assert _val('Value = 25') == 25.0

    def test_negative(self):
        assert _val('Value = -0.5') == -0.5

    def test_scientific(self):
        assert _val('Value = 1.5E-3') == pytest.approx(0.0015)

    def test_inf(self):
        assert _val('Value = INF') == float('inf')

    def test_negative_inf(self):
        assert _val('Value = -INF') == float('-inf')

    # ── node references ────────────────────────────────────────────
    def test_node_reference(self):
        val = _val('Route = Route("main")')
        assert isinstance(val, NodeReference)

    # ── expressions ────────────────────────────────────────────────
    def test_expression(self):
        val = _val('Value = <1 + Forecast("x")>')
        assert isinstance(val, Expression)

    # ── strings ────────────────────────────────────────────────────
    def test_string(self):
        assert _val('Dir = "output"') == 'output'

    def test_date_string_auto_converted(self):
        assert _val('StartDate = "01-01-2025"') == np.datetime64('2025-01-01')

    # ── identifiers ────────────────────────────────────────────────
    def test_ident_uppercase(self):
        assert _val('FuelType = OIL') == 'OIL'

    def test_ident_with_underscore(self):
        assert _val('Mode = TRANSPORT_NOMINAL') == 'TRANSPORT_NOMINAL'

    def test_ident_titlecase(self):
        assert _val('Price = BunkerIntensityPrice') == 'BunkerIntensityPrice'

    # ── lists ──────────────────────────────────────────────────────
    def test_list_of_node_refs(self):
        val = _val('Ports = [Port("a"), Port("b")]')
        assert isinstance(val, list) and len(val) == 2
        assert all(isinstance(v, NodeReference) for v in val)

    def test_empty_list(self):
        assert _val('Items = []') == []

    # ── templates ──────────────────────────────────────────────────
    def test_template(self):
        assert _val('Capacity = %plant_capacity%') == '%plant_capacity%'

    # ── tables as values ───────────────────────────────────────────
    def test_table_as_value(self):
        val = _val('Curve = Table = [ 2020 0.5\n2030 1.0\n]')
        assert isinstance(val, TableData)
        assert val.rows == [[2020.0, 0.5], [2030.0, 1.0]]


# ═════════════════════════════════════════════════════════════════════════════════
# Commands
# ═════════════════════════════════════════════════════════════════════════════════
class TestCommands:

    def test_command_with_strings(self):
        cmd = _body('Vessel "v" { set_bunkering_allowed("LSFO", TRUE) }')[0]
        assert isinstance(cmd, Command)
        assert cmd.name == 'set_bunkering_allowed'
        assert cmd.args == ['LSFO', 'TRUE']

    def test_command_with_number(self):
        cmd = _body('Vessel "v" { set_cost("fuel", 100.0) }')[0]
        assert cmd.args == ['fuel', 100.0]

    def test_command_with_node_reference(self):
        cmd = _body('Vessel "v" { set_process(Process("proc"), 500) }')[0]
        assert isinstance(cmd.args[0], NodeReference)


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

    def testparse_table_cells_basic(self):
        rows = parse_table_cells('Table = [ 2020 0.5\n2030 1.0\n]')
        assert rows == [[2020.0, 0.5], [2030.0, 1.0]]

    def testparse_table_cells_with_comments(self):
        rows = parse_table_cells('Table = [ # header\n2020 0.5 # inline\n2030 1.0\n]')
        assert len(rows) == 2

    def testparse_table_cells_quoted_dates(self):
        rows = parse_table_cells('Table = [ "01-01-2020" 100\n"01-01-2030" 200\n]')
        assert rows[0] == ['01-01-2020', 100.0]
        assert rows[1] == ['01-01-2030', 200.0]

    def testparse_table_cells_empty(self):
        assert parse_table_cells('Table = [\n]') == []

    def testparse_table_cells_2d_with_headers(self):
        rows = parse_table_cells('Table = [ "col_a" "col_b"\n1.0 2.0\n3.0 4.0\n]')
        assert len(rows) == 3
        assert rows[0] == ['col_a', 'col_b']
        assert rows[1] == [1.0, 2.0]


# ═════════════════════════════════════════════════════════════════════════════════
# Casing rules — NODE_TYPE requires Title case, NAME accepts any
# ═════════════════════════════════════════════════════════════════════════════════
class TestCasingRules:

    # ── node types must start uppercase ────────────────────────────
    def test_lowercase_node_type_rejected(self):
        with pytest.raises(DeckFormatError):
            parse_include_content('vessel "v" { }')

    def test_underscore_start_node_type_rejected(self):
        with pytest.raises(DeckFormatError):
            parse_include_content('_Vessel "v" { }')

    # ── digits allowed in node types ───────────────────────────────
    def test_digits_in_node_type(self):
        stmts = parse_include_content('Vessel2 "v" { }')
        assert stmts[0].node_type == 'Vessel2'

    # ── attributes accept any casing ───────────────────────────────
    def test_lowercase_attribute(self):
        assert _body('Vessel "v" { lifetime = 25 }')[0].attribute == 'lifetime'

    def test_uppercase_attribute(self):
        assert _body('Vessel "v" { Lifetime = 25 }')[0].attribute == 'Lifetime'

    def test_attribute_with_digits(self):
        assert _body('Vessel "v" { co2_factor = 0.5 }')[0].attribute == 'co2_factor'

    # ── commands accept any casing ─────────────────────────────────
    def test_lowercase_command(self):
        cmd = _body('Vessel "v" { set_fuel("oil") }')[0]
        assert cmd.name == 'set_fuel'

    def test_titlecase_command(self):
        cmd = _body('Vessel "v" { SetFuel("oil") }')[0]
        assert cmd.name == 'SetFuel'


# ═════════════════════════════════════════════════════════════════════════════════
# One statement per line enforcement
# ═════════════════════════════════════════════════════════════════════════════════
class TestOneStatementPerLine:

    def test_two_stmts_same_line_rejected(self):
        with pytest.raises(VisitError, match="same line"):
            parse_include_content('Vessel "a" { } Vessel "b" { }')

    def test_two_body_items_same_line_rejected(self):
        with pytest.raises(VisitError, match="same line"):
            parse_include_content('Vessel "v" { A = 1 B = 2 }')

    def test_two_deck_blocks_same_line_rejected(self):
        with pytest.raises(VisitError, match="same line"):
            parse_deck_content('DEFINE { } EVENTS { }')

    def test_separate_lines_accepted(self):
        stmts = parse_include_content('Vessel "a" { }\nVessel "b" { }')
        assert len(stmts) == 2

    def test_body_items_separate_lines_accepted(self):
        body = _body('Vessel "v" {\n  A = 1\n  B = 2\n}')
        assert len(body) == 2


# ═════════════════════════════════════════════════════════════════════════════════
# Rejection of invalid syntax
# ═════════════════════════════════════════════════════════════════════════════════
class TestSyntaxErrors:

    def test_missing_braces(self):
        with pytest.raises(DeckFormatError):
            parse_include_content('Vessel "ship" Lifetime = 25')

    def test_missing_quotes_on_name(self):
        with pytest.raises(DeckFormatError):
            parse_include_content('Vessel ship { Lifetime = 25 }')

    def test_double_equals(self):
        with pytest.raises(DeckFormatError):
            parse_include_content('Vessel "v" { Attr == 1.0 }')

    def test_unrecognized_rhs(self):
        with pytest.raises(DeckFormatError):
            parse_include_content('Vessel "v" { Attr = ??? }')

    def test_wildcard_in_node_ref_produces_wildcard_reference(self):
        stmts = parse_include_content('Vessel "v" { Route = Route("r_*") }')
        assignment = stmts[0].body[0]
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
        from navigate.core.nodes.curve import Curve
        from navigate.parser.parser import REFERENCE_SCAN_EXCLUDE

        curve = Curve('c')
        for entry in REFERENCE_SCAN_EXCLUDE:
            assert entry in vars(curve), entry
