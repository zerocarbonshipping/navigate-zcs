# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests for the restricted arithmetic evaluator behind deck ``<...>`` expressions."""

from __future__ import annotations

import copy

import numpy as np
import pytest

from navigate.core.expression import Expression


class _StubNode:
    """Stands in for both the owning node and resolved node references."""

    def __init__(self, value=1.0, type_="Forecast"):
        self._value = value
        self.type = type_

    def __str__(self):
        return "StubNode"

    def get(self, x=None, y=None):
        return self._value


class _EchoNode(_StubNode):
    """Node reference stub that returns the x it was evaluated with."""

    def get(self, x=None, y=None):
        return x


# -- arithmetic ----------------------------------------------------------------


class TestArithmetic:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("3", 3.0),
            ("0.11", 0.11),
            ("0.05 * 1e6", 50000.0),
            ("1 + 2", 3.0),
            ("5 - 2", 3.0),
            ("3 * 4", 12.0),
            ("1 / 4", 0.25),
            ("2 ** 3", 8.0),
            ("-3", -3.0),
            ("- 3 + 5", 2.0),
            ("+3", 3.0),
            ("1 + 2 * 3", 7.0),
            ("(1 + 2) * 3", 9.0),
        ],
    )
    def test_evaluates(self, text, expected):
        assert Expression(text).get() == expected

    def test_huge_power_does_not_hang(self):
        # literals evaluate as floats, so this overflows immediately
        # instead of computing a 10-billion-digit integer
        with pytest.raises(OverflowError):
            Expression("10 ** 10 ** 10").get()


# -- node references -----------------------------------------------------------


class TestNodeReferences:
    def test_full_lifecycle(self):
        expression = Expression('1 + Forecast("x")')

        assert expression.reference_strings == ['Forecast("x")']

        expression.node_references = [_StubNode(2.0)]
        assert expression.get() == 3.0

    def test_reference_only(self):
        expression = Expression('Forecast("x")')
        expression.node_references = [_StubNode(4.0)]
        assert expression.get() == 4.0

    def test_reference_arithmetic(self):
        expression = Expression('0.5 * Forecast("a") + Forecast("b")')
        expression.node_references = [_StubNode(4.0), _StubNode(1.0)]
        assert expression.get() == 3.0

    def test_multiple_distinct_references_keep_order(self):
        expression = Expression('Forecast("a") - Variable("b")')
        assert expression.reference_strings == ['Forecast("a")', 'Variable("b")']

        expression.node_references = [_StubNode(4.0), _StubNode(1.0)]
        assert expression.get() == 3.0

    def test_duplicate_reference_yields_entry_per_occurrence(self):
        expression = Expression('Forecast("x") + Forecast("x")')
        assert expression.reference_strings == ['Forecast("x")', 'Forecast("x")']

        expression.node_references = [_StubNode(2.0), _StubNode(2.0)]
        assert expression.get() == 4.0

    def test_reference_with_spacing_is_canonicalized(self):
        expression = Expression('Forecast( "x" )')
        assert expression.reference_strings == ['Forecast("x")']

    def test_single_quoted_reference_is_canonicalized(self):
        expression = Expression("Forecast('x')")
        assert expression.reference_strings == ['Forecast("x")']

    def test_x_is_passed_to_references(self):
        expression = Expression('Forecast("f")')
        expression.node_references = [_EchoNode()]
        assert expression.get(x=5.0) == 5.0

    def test_check_consistency_allows_matching_type(self):
        expression = Expression('1 + Forecast("x")')
        expression.set_allowed_types("Forecast")
        expression.check_consistency()

    def test_check_consistency_rejects_other_type(self):
        expression = Expression('1 + Forecast("x")')
        expression.set_allowed_types("Variable")
        with pytest.raises(ValueError, match="references unacceptable type"):
            expression.check_consistency()

    def test_check_consistency_rejects_references_when_disallowed(self):
        expression = Expression('1 + Forecast("x")')
        with pytest.raises(ValueError, match="does not allow node references"):
            expression.check_consistency()

    def test_resolve_binds_first_node_and_leaves_second_unbound(self):
        expression = Expression("1 + 2")
        first, second = _StubNode(), _StubNode()

        def read_reference(reference_string, location):
            raise AssertionError("no reference to read")

        expression.resolve(first, read_reference)
        expression.resolve(second, read_reference)

        assert expression._node is first
        assert expression.node_references == []


# -- broadcasting and bounds ---------------------------------------------------


