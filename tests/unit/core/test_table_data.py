# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the TableData-to-numpy builders behind ``Table = [...]`` assignments.

The undated builders feed ``Curve``/``Surface`` and the dated ones
``Forecast``/``Timetable``, which dispatch on the returned dtype in
``replace_reference_table`` — so the numeric-table cases pin the dated
builders' float arrays as much as the dated ones pin their dates.

The returned arrays are described positionally here — first, second, third —
because ``dsl_reference.md`` and the code disagree on which one is "the
x-axis". The consumers fix the meaning: ``check_table2d_input`` requires
``z.shape == (x.size, y.size)`` and ``Surface.get(x, y)`` indexes in that
order.
"""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core.table_data import (
    TableData,
    build_table_1d,
    build_table_1d_dated,
    build_table_2d,
    build_table_2d_dated,
)

# the deck literals used throughout; 01-01-2024 and 01-01-2030 as np.datetime64
DATE_A = np.datetime64("2024-01-01", "D")
DATE_B = np.datetime64("2030-01-01", "D")


# the Surface example from dsl_reference.md: 3 header values, 3 data rows of 4
SURFACE_ROWS = [
    [0.0, 1.0, 2.0],
    [0.0, 0.0, 1.0, 2.0],
    [10.0, 3.0, 4.0, 12.0],
    [20.0, 20.0, 21.0, 22.0],
]


# ── shared by the builders ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "build",
    [build_table_1d, build_table_1d_dated, build_table_2d, build_table_2d_dated],
)
def test_an_empty_table_is_empty_float_arrays(build):
    # with no row to read, no date was seen, and the consumers' dtype dispatch
    # has to land on the numeric branch
    arrays = build(TableData([]))

    assert all(array.dtype == np.float64 for array in arrays)
    assert all(array.size == 0 for array in arrays)


@pytest.mark.parametrize(
    ("build", "rows"),
    [
        (build_table_1d_dated, [[2020.0, 0.5], [2030.0, 1.0]]),
        (build_table_2d_dated, SURFACE_ROWS),
    ],
    ids=["1d", "2d"],
)
def test_dated_builder_does_not_coerce_a_numeric_first_column(build, rows):
    # Forecast/Timetable branch on the dtype afterwards, so a numeric deck
    # must stay numeric
    first, *_ = build(TableData(rows))
    assert first.dtype == np.float64


@pytest.mark.parametrize(
    ("build", "rows"),
    [
        (build_table_1d_dated, [[2020.0, 0.5], ["01-01-2030", 1.0]]),
        (
            build_table_2d_dated,
            [[0.0, 1.0], ["01-01-2024", 3.0, 4.0], [2030.0, 5.0, 6.0]],
        ),
    ],
    ids=["1d", "2d"],
)
def test_mixed_first_column_rejected(build, rows):
    with pytest.raises(ValueError, match="consistently number or date"):
        build(TableData(rows))


# ── build_table_1d ────────────────────────────────────────────────────────────


class TestBuildTable1D:
    def test_numeric_table(self):
        x, y = build_table_1d(TableData([[2020.0, 0.5], [2030.0, 1.0]]))

        np.testing.assert_array_equal(x, np.array([2020.0, 2030.0]))
        np.testing.assert_array_equal(y, np.array([0.5, 1.0]))

    def test_dated_table(self):
        x, y = build_table_1d_dated(
            TableData([["01-01-2024", 0.5], ["01-01-2030", 1.0]])
        )

        assert x.dtype == np.dtype("datetime64[D]")
        np.testing.assert_array_equal(x, np.array([DATE_A, DATE_B]))
        np.testing.assert_array_equal(y, np.array([0.5, 1.0]))

    def test_date_rejected_by_the_undated_builder(self):
        with pytest.raises(ValueError, match="'x' must be a number"):
            build_table_1d(TableData([["01-01-2024", 0.5]]))

    def test_non_numeric_y_rejected(self):
        with pytest.raises(ValueError, match="'y' must be a number"):
            build_table_1d(TableData([[2020.0, "high"]]))

    def test_wrong_column_count_rejected(self):
        with pytest.raises(ValueError, match="exactly 2 columns"):
            build_table_1d(TableData([[2020.0, 0.5, 1.0]]))


# ── build_table_2d ────────────────────────────────────────────────────────────


class TestBuildTable2D:
    def test_numeric_table(self):
        x, y, z = build_table_2d(TableData(SURFACE_ROWS))

        np.testing.assert_array_equal(y, np.array([0.0, 1.0, 2.0]))
        np.testing.assert_array_equal(x, np.array([0.0, 10.0, 20.0]))
        assert z.shape == (3, 3)
        np.testing.assert_array_equal(z[1], np.array([3.0, 4.0, 12.0]))

    def test_dated_first_column(self):
        x, _, z = build_table_2d_dated(
            TableData(
                [
                    [0.0, 1.0],
                    ["01-01-2024", 3.0, 4.0],
                    ["01-01-2030", 5.0, 6.0],
                ]
            )
        )

        assert x.dtype == np.dtype("datetime64[D]")
        np.testing.assert_array_equal(x, np.array([DATE_A, DATE_B]))
        np.testing.assert_array_equal(z, np.array([[3.0, 4.0], [5.0, 6.0]]))

    def test_date_rejected_by_the_undated_builder(self):
        with pytest.raises(ValueError, match="input must be numbers"):
            build_table_2d(TableData([[0.0, 1.0], ["01-01-2024", 3.0, 4.0]]))

    def test_non_numeric_header_rejected(self):
        with pytest.raises(ValueError, match="Header row must contain only numbers"):
            build_table_2d(TableData([[0.0, "high"], [0.0, 1.0, 2.0]]))

    def test_row_length_mismatch_rejected(self):
        with pytest.raises(ValueError, match="equal length"):
            build_table_2d(TableData([[0.0, 1.0], [0.0, 1.0]]))

    def test_date_in_value_column_rejected(self):
        with pytest.raises(ValueError, match="input must be numbers"):
            build_table_2d_dated(TableData([[0.0, 1.0], [0.0, "01-01-2024", 2.0]]))
