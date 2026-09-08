# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the restricted arithmetic evaluator behind deck ``<...>`` expressions."""
import copy
import pickle

import numpy as np
import pytest

from navigate.core.expression import Expression


class _StubNode:
    """Stands in for both the owning node and resolved node references."""

    def __init__(self, value=1., type_='Forecast'):
        self._value = value
        self.type = type_

    def __str__(self):
        return 'StubNode'

    def get(self, x=None, y=None):
        return self._value


class _EchoNode(_StubNode):
    """Node reference stub that returns the x it was evaluated with."""

    def get(self, x=None, y=None):
        return x


def _initialized(expression_text):
    expression = Expression(expression_text)
    expression.initialize(_StubNode())
    return expression


# ── arithmetic ────────────────────────────────────────────────────────────────

class TestArithmetic:

    @pytest.mark.parametrize('text, expected', [
        ('3', 3.),
        ('0.11', 0.11),
        ('0.05 * 1e6', 50000.),
        ('1 + 2', 3.),
        ('5 - 2', 3.),
        ('3 * 4', 12.),
        ('1 / 4', 0.25),
        ('2 ** 3', 8.),
        ('-3', -3.),
        ('- 3 + 5', 2.),
        ('+3', 3.),
        ('1 + 2 * 3', 7.),
        ('(1 + 2) * 3', 9.),
    ])
    def test_evaluates(self, text, expected):
        assert _initialized(text).get() == expected

    def test_huge_power_does_not_hang(self):
        # literals evaluate as floats, so this overflows immediately
        # instead of computing a 10-billion-digit integer
        with pytest.raises(OverflowError):
            _initialized('10 ** 10 ** 10').get()


# ── node references ───────────────────────────────────────────────────────────

class TestNodeReferences:

    def test_full_lifecycle(self):
        expression = Expression('1 + Forecast("x")')

        assert not expression.is_initialized()
        expression.initialize(_StubNode())
        assert expression.is_initialized()

        assert expression.node_references == ['Forecast("x")']

        expression.node_references = [_StubNode(2.)]
        assert expression.get() == 3.

    def test_reference_only(self):
        expression = _initialized('Forecast("x")')
        expression.node_references = [_StubNode(4.)]
        assert expression.get() == 4.

    def test_reference_arithmetic(self):
        expression = _initialized('0.5 * Forecast("a") + Forecast("b")')
        expression.node_references = [_StubNode(4.), _StubNode(1.)]
        assert expression.get() == 3.

    def test_multiple_distinct_references_keep_order(self):
        expression = _initialized('Forecast("a") - Variable("b")')
        assert expression.node_references == ['Forecast("a")', 'Variable("b")']

        expression.node_references = [_StubNode(4.), _StubNode(1.)]
        assert expression.get() == 3.

    def test_duplicate_reference_yields_entry_per_occurrence(self):
        expression = _initialized('Forecast("x") + Forecast("x")')
        assert expression.node_references == ['Forecast("x")', 'Forecast("x")']

        expression.node_references = [_StubNode(2.), _StubNode(2.)]
        assert expression.get() == 4.

    def test_reference_with_spacing_is_canonicalized(self):
        expression = _initialized('Forecast( "x" )')
        assert expression.node_references == ['Forecast("x")']

    def test_single_quoted_reference_is_canonicalized(self):
        expression = _initialized("Forecast('x')")
        assert expression.node_references == ['Forecast("x")']

    def test_x_is_passed_to_references(self):
        expression = _initialized('Forecast("f")')
        expression.node_references = [_EchoNode()]
        assert expression.get(x=5.) == 5.

    def test_check_consistency_allows_matching_type(self):
        expression = Expression('1 + Forecast("x")')
        expression.set_allowed_types('Forecast')
        expression.initialize(_StubNode())
        expression.check_consistency()

    def test_check_consistency_rejects_other_type(self):
        expression = Expression('1 + Forecast("x")')
        expression.set_allowed_types('Variable')
        expression.initialize(_StubNode())
        with pytest.raises(ValueError, match='references unacceptable type'):
            expression.check_consistency()

    def test_check_consistency_rejects_references_when_disallowed(self):
        expression = _initialized('1 + Forecast("x")')
        with pytest.raises(ValueError, match='does not allow node references'):
            expression.check_consistency()


# ── broadcasting and bounds ───────────────────────────────────────────────────

