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

    def test_integer_literal(self):
        assert _initialized('3').get() == 3.

    def test_float_literal(self):
        assert _initialized('0.11').get() == 0.11

    def test_scientific_notation(self):
        assert _initialized('0.05 * 1e6').get() == 50000.

    def test_addition(self):
        assert _initialized('1 + 2').get() == 3.

    def test_subtraction(self):
        assert _initialized('5 - 2').get() == 3.

    def test_multiplication(self):
        assert _initialized('3 * 4').get() == 12.

    def test_division(self):
        assert _initialized('1 / 4').get() == 0.25

    def test_power(self):
        assert _initialized('2 ** 3').get() == 8.

    def test_unary_minus(self):
        assert _initialized('-3').get() == -3.

    def test_spaced_unary_minus(self):
        assert _initialized('- 3 + 5').get() == 2.

    def test_unary_plus(self):
        assert _initialized('+3').get() == 3.

    def test_precedence(self):
        assert _initialized('1 + 2 * 3').get() == 7.

    def test_parentheses(self):
        assert _initialized('(1 + 2) * 3').get() == 9.

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

    def test_repr_returns_deck_text(self):
        assert repr(Expression('1 + Forecast("x")')) == '1 + Forecast("x")'

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

    def test_open_rejected(self):
        with pytest.raises(ValueError, match='not a valid node reference'):
            _initialized("open('f', 'w')")

    def test_attribute_access_rejected(self):
        with pytest.raises(ValueError, match='unsupported syntax'):
            _initialized('Forecast("x").__class__')

    def test_subscript_rejected(self):
        with pytest.raises(ValueError, match='unsupported syntax'):
            _initialized('[1][0]')

    def test_comparison_rejected(self):
        with pytest.raises(ValueError, match='unsupported syntax'):
            _initialized('1 < 2')

    def test_boolean_op_rejected(self):
        with pytest.raises(ValueError, match='unsupported syntax'):
            _initialized('1 and 2')

    def test_ternary_rejected(self):
        with pytest.raises(ValueError, match='unsupported syntax'):
            _initialized('1 if 2 else 3')

    def test_fstring_rejected(self):
        with pytest.raises(ValueError):
            _initialized('Forecast(f"x")')

    def test_lambda_rejected(self):
        with pytest.raises(ValueError, match='unsupported syntax'):
            _initialized('lambda: 1')

    def test_list_rejected(self):
        with pytest.raises(ValueError, match='unsupported syntax'):
            _initialized('[1, 2]')

    def test_tuple_rejected(self):
        with pytest.raises(ValueError, match='unsupported syntax'):
            _initialized('(1, 2)')

    def test_bare_lowercase_name_rejected(self):
        with pytest.raises(ValueError, match='unsupported syntax'):
            _initialized('x + 1')

    def test_bare_y_rejected(self):
        with pytest.raises(ValueError, match='unsupported syntax'):
            _initialized('y')

    def test_bare_capitalized_name_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match='unable to support references to attributes'):
            _initialized('Foo + 1')

    def test_true_rejected(self):
        with pytest.raises(ValueError, match='only numeric literals'):
            _initialized('True')

    def test_string_literal_rejected(self):
        with pytest.raises(ValueError, match='only numeric literals'):
            _initialized("'abc'")

    def test_complex_literal_rejected(self):
        with pytest.raises(ValueError, match='only numeric literals'):
            _initialized('1j')

    def test_keyword_argument_rejected(self):
        with pytest.raises(ValueError, match='exactly one positional argument'):
            _initialized('Forecast(name="x")')

    def test_zero_arguments_rejected(self):
        with pytest.raises(ValueError, match='exactly one positional argument'):
            _initialized('Forecast()')

    def test_two_arguments_rejected(self):
        with pytest.raises(ValueError, match='exactly one positional argument'):
            _initialized('Forecast("a", "b")')

    def test_lowercase_call_rejected(self):
        with pytest.raises(ValueError, match='not a valid node reference'):
            _initialized('forecast("x")')

    def test_non_string_argument_rejected(self):
        with pytest.raises(ValueError, match='argument must be a string literal'):
            _initialized('Forecast(1)')

    def test_starred_argument_rejected(self):
        with pytest.raises(ValueError, match='argument must be a string literal'):
            _initialized('Forecast(*"x")')

    def test_argument_containing_quote_rejected(self):
        with pytest.raises(ValueError, match='must not contain a quote'):
            _initialized('Forecast(\'a"b\')')

    def test_all_caps_call_is_value_error_not_attribute_reference(self):
        with pytest.raises(ValueError, match='not a valid node reference'):
            _initialized('ABC("x")')

    def test_modulo_rejected(self):
        with pytest.raises(ValueError, match='unsupported operator'):
            _initialized('5 % 2')

    def test_floor_division_rejected(self):
        with pytest.raises(ValueError, match='unsupported operator'):
            _initialized('5 // 2')

    def test_bitwise_or_rejected(self):
        with pytest.raises(ValueError, match='unsupported operator'):
            _initialized('1 | 2')

    def test_shift_rejected(self):
        with pytest.raises(ValueError, match='unsupported operator'):
            _initialized('1 << 2')

    def test_unary_not_rejected(self):
        with pytest.raises(ValueError, match='unsupported unary operator'):
            _initialized('not 1')

    def test_template_placeholder_is_syntax_error(self):
        with pytest.raises(ValueError, match='Error in expression'):
            _initialized('Forecast("a") * (1 - %multiplier%)')

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValueError, match='Error in expression'):
            _initialized(' ')

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match='Error in expression'):
            _initialized('')

    def test_garbage_rejected(self):
        with pytest.raises(ValueError, match='Error in expression'):
            _initialized('!!!')


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
