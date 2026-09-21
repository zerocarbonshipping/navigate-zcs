# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.util.collections — dict arithmetic, extraction, summation."""

from __future__ import annotations

import numpy as np
import pytest

from navigate.util import (
    add_dicts,
    collapse_tuple_dict,
    extract_from_dict,
    extract_from_dict_list,
    extract_from_tuple_dict,
    multiply_dicts,
    sum_dict_results,
)


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
        first_value = np.array([1.0, 2.0])
        second_value = np.array([3.0, 4.0])
        result = multiply_dicts(
            {"a": first_value}, {"a": second_value, "b": second_value}
        )

        np.testing.assert_array_equal(first_value, [1.0, 2.0])
        np.testing.assert_array_equal(second_value, [3.0, 4.0])
        np.testing.assert_array_equal(result["a"], [3.0, 8.0])
        assert not np.shares_memory(result["a"], first_value)
        assert not np.shares_memory(result["b"], second_value)


class TestSumDictResults:
    def test_sums_arrays(self):
        result = sum_dict_results(
            {"a": np.array([1.0, 2.0]), "b": np.array([3.0, 4.0])}
        )
        np.testing.assert_array_equal(result, [4.0, 6.0])

    def test_index_slices_before_summing(self):
        result = sum_dict_results(
            {"a": np.array([1.0, 2.0]), "b": np.array([3.0, 4.0])}, idx=1
        )
        assert result == 6.0

    def test_empty_dict_with_index_is_zero(self):
        assert sum_dict_results({}, idx=0) == 0.0

    def test_empty_dict_without_index_raises(self):
        with pytest.raises(ValueError, match="empty"):
            sum_dict_results({})


class TestCollapseTupleDict:
    @pytest.fixture
    def result(self):
        return {
            ("a", "x"): np.array([1.0, 2.0]),
            ("a", "y"): np.array([10.0, 20.0]),
            ("b", "x"): np.array([100.0, 200.0]),
        }

    def test_no_collapse_returns_dict_unchanged(self, result):
        assert collapse_tuple_dict(result) == result

    def test_collapse_over_secondary_keys(self, result):
        collapsed = collapse_tuple_dict(result, key1=True)
        assert collapsed.keys() == {"a", "b"}
        np.testing.assert_array_equal(collapsed["a"], [11.0, 22.0])
        np.testing.assert_array_equal(collapsed["b"], [100.0, 200.0])

    def test_collapse_over_primary_keys(self, result):
        collapsed = collapse_tuple_dict(result, key2=True)
        assert collapsed.keys() == {"x", "y"}
        np.testing.assert_array_equal(collapsed["x"], [101.0, 202.0])
        np.testing.assert_array_equal(collapsed["y"], [10.0, 20.0])

    def test_collapse_both(self, result):
        collapsed = collapse_tuple_dict(result, key1=True, key2=True)
        np.testing.assert_array_equal(collapsed, [111.0, 222.0])


class TestExtractFromDict:
    def test_key_and_index(self):
        assert extract_from_dict({"a": np.array([1.0, 2.0])}, "a", 1) == 2.0

    def test_scalar_value_passes_through_the_index(self):
        assert extract_from_dict({"a": 2.0}, "a", 0) == 2.0

    def test_whole_dict_sliced(self):
        result = extract_from_dict({"a": np.array([1.0, 2.0])}, idx=0)
        assert result == {"a": 1.0}

    def test_whole_dict_fancy_index(self):
        source = {"a": np.array([1.0, 2.0, 3.0])}
        result = extract_from_dict(source, idx=np.array([2, 0]))
        np.testing.assert_array_equal(result["a"], [3.0, 1.0])

    def test_whole_dict_does_not_alias_the_input(self):
        source = {"a": np.array([1.0, 2.0])}
        assert extract_from_dict(source) is not source

    def test_numpy_scalar_index(self):
        assert extract_from_dict({"a": np.array([1.0, 2.0])}, "a", np.int64(1)) == 2.0

    def test_fancy_index_returns_a_copy(self):
        value = np.array([1.0, 2.0, 3.0])
        result = extract_from_dict({"a": value}, "a", np.array([2, 0]))
        np.testing.assert_array_equal(result, [3.0, 1.0])
        assert not np.shares_memory(result, value)


class TestExtractFromTupleDict:
    @pytest.fixture
    def result(self):
        return {
            ("a", "x"): np.array([1.0, 2.0]),
            ("a", "y"): np.array([10.0, 20.0]),
            ("b", "x"): np.array([100.0, 200.0]),
        }

    def test_both_keys_give_the_sliced_value(self, result):
        assert extract_from_tuple_dict(result, "a", "y", 1) == 20.0

    def test_key1_collects_by_key2(self, result):
        assert extract_from_tuple_dict(result, key1="a", idx=0) == {"x": 1.0, "y": 10.0}

    def test_key2_collects_by_key1(self, result):
        assert extract_from_tuple_dict(result, key2="x", idx=1) == {
            "a": 2.0,
            "b": 200.0,
        }

    def test_no_keys_slice_the_whole_dict(self, result):
        sliced = extract_from_tuple_dict(result, idx=0)
        assert sliced == {("a", "x"): 1.0, ("a", "y"): 10.0, ("b", "x"): 100.0}

    def test_no_index_leaves_values_unsliced(self, result):
        whole = extract_from_tuple_dict(result, key1="b")
        np.testing.assert_array_equal(whole["x"], [100.0, 200.0])

    def test_empty_input_stays_empty(self):
        assert extract_from_tuple_dict({}, idx=0) == {}


class TestExtractFromDictList:
    @pytest.fixture
    def result(self):
        return {"a": [np.array([1.0, 2.0]), np.array([3.0, 4.0])]}

    def test_key_and_index(self, result):
        assert extract_from_dict_list(result, "a", 1) == [2.0, 4.0]

    def test_key_and_slice(self, result):
        arrays = extract_from_dict_list(result, "a", np.s_[1:])
        np.testing.assert_array_equal(arrays, [[2.0], [4.0]])

    def test_key_and_fancy_index(self, result):
        arrays = extract_from_dict_list(result, "a", np.array([1, 0]))
        np.testing.assert_array_equal(arrays, [[2.0, 1.0], [4.0, 3.0]])

    def test_whole_dict_sliced(self, result):
        sliced = extract_from_dict_list(result, idx=0)
        assert sliced == {"a": [1.0, 3.0]}
