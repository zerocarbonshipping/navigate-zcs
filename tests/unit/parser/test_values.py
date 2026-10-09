# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Every value form the grammar reads on the right of an assignment.

One table, one row per form of `?value` in `grammar.lark`, each with the
Python value the transformer turns it into.
"""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core import Expression
from navigate.core.table_data import TableData
from navigate.exceptions import DeckFormatError
from navigate.parser._lark_parser import parse_include_content
from navigate.parser._node_reference import NodeReference, WildcardNodeReference


def _value(text: str):
    """Parse `Value = <text>` inside a node and return the value."""
    [declaration] = parse_include_content(f'Vessel "v" {{\nValue = {text}\n}}')
    [assignment] = declaration.body
    return assignment.value


# input:    | e.g. Value = [Port("a"), Port("b"),]
# expected: -> [NodeReference("Port", "a"), NodeReference("Port", "b")]
#              and Value = "01-02-2025" -> np.datetime64("2025-02-01"),
#              but Value = "2025-02-01" -> the string "2025-02-01"
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # numbers, every one a float
        ("25", 25.0),
        ("-1.5E-3", -0.0015),
        ("1.5e3", 1500.0),
        (".5", 0.5),
        ("+2", 2.0),
        ("INF", float("inf")),
        ("-INF", float("-inf")),
        # node references
        ('Route("main")', NodeReference("Route", "main")),
        ('Route("r_*")', WildcardNodeReference("Route", "r_*")),
        ('Route("r?")', WildcardNodeReference("Route", "r?")),
        ('Route("*")', WildcardNodeReference("Route", "*")),
        # identifiers: enum IDs and booleans stay strings for the setters
        ("OIL", "OIL"),
        ("TRUE", "TRUE"),
        ("BunkerIntensityPrice", "BunkerIntensityPrice"),
        ("lowercase_name", "lowercase_name"),
        # unquoted wildcards
        ("M*", "M*"),
        ("*", "*"),
        ("a?b", "a?b"),
        # quoted strings; only the dd-mm-yyyy and dd/mm/yyyy forms become dates
        ('"output"', "output"),
        ('"a b"', "a b"),
        ('""', ""),
        ('"01-02-2025"', np.datetime64("2025-02-01")),
        ('"01/02/2025"', np.datetime64("2025-02-01")),
        ('"2025-02-01"', "2025-02-01"),
        # lists
        ("[]", []),
        ("[1]", [1.0]),
        ("[1, 2,]", [1.0, 2.0]),
        ("[1, [2, 3]]", [1.0, [2.0, 3.0]]),
        (
            '[Port("a"), Port("b")]',
            [NodeReference("Port", "a"), NodeReference("Port", "b")],
        ),
        ("[OIL, METHANE]", ["OIL", "METHANE"]),
        # templates
        ("%plant_capacity%", "%plant_capacity%"),
        # a table as the value of another attribute
        ("Table = [ 2020 0.5\n2030 1.0\n]", TableData([[2020.0, 0.5], [2030.0, 1.0]])),
    ],
)
def test_value(text, expected):
    value = _value(text)

    assert value == expected
    assert type(value) is type(expected)


# input:    | Value = <1 + 2 * 3>
# expected: -> an Expression that evaluates to 7.0
@pytest.mark.parametrize(
    ("text", "expected"),
    [("<1 + 2 * 3>", 7.0), ("<(1 + 2) * 3>", 9.0), ("<-2 ** 2>", -4.0)],
)
def test_an_expression_is_parsed_into_an_evaluable_expression(text, expected):
    value = _value(text)

    assert isinstance(value, Expression)
    assert value.get() == expected


# input:    | Value = <2 * Forecast("x") + Variable("y")>
# expected: -> an Expression referencing ['Forecast("x")', 'Variable("y")']
def test_an_expression_holds_its_node_references():
    value = _value('<2 * Forecast("x") + Variable("y")>')

    assert isinstance(value, Expression)
    assert value.reference_strings == ['Forecast("x")', 'Variable("y")']


# input:    | Vessel "v" {
#           | Value = <1 +>
#           | }
# expected: -> DeckFormatError "In file 'f.inc', line 2: Error in expression <1 +>:
#              invalid syntax."
@pytest.mark.parametrize(
    ("file", "expected"),
    [
        ("", "Line 2: Error in expression <1 +>: invalid syntax."),
        (
            "f.inc",
            "In file 'f.inc', line 2: Error in expression <1 +>: invalid syntax.",
        ),
    ],
    ids=["no_file", "file"],
)
def test_an_invalid_expression_is_a_located_format_error(file, expected):
    with pytest.raises(DeckFormatError) as error:
        parse_include_content('Vessel "v" {\nValue = <1 +>\n}', file=file)

    assert str(error.value) == expected


# input:    | e.g. Value = f()
# expected: -> DeckFormatError (not a value form the grammar knows)
@pytest.mark.parametrize(
    "text",
    ["???", "%Abc%", "f()", "<>", '"unterminated'],
    ids=[
        "unknown_characters",
        "uppercase_template",
        "call",
        "empty_expression",
        "quote",
    ],
)
def test_an_unknown_value_form_is_rejected(text):
    with pytest.raises(DeckFormatError):
        _value(text)
