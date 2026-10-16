# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The grammar and transformer: which statements a deck and an include file hold.

Every statement form of `grammar.lark` is parsed here into the AST dataclass it
produces, compared whole, source location included. The value forms on the
right of an assignment are in `test_values.py`, the table cells in
`test_tables.py`.
"""

from __future__ import annotations

import pytest

from navigate.core.table_data import TableData
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
    SourceLocation,
    StartTimeline,
    parse_deck_content,
    parse_include_content,
)
from navigate.parser._node_reference import NodeReference

FILE = "f.inc"


def _at(line: int) -> SourceLocation:
    return SourceLocation(FILE, line)


# ── deck files (.nav) ─────────────────────────────────────────────────────────


# input:    | DEFINE {
#           |   Include "a.inc"
#           |   Load DefaultEmission
#           | }
# expected: -> DefineBlock([IncludeDirective("a.inc"), LoadModuleDirective(
#              "DefaultEmission")]), with each directive on its own source line
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", []),
        ("DEFINE {\n}", [DefineBlock([], _at(1))]),
        ("EVENTS {\n}", [EventsBlock([], _at(1))]),
        (
            'DEFINE {\n  Include "a.inc"\n  Load DefaultEmission\n}\nEVENTS {\n'
            '  Include "b.inc"\n}',
            [
                DefineBlock(
                    [
                        IncludeDirective("a.inc", _at(2)),
                        LoadModuleDirective("DefaultEmission", _at(3)),
                    ],
                    _at(1),
                ),
                EventsBlock([IncludeDirective("b.inc", _at(6))], _at(5)),
            ],
        ),
    ],
    ids=["empty_deck", "empty_define", "empty_events", "include_and_load"],
)
def test_deck_blocks_and_directives(text, expected):
    assert parse_deck_content(text, file=FILE) == expected


# input:    | e.g. DEFINE {
#           |        Copy Vessel "a" "b"
#           |      }
# expected: -> DeckFormatError (a .nav block holds only Include and Load)
@pytest.mark.parametrize(
    "text",
    ['Vessel "v" {\n}', 'DEFINE {\n  Copy Vessel "a" "b"\n}', "DEFINE {\n  Load x\n}"],
    ids=["statement_outside_a_block", "statement_in_a_block", "lowercase_module"],
)
def test_a_deck_holds_only_blocks_of_directives(text):
    with pytest.raises(DeckFormatError):
        parse_deck_content(text)


# ── include files (.inc) ──────────────────────────────────────────────────────


# input:    | e.g. Copy Vessel "a" "b"
# expected: -> CopyStatement("Vessel", "a", "b", line 1)
#              and Import Vessel "a_*" -> ImportStatement("Vessel", "a_*", line 1)
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('Vessel "v" {\n}', NodeDeclaration("Vessel", "v", [], _at(1))),
        ("ModelDefinition {\n}", GeneralNodeDeclaration("ModelDefinition", [], _at(1))),
        ('Copy Vessel "a" "b"', CopyStatement("Vessel", "a", "b", _at(1))),
        ('Import Vessel "a"', ImportStatement("Vessel", "a", _at(1))),
        ('Import Vessel "a_*"', ImportStatement("Vessel", "a_*", _at(1))),
        ('Date "01-01-2030"', DateStatement("01-01-2030", _at(1))),
        ("Start", StartTimeline(_at(1))),
        ("End", EndTimeline(_at(1))),
    ],
    ids=[
        "node_declaration",
        "general_node_declaration",
        "copy",
        "import",
        "wildcard_import",
        "date",
        "start",
        "end",
    ],
)
def test_include_statement(text, expected):
    assert parse_include_content(text, file=FILE) == [expected]


# input:    | Date "2030-01-01"
# expected: -> DateStatement("2030-01-01"), the text kept as written
def test_a_date_statement_keeps_its_text():
    # a Date statement is read as a date by the parser, not the transformer,
    # which also accepts the ISO form
    assert parse_include_content('Date "2030-01-01"') == [
        DateStatement("2030-01-01", SourceLocation("", 1))
    ]


# input:    | Vessel "v" {
#           | set_x("a", 2, OIL, M*, *, Port("p"))
#           | }
# expected: -> Command("set_x", ["a", 2.0, "OIL", "M*", "*",
#              NodeReference("Port", "p")], line 2)
@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("Lifetime = 25", Assignment("Lifetime", 25.0, _at(2))),
        ("set_x()", Command("set_x", [], _at(2))),
        (
            'set_x("a", 2, OIL, M*, *, Port("p"))',
            Command(
                "set_x",
                ["a", 2.0, "OIL", "M*", "*", NodeReference("Port", "p")],
                _at(2),
            ),
        ),
        (
            "Table = [\n 1 2\n 3 4\n]",
            Assignment("Table", TableData([[1.0, 2.0], [3.0, 4.0]]), _at(2)),
        ),
    ],
    ids=["assignment", "command_without_arguments", "command_arguments", "table"],
)
def test_body_item(body, expected):
    [declaration] = parse_include_content(f'Vessel "v" {{\n{body}\n}}', file=FILE)
    assert declaration.body == [expected]


# input:    | # comment
#           | Vessel "v" {
#           |   # another
#           |   Lifetime = 25 # inline
#           | }
# expected: -> the comments are dropped; Vessel is on line 2, Lifetime on line 4
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
def test_comments_are_skipped_and_lines_located(parse, text, children):
    [statement] = parse(text, file=FILE)
    [child] = children(statement)

    assert statement.source == _at(2)
    assert child.source == _at(4)


# ── casing: a node type is Title case, an attribute or command any case ──────


# input:    | vessel "v" { }
# expected: -> DeckFormatError (a node type must start with a capital letter)
@pytest.mark.parametrize(
    "text", ['vessel "v" {\n}', '_Vessel "v" {\n}'], ids=["lowercase", "underscore"]
)
def test_a_node_type_starts_with_a_capital(text):
    with pytest.raises(DeckFormatError):
        parse_include_content(text)


# input:    | Vessel "v" {
#           | lifetime = 1
#           | }
# expected: -> NodeDeclaration("Vessel", "v", [Assignment("lifetime", 1.0)]); the
#              grammar accepts it and leaves the casing to the attribute registry
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('Vessel2 "v" {\n}', NodeDeclaration("Vessel2", "v", [], _at(1))),
        (
            'Vessel "v" {\nlifetime = 1\n}',
            NodeDeclaration(
                "Vessel", "v", [Assignment("lifetime", 1.0, _at(2))], _at(1)
            ),
        ),
        (
            'Vessel "v" {\nSetFuel()\n}',
            NodeDeclaration("Vessel", "v", [Command("SetFuel", [], _at(2))], _at(1)),
        ),
    ],
    ids=["digits_in_node_type", "lowercase_attribute", "titlecase_command"],
)
def test_casing_left_to_the_registries(text, expected):
    assert parse_include_content(text, file=FILE) == [expected]


# ── one statement per line ────────────────────────────────────────────────────


# input:    | Vessel "v" { A = 1 B = 2 }
# expected: -> DeckFormatError "Line 1: Multiple statements on the same line.
#              Each statement must be on its own line."
@pytest.mark.parametrize(
    ("parse", "text"),
    [
        (parse_include_content, 'Vessel "a" { } Vessel "b" { }'),
        (parse_include_content, 'Vessel "v" { A = 1 B = 2 }'),
        (parse_deck_content, "DEFINE { } EVENTS { }"),
    ],
    ids=["two_statements", "two_body_items", "two_deck_blocks"],
)
def test_one_statement_per_line(parse, text):
    with pytest.raises(DeckFormatError) as error:
        parse(text)

    assert str(error.value) == (
        "Line 1: Multiple statements on the same line. "
        "Each statement must be on its own line."
    )


# ── syntax errors ─────────────────────────────────────────────────────────────


# input:    | Vessel ship { }
# expected: -> DeckFormatError "In file 'f.inc', line 1:
#              1 | Vessel ship { }
#              |        ^
#              Unexpected a name - expected '{' or a quoted string"
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Vessel ship { }",
            "In file 'f.inc', line 1:\n\n"
            "  1 | Vessel ship { }\n"
            "    |        ^\n"
            "Unexpected a name — expected '{' or a quoted string",
        ),
        (
            'Vessel "v" {\n  A =\n}',
            "In file 'f.inc', line 3:\n\n"
            "  3 | }\n"
            "    | ^\n"
            "Unexpected '}' — expected an expression, '[', a name, a node type, "
            "a quoted string, a number, a Table = [...] block, a template or "
            "WILDCARD_NAME",
        ),
    ],
    ids=["unquoted_name", "missing_value"],
)
def test_an_unexpected_token_is_located_and_names_what_was_expected(text, expected):
    with pytest.raises(DeckFormatError) as error:
        parse_include_content(text, file=FILE)

    assert str(error.value) == expected


# input:    | Vessel "v" {
#           |   A = ???
#           | }
# expected: -> DeckFormatError starting "In file 'f.inc', line 2:", with a caret
#              under the first '?'
def test_an_unknown_character_is_located():
    with pytest.raises(DeckFormatError) as error:
        parse_include_content('Vessel "v" {\n  A = ???\n}', file=FILE)

    assert str(error.value).startswith(
        "In file 'f.inc', line 2:\n\n  2 |   A = ???\n    |       ^"
    )