class TestBroadcastAndBounds:

    def test_scalar_broadcast_to_x(self):
        value = _initialized('2').get(x=np.arange(3.))
        np.testing.assert_array_equal(value, np.full(3, 2.))

    def test_scalar_broadcast_to_y(self):
        value = _initialized('2').get(y=np.arange(4.))
        np.testing.assert_array_equal(value, np.full(4, 2.))

    def test_ndarray_reference_passthrough(self):
        expression = _initialized('2 * Forecast("f")')
        expression.node_references = [_EchoNode()]

        value = expression.get(x=np.array([1., 2.]))
        np.testing.assert_array_equal(value, np.array([2., 4.]))

    def test_internal_bounds_clip_upper(self):
        expression = _initialized('10')
        expression.set_internal_bounds(0., 5.)
        assert expression.get() == 5.

    def test_internal_bounds_clip_lower(self):
        expression = _initialized('-10')
        expression.set_internal_bounds(0., 5.)
        assert expression.get() == 0.


# ── rejected syntax ───────────────────────────────────────────────────────────

class TestRejectedSyntax:

    def test_import_os_system_payload_rejected(self, tmp_path, monkeypatch):
        # the arbitrary-code-execution payload that passed the old eval() guards
        monkeypatch.chdir(tmp_path)
        expression = Expression("__import__('os').system('touch marker')")

        with pytest.raises((ValueError, NotImplementedError)):
            expression.initialize(_StubNode())

        assert not (tmp_path / 'marker').exists()

    @pytest.mark.parametrize('text, exception, match', [
        ("open('f', 'w')", ValueError, 'not a valid node reference'),
        ('Forecast("x").__class__', ValueError, 'unsupported syntax'),
        ('[1][0]', ValueError, 'unsupported syntax'),
        ('1 < 2', ValueError, 'unsupported syntax'),
        ('1 and 2', ValueError, 'unsupported syntax'),
        ('1 if 2 else 3', ValueError, 'unsupported syntax'),
        ('Forecast(f"x")', ValueError, None),
        ('lambda: 1', ValueError, 'unsupported syntax'),
        ('[1, 2]', ValueError, 'unsupported syntax'),
        ('(1, 2)', ValueError, 'unsupported syntax'),
        ('x + 1', ValueError, 'unsupported syntax'),
        ('y', ValueError, 'unsupported syntax'),
        ('Foo + 1', NotImplementedError, 'unable to support references to attributes'),
        ('True', ValueError, 'only numeric literals'),
        ("'abc'", ValueError, 'only numeric literals'),
        ('1j', ValueError, 'only numeric literals'),
        ('Forecast(name="x")', ValueError, 'exactly one positional argument'),
        ('Forecast()', ValueError, 'exactly one positional argument'),
        ('Forecast("a", "b")', ValueError, 'exactly one positional argument'),
        ('forecast("x")', ValueError, 'not a valid node reference'),
        ('Forecast(1)', ValueError, 'argument must be a string literal'),
        ('Forecast(*"x")', ValueError, 'argument must be a string literal'),
        ('Forecast(\'a"b\')', ValueError, 'must not contain a quote'),
        ('ABC("x")', ValueError, 'not a valid node reference'),
        ('5 % 2', ValueError, 'unsupported operator'),
        ('5 // 2', ValueError, 'unsupported operator'),
        ('1 | 2', ValueError, 'unsupported operator'),
        ('1 << 2', ValueError, 'unsupported operator'),
        ('not 1', ValueError, 'unsupported unary operator'),
        ('Forecast("a") * (1 - %multiplier%)', ValueError, 'Error in expression'),
        (' ', ValueError, 'Error in expression'),
        ('', ValueError, 'Error in expression'),
        ('!!!', ValueError, 'Error in expression'),
    ])
    def test_rejected(self, text, exception, match):
        with pytest.raises(exception, match=match):
            _initialized(text)


# ── copy and pickle semantics ─────────────────────────────────────────────────

class TestCopySemantics:

    def test_deepcopy_preserves_value(self):
        expression = _initialized('1 + Forecast("x")')
        expression.node_references = [_StubNode(2.)]

        clone = copy.deepcopy(expression)
        assert clone.get() == 3.

    def test_deepcopy_clone_is_independent_of_original(self):
        expression = _initialized('Forecast("x")')
        expression.node_references = [_StubNode(2.)]

        clone = copy.deepcopy(expression)
        clone.node_references = [_StubNode(5.)]

        assert expression.get() == 2.
        assert clone.get() == 5.

    def test_pickle_round_trip_after_initialize(self):
        expression = _initialized('2 * Forecast("x")')
        expression.node_references = [_StubNode(3.)]

        restored = pickle.loads(pickle.dumps(expression))
        assert restored.get() == 6.
