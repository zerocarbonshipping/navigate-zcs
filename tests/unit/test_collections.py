# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.util.collections — dict arithmetic, summation, slicing."""

from __future__ import annotations

import numpy as np
import pytest

from navigate.util import (
    add_dicts,
    collapse_tuple_dict,
    multiply_dicts,
    slice_dict,
    slice_dict_list,
    slice_list,
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


class TestSliceList:
    @pytest.fixture
    def result(self):
        return [np.array([1.0, 2.0, 3.0]), np.array([4.0, 5.0, 6.0])]

    def test_scalar_index_gives_a_list_of_floats(self, result):
        assert slice_list(result, 0) == [1.0, 4.0]

    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            ((np.s_[1:],), [[2.0, 3.0], [5.0, 6.0]]),
            ((np.array([2, 0]),), [[3.0, 1.0], [6.0, 4.0]]),
            ((), [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]),
        ],
        ids=["slice", "fancy_index", "no_index_slices_the_whole_timeline"],
    )
    def test_index_kinds(self, result, args, expected):
        np.testing.assert_array_equal(slice_list(result, *args), expected)


class TestSliceDict:
    @pytest.fixture
    def result(self):
        return {"a": np.array([1.0, 2.0, 3.0])}

    def test_scalar_index_gives_a_dict_of_floats(self, result):
        assert slice_dict(result, 0) == {"a": 1.0}

    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            ((np.s_[1:],), [2.0, 3.0]),
            ((np.array([2, 0]),), [3.0, 1.0]),
            ((np.int64(1),), 2.0),
            ((), [1.0, 2.0, 3.0]),
        ],
        ids=[
            "slice",
            "fancy_index",
            "numpy_scalar_index",
            "no_index_slices_the_whole_timeline",
        ],
    )
    def test_index_kinds(self, result, args, expected):
        np.testing.assert_array_equal(slice_dict(result, *args)["a"], expected)

    def test_fancy_index_returns_a_copy(self, result):
        sliced = slice_dict(result, np.array([2, 0]))
        assert not np.shares_memory(sliced["a"], result["a"])

    def test_whole_dict_is_not_the_input_object(self, result):
        assert slice_dict(result) is not result


class TestSliceDictList:
    @pytest.fixture
    def result(self):
        return {"a": [np.array([1.0, 2.0]), np.array([3.0, 4.0])]}

    def test_scalar_index_gives_a_dict_of_floats(self, result):
        assert slice_dict_list(result, 0) == {"a": [1.0, 3.0]}

    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            ((np.s_[1:],), [[2.0], [4.0]]),
            ((np.array([1, 0]),), [[2.0, 1.0], [4.0, 3.0]]),
            ((), [[1.0, 2.0], [3.0, 4.0]]),
        ],
        ids=["slice", "fancy_index", "no_index_slices_the_whole_timeline"],
    )
    def test_index_kinds(self, result, args, expected):
        np.testing.assert_array_equal(slice_dict_list(result, *args)["a"], expected)
