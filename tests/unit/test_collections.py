# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.util.collections — dict arithmetic."""

from __future__ import annotations

import numpy as np

from navigate.util import add_dicts, multiply_dicts


class TestAddDicts:
    def test_overlapping_and_unique_keys(self):
        result = add_dicts({"a": 1.0, "b": 2.0}, {"b": 3.0, "c": 4.0})
        assert result == {"a": 1.0, "b": 5.0, "c": 4.0}

    def test_array_values(self):
        result = add_dicts(
            {"a": np.array([1.0, 2.0])},
            {"a": np.array([3.0, 4.0]), "b": np.array([5.0, 6.0])},
        )
        np.testing.assert_array_equal(result["a"], [4.0, 6.0])
        np.testing.assert_array_equal(result["b"], [5.0, 6.0])

    def test_empty_call_returns_empty_dict(self):
        assert add_dicts() == {}

    def test_inputs_left_unmutated_and_unaliased(self):
        first_value = np.array([1.0, 2.0])
        second_value = np.array([3.0, 4.0])
        result = add_dicts({"a": first_value}, {"a": second_value, "b": second_value})

        np.testing.assert_array_equal(first_value, [1.0, 2.0])
        np.testing.assert_array_equal(second_value, [3.0, 4.0])
        assert not np.shares_memory(result["a"], first_value)
        assert not np.shares_memory(result["b"], second_value)


class TestMultiplyDicts:
    def test_overlapping_and_unique_keys(self):
        result = multiply_dicts({"a": 2.0, "b": 3.0}, {"b": 4.0, "c": 5.0})
        assert result == {"a": 2.0, "b": 12.0, "c": 5.0}

    def test_array_times_float_dict(self):
        result = multiply_dicts({"a": np.array([1.0, 2.0])}, {"a": 3.0})
        np.testing.assert_array_equal(result["a"], [3.0, 6.0])

    def test_empty_call_returns_empty_dict(self):
        assert multiply_dicts() == {}

    def test_inputs_left_unmutated_and_unaliased(self):
        value = np.array([1.0, 2.0])
        result = multiply_dicts({"a": value})

        np.testing.assert_array_equal(value, [1.0, 2.0])
        assert not np.shares_memory(result["a"], value)
