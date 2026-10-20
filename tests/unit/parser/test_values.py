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
from navigate.core.expression import node_references
from navigate.core.nodes.variable import Variable
from navigate.exceptions import DeckError
from navigate.parser._lark_parser import (
    ExpressionSyntax,
    NodeReference,
    parse_include_content,
)


def _value(text: str):
    """Parse `Value = <text>` inside a node and return the value."""
    [declaration] = parse_include_content(f'Vessel "v" {{\nValue = {text}\n}}')
    [assignment] = declaration.body
    return assignment.value


# input:    | e.g. Value = [Port("a"), Port("b"),]
# expected: -> [NodeReference("Port", "a"), NodeReference("Port", "b")]
#              and Value = "01-02-2025" -> np.datetime64("2025-02-01")
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
        # node references; a glob in the name is the same reference, flagged
        ('Route("main")', NodeReference("Route", "main")),
        ('Route("r_*")', NodeReference("Route", "r_*")),
        ('Route("r?")', NodeReference("Route", "r?")),
        ('Route("*")', NodeReference("Route", "*")),
        # identifiers: enum IDs and booleans stay strings for the setters
        ("OIL", "OIL"),
        ("TRUE", "TRUE"),
        ("BunkerIntensityPrice", "BunkerIntensityPrice"),
        ("lowercase_name", "lowercase_name"),
        # quoted strings; the dd-mm-yyyy, dd/mm/yyyy and ISO forms become dates
        ('"output"', "output"),
        ('"a b"', "a b"),
        ('""', ""),
        ('"01-02-2025"', np.datetime64("2025-02-01")),
        ('"01/02/2025"', np.datetime64("2025-02-01")),
        ('"2025-02-01"', np.datetime64("2025-02-01")),
        ("2025-02-01", np.datetime64("2025-02-01")),
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
    ],
)
def test_value(text, expected):
    value = _value(text)

    assert value == expected
    assert type(value) is type(expected)


# input:    | Route("r_*")  /  Route("main")
# expected: -> is_wildcard True  /  False
@pytest.mark.parametrize(
    ("text", "expected"), [('Route("r_*")', True), ('Route("main")', False)]
)
def test_a_node_reference_knows_whether_its_name_is_a_glob(text, expected):
    assert _value(text).is_wildcard is expected


# input:    | Value = <1 + 2 * 3>
# expected: -> an expression that evaluates to 7.0 once built
@pytest.mark.parametrize(
    ("text", "expected"),
    [("<1 + 2 * 3>", 7.0), ("<(1 + 2) * 3>", 9.0), ("<-2 ** 2>", -4.0)],
)
def test_an_expression_is_parsed_into_an_evaluable_expression(text, expected):
    value = _value(text)

    assert isinstance(value, ExpressionSyntax)
    expression = Expression(value.text, value.root, {}, Variable("holder"))
    assert expression.get() == expected


# input:    | Value = <2 * Forecast("x") + Variable("y")>
# expected: -> an expression referencing Forecast("x") then Variable("y")
def test_an_expression_holds_its_node_references():
    value = _value('<2 * Forecast("x") + Variable("y")>')

    assert isinstance(value, ExpressionSyntax)
    assert list(node_references(value.root)) == [
        NodeReference("Forecast", "x"),
        NodeReference("Variable", "y"),
    ]


# input:    | Vessel "v" {
#           | Value = <1 +>
#           | }
# expected: -> DeckError "In file 'f.inc', line 2: ... Unexpected '>' ..."
@pytest.mark.parametrize(
    ("file", "expected"),
    [("", "Line 2:"), ("f.inc", "In file 'f.inc', line 2:")],
    ids=["no_file", "file"],
)
def test_an_invalid_expression_is_a_located_syntax_error(file, expected):
    with pytest.raises(DeckError) as error:
        parse_include_content('Vessel "v" {\nValue = <1 +>\n}', file=file)

    assert str(error.value).startswith(expected)
    assert "Unexpected '>'" in str(error.value)


# input:    | e.g. Value = f()
# expected: -> DeckError (not a value form the grammar knows)
@pytest.mark.parametrize(
    "text",
    ["???", "%plant_capacity%", "f()", "<>", '"unterminated'],
    ids=["unknown_characters", "template", "call", "empty_expression", "quote"],
)
def test_an_unknown_value_form_is_rejected(text):
    with pytest.raises(DeckError):
        _value(text)
