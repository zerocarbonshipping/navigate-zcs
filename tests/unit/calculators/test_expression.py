# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The restricted arithmetic behind a deck `<...>` expression.

An expression is parsed with `ast` and evaluated by its own tree, never by
`eval`: numeric literals, + - * / **, unary signs, and calculator references
written `Type("name")`. Everything else is refused when the expression is
built.
"""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core.expression import Expression
from navigate.core.nodes.variable import Variable


def _variable(name: str, value: float) -> Variable:
    variable = Variable(name)
    variable.set_value(value)
    return variable


def _resolved(text: str, **values: float) -> Expression:
    """Build an expression whose Variable references read the given values."""
    variables = {
        f'Variable("{name}")': _variable(name, v) for name, v in values.items()
    }
    expression = Expression(text)
    expression.set_allowed_types("Variable")
    expression.resolve(
        _variable("owner", 0.0),
        lambda reference_string, location: variables[reference_string],
    )
    return expression


# evaluates small arithmetic expressions and compares with the hand result:
# precedence, brackets, power, unary minus, division and 1e6 literals.
# catches: a wrong operator table or grouping, e.g. 2 ** 3 ** 2 read as
# (2 ** 3) ** 2 = 64 instead of 512.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1 + 2 * 3", 7.0),
        ("(1 + 2) * 3", 9.0),
        # right-associative: 2 ** (3 ** 2) = 2 ** 9
        ("2 ** 3 ** 2", 512.0),
        ("- 3 + 5", 2.0),
        ("1 / 4", 0.25),
        ("0.05 * 1e6", 50000.0),
    ],
    ids=["precedence", "parentheses", "power", "unary", "division", "sci_literal"],
)
def test_arithmetic(text, expected):
    assert Expression(text).get() == pytest.approx(expected)


# evaluates an expression that multiplies two Variables and subtracts 2, with
# the Variables resolved to real nodes.
# catches: references swapped or read as 0, so 3 * 4 - 2 gives the wrong number.
def test_references_read_their_nodes():
    # 3 * 4 - 2 = 10
    expression = _resolved('Variable("a") * Variable("b") - 2', a=3.0, b=4.0)

    assert expression.get() == pytest.approx(10.0)


# reads a constant expression with an array input and expects an array of the
# same length, not a single number.
# catches: a constant returned as a scalar, which breaks code that indexes the
# result per vessel or per year.
def test_a_constant_is_broadcast_to_an_array_input():
    np.testing.assert_array_equal(Expression("2").get(np.arange(3.0)), np.full(3, 2.0))


# builds expressions with code injection, attribute access, names, booleans,
# modulo, `not` and empty text, and expects each to be refused.
# catches: a parser change that lets `__import__('os')` or other Python through
# from a deck file.
@pytest.mark.parametrize(
    ("text", "exception", "match"),
    [
        ("__import__('os').system('true')", ValueError, "not a valid node reference"),
        ('Variable("x").__class__', ValueError, "unsupported syntax"),
        # x is an argument of the getter, not a name an expression can read
        ("x + 1", ValueError, "unsupported syntax"),
        ("Foo + 1", NotImplementedError, "unable to support references"),
        ("True", ValueError, "only numeric literals"),
        ('Variable(name="x")', ValueError, "exactly one positional argument"),
        ("Variable(1)", ValueError, "argument must be a string literal"),
        ("5 % 2", ValueError, "unsupported operator"),
        ("not 1", ValueError, "unsupported unary operator"),
        ("", ValueError, "Error in expression"),
    ],
    ids=[
        "code_injection",
        "attribute_access",
        "bare_name",
        "unknown_name",
        "bool",
        "keyword_argument",
        "non_string_argument",
        "modulo",
        "not",
        "empty",
    ],
)
def test_syntax_outside_the_arithmetic_is_refused(text, exception, match):
    with pytest.raises(exception, match=match):
        Expression(text)