class TestBroadcastAndBounds:
    def test_scalar_broadcast_to_x(self):
        value = Expression("2").get(x=np.arange(3.0))
        np.testing.assert_array_equal(value, np.full(3, 2.0))

    def test_scalar_broadcast_to_y(self):
        value = Expression("2").get(y=np.arange(4.0))
        np.testing.assert_array_equal(value, np.full(4, 2.0))

    def test_ndarray_reference_passthrough(self):
        expression = Expression('2 * Forecast("f")')
        expression.node_references = [_EchoNode()]

        value = expression.get(x=np.array([1.0, 2.0]))
        np.testing.assert_array_equal(value, np.array([2.0, 4.0]))

    def test_internal_bounds_clip_upper(self):
        expression = Expression("10")
        expression.set_internal_bounds(0.0, 5.0)
        assert expression.get() == 5.0

    def test_internal_bounds_clip_lower(self):
        expression = Expression("-10")
        expression.set_internal_bounds(0.0, 5.0)
        assert expression.get() == 0.0

    @pytest.mark.parametrize(
        ("text", "flags", "message"),
        [
            # 0 sits on the exclusive lower bound, -1 beyond it
            ("0", {"inclusive_lower": False}, r"must be > 0\.0, but got 0\.0"),
            ("-1", {"inclusive_lower": False}, r"must be > 0\.0, but got -1\.0"),
            ("5", {"inclusive_upper": False}, r"must be < 5\.0, but got 5\.0"),
        ],
        ids=["lower_at_bound", "lower_beyond", "upper_at_bound"],
    )
    def test_exclusive_internal_bound_raises(self, text, flags, message):
        expression = Expression(text)
        expression.set_internal_bounds(0.0, 5.0, **flags)

        with pytest.raises(ValueError, match=rf"Expression <{text}>: {message}"):
            expression.get()

    def test_exclusive_internal_bound_reports_the_extreme_entry(self):
        # of the entries 2, 0 and -3 the lowest breaks the bound furthest
        expression = Expression('Forecast("f")')
        expression.node_references = [_EchoNode()]
        expression.set_internal_bounds(0.0, np.inf, inclusive_lower=False)

        with pytest.raises(ValueError, match=r"must be > 0\.0, but got -3\.0"):
            expression.get(x=np.array([2.0, 0.0, -3.0]))

    def test_value_inside_an_exclusive_bound_passes(self):
        expression = Expression("0.5")
        expression.set_internal_bounds(0.0, 5.0, inclusive_lower=False)
        assert expression.get() == 0.5


# -- rejected syntax -----------------------------------------------------------


class TestRejectedSyntax:
    def test_import_os_system_payload_rejected(self, tmp_path, monkeypatch):
        # the arbitrary-code-execution payload that passed the old eval() guards
        monkeypatch.chdir(tmp_path)

        with pytest.raises((ValueError, NotImplementedError)):
            Expression("__import__('os').system('touch marker')")

        assert not (tmp_path / "marker").exists()

    @pytest.mark.parametrize(
        ("text", "exception", "match"),
        [
            ("open('f', 'w')", ValueError, "not a valid node reference"),
            ('Forecast("x").__class__', ValueError, "unsupported syntax"),
            ("[1][0]", ValueError, "unsupported syntax"),
            ("1 < 2", ValueError, "unsupported syntax"),
            ("1 and 2", ValueError, "unsupported syntax"),
            ("1 if 2 else 3", ValueError, "unsupported syntax"),
            ('Forecast(f"x")', ValueError, None),
            ("lambda: 1", ValueError, "unsupported syntax"),
            ("[1, 2]", ValueError, "unsupported syntax"),
            ("(1, 2)", ValueError, "unsupported syntax"),
            ("x + 1", ValueError, "unsupported syntax"),
            ("y", ValueError, "unsupported syntax"),
            (
                "Foo + 1",
                NotImplementedError,
                "unable to support references to attributes",
            ),
            ("True", ValueError, "only numeric literals"),
            ("'abc'", ValueError, "only numeric literals"),
            ("1j", ValueError, "only numeric literals"),
            ('Forecast(name="x")', ValueError, "exactly one positional argument"),
            ("Forecast()", ValueError, "exactly one positional argument"),
            ('Forecast("a", "b")', ValueError, "exactly one positional argument"),
            ('forecast("x")', ValueError, "not a valid node reference"),
            ("Forecast(1)", ValueError, "argument must be a string literal"),
            ('Forecast(*"x")', ValueError, "argument must be a string literal"),
            ("Forecast('a\"b')", ValueError, "must not contain a quote"),
            ('ABC("x")', ValueError, "not a valid node reference"),
            ("5 % 2", ValueError, "unsupported operator"),
            ("5 // 2", ValueError, "unsupported operator"),
            ("1 | 2", ValueError, "unsupported operator"),
            ("1 << 2", ValueError, "unsupported operator"),
            ("not 1", ValueError, "unsupported unary operator"),
            ('Forecast("a") * (1 - %multiplier%)', ValueError, "Error in expression"),
            (" ", ValueError, "Error in expression"),
            ("", ValueError, "Error in expression"),
            ("!!!", ValueError, "Error in expression"),
        ],
    )
    def test_rejected(self, text, exception, match):
        with pytest.raises(exception, match=match):
            Expression(text)


# -- copy semantics ------------------------------------------------------------


class TestCopySemantics:
    def test_deepcopy_preserves_value(self):
        expression = Expression('1 + Forecast("x")')
        expression.node_references = [_StubNode(2.0)]

        clone = copy.deepcopy(expression)
        assert clone.get() == 3.0

    def test_deepcopy_clone_is_independent_of_original(self):
        expression = Expression('Forecast("x")')
        expression.node_references = [_StubNode(2.0)]

        clone = copy.deepcopy(expression)
        clone.node_references = [_StubNode(5.0)]

        assert expression.get() == 2.0
        assert clone.get() == 5.0
