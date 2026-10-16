# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Reading a `Table = [...]` block: its cells, its dates, and its arrays.

`parse_table_cells` splits the block into typed cells, `string_to_date` reads a
date cell, and the `build_table_*` builders turn the cells into the arrays a
calculator holds: undated for Curve and Surface, dated for Forecast and
Timetable. What a calculator then does with the arrays, and which arrays it
refuses, is in the calculator tests.
"""

from __future__ import annotations

import re

import numpy as np
import pytest

from navigate.core.table_data import (
    _DATE_FORMAT_ERROR,
    TableData,
    build_table_1d,
    build_table_1d_dated,
    build_table_2d,
    build_table_2d_dated,
    parse_table_cells,
    string_to_date,
)

DATE_A = np.datetime64("2024-01-01", "D")
DATE_B = np.datetime64("2030-01-01", "D")

# three header values, then one row per x: the x-value first
SURFACE_ROWS = [
    [0.0, 1.0, 2.0],
    [0.0, 0.0, 1.0, 2.0],
    [10.0, 3.0, 4.0, 12.0],
]


# ── cells ─────────────────────────────────────────────────────────────────────


# input:    | Table = [ # header
#           | 2020 0.5 # inline
#           |
#           | 2030 1.0
#           | ]
# expected: -> [[2020.0, 0.5], [2030.0, 1.0]] (comments and blank lines dropped)
@pytest.mark.parametrize(
    ("block", "expected"),
    [
        ("Table = [\n]", []),
        ("Table = [ 2020 0.5\n2030 1.0\n]", [[2020.0, 0.5], [2030.0, 1.0]]),
        (
            "Table = [ # header\n2020 0.5 # inline\n\n2030 1.0\n]",
            [[2020.0, 0.5], [2030.0, 1.0]],
        ),
        ("Table=[\n\t1\t-2e-1\n]", [[1.0, -0.2]]),
        (
            'Table = [ "01-01-2020" 100\n"2030-01-01" 200\n]',
            [["01-01-2020", 100.0], ["2030-01-01", 200.0]],
        ),
        (
            'Table = [ "col_a" "col_b"\n1.0 2.0\n]',
            [["col_a", "col_b"], [1.0, 2.0]],
        ),
        ("Table = [ 0 1 2\n0 0 1 2\n]", [[0.0, 1.0, 2.0], [0.0, 0.0, 1.0, 2.0]]),
        ("Table = [ 1 high\n]", [[1.0, "high"]]),
        ("Table = [ 1 INF\n2 -INF\n]", [[1.0, float("inf")], [2.0, float("-inf")]]),
    ],
    ids=[
        "empty",
        "rows",
        "comments_and_blank_lines",
        "tabs_and_no_spaces",
        "quoted_dates",
        "quoted_headers",
        "2d",
        "unquoted_word_kept_as_text",
        "infinities",
    ],
)
def test_parse_table_cells(block, expected):
    assert parse_table_cells(block) == expected


# ── dates ─────────────────────────────────────────────────────────────────────


# input:    | "15-06-2030"  /  "15/06/2030"  /  "2030-06-15"
# expected: -> np.datetime64("2030-06-15") for each, at day resolution
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("15-06-2030", np.datetime64("2030-06-15")),
        ("15/06/2030", np.datetime64("2030-06-15")),
        ("2030-06-15", np.datetime64("2030-06-15")),
        ('  "15-06-2030"\n', np.datetime64("2030-06-15")),
    ],
    ids=["dash", "slash", "iso", "whitespace_and_quotes"],
)
def test_string_to_date(text, expected):
    date = string_to_date(text, _DATE_FORMAT_ERROR)

    assert date == expected
    assert date.dtype == np.dtype("datetime64[D]")


# input:    | e.g. "31-02-2025"  (no 31 February)
# expected: -> ValueError with the caller's date-format message
@pytest.mark.parametrize(
    "text", ["99-99-9999", "31-02-2025", "2030/06/15", "06-15-2030", "2030"]
)
def test_string_to_date_rejects_other_text_with_the_callers_message(text):
    with pytest.raises(ValueError, match=f"^{re.escape(_DATE_FORMAT_ERROR)}$"):
        string_to_date(text, _DATE_FORMAT_ERROR)


# ── 1D builders: Curve (undated) and Forecast (dated) ────────────────────────


# input:    | Curve "c" { Table = [ 2020 0.5
#           |                       2030 1.0 ] }
# expected: -> x = [2020.0, 2030.0], y = [0.5, 1.0], both float arrays
def test_build_table_1d():
    x, y = build_table_1d(TableData([[2020.0, 0.5], [2030.0, 1.0]]))

    np.testing.assert_array_equal(x, [2020.0, 2030.0])
    np.testing.assert_array_equal(y, [0.5, 1.0])
    assert x.dtype == y.dtype == np.float64


# input:    | Forecast "f" { Table = [ "01-01-2024" 0.5
#           |                          "2030-01-01" 1.0 ] }
# expected: -> x = [2024-01-01, 2030-01-01] as dates, y = [0.5, 1.0];
#              with numeric x (2020, 2030) the x stays a float array
@pytest.mark.parametrize(
    ("rows", "dtype", "expected_x"),
    [
        ([[2020.0, 0.5], [2030.0, 1.0]], np.float64, [2020.0, 2030.0]),
        ([["01-01-2024", 0.5], ["2030-01-01", 1.0]], "datetime64[D]", [DATE_A, DATE_B]),
    ],
    ids=["numeric_x_stays_numeric", "date_x"],
)
def test_build_table_1d_dated(rows, dtype, expected_x):
    x, y = build_table_1d_dated(TableData(rows))

    assert x.dtype == np.dtype(dtype)
    np.testing.assert_array_equal(x, expected_x)
    np.testing.assert_array_equal(y, [0.5, 1.0])


# input:    | e.g. Curve "c" { Table = [ 2020 0.5 1.0 ] }
# expected: -> ValueError "Table row must have exactly 2 columns, got 3."
#              and Table = [ 2020 high ] -> "Error in table row, 'y' must be a number."
@pytest.mark.parametrize(
    ("build", "rows", "message"),
    [
        (
            build_table_1d,
            [[2020.0, 0.5, 1.0]],
            "Table row must have exactly 2 columns, got 3.",
        ),
        (build_table_1d, [[2020.0]], "Table row must have exactly 2 columns, got 1."),
        (
            build_table_1d,
            [["01-01-2024", 0.5]],
            "Error in table row, 'x' must be a number.",
        ),
        (
            build_table_1d,
            [[2020.0, "high"]],
            "Error in table row, 'y' must be a number.",
        ),
        (build_table_1d_dated, [["soon", 0.5]], _DATE_FORMAT_ERROR),
        (
            build_table_1d_dated,
            [[2020.0, 0.5], ["01-01-2030", 1.0]],
            "All 'x' values in table must be consistently number or date.",
        ),
    ],
    ids=[
        "three_columns",
        "one_column",
        "date_in_undated_table",
        "text_y",
        "text_x",
        "mixed_x",
    ],
)
def test_a_malformed_1d_table_is_rejected(build, rows, message):
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        build(TableData(rows))


# ── 2D builders: Surface (undated) and Timetable (dated) ─────────────────────


# input:    | Surface "s" { Table = [  0  1  2
#           |                          0  0  1  2
#           |                         10  3  4 12 ] }
# expected: -> x = [0, 10], y = [0, 1, 2], z = [[0, 1, 2], [3, 4, 12]]
def test_build_table_2d():
    x, y, z = build_table_2d(TableData(SURFACE_ROWS))

    np.testing.assert_array_equal(x, [0.0, 10.0])
    np.testing.assert_array_equal(y, [0.0, 1.0, 2.0])
    np.testing.assert_array_equal(z, [[0.0, 1.0, 2.0], [3.0, 4.0, 12.0]])


# input:    | Timetable "t" { Table = [              0  1
#           |                           "01-01-2024"  3  4
#           |                           "01-01-2030"  5  6 ] }
# expected: -> x = [2024-01-01, 2030-01-01] as dates, y = [0, 1], z = [[3, 4], [5, 6]]
def test_build_table_2d_dated():
    x, y, z = build_table_2d_dated(
        TableData([[0.0, 1.0], ["01-01-2024", 3.0, 4.0], ["01-01-2030", 5.0, 6.0]])
    )

    assert x.dtype == np.dtype("datetime64[D]")
    np.testing.assert_array_equal(x, [DATE_A, DATE_B])
    np.testing.assert_array_equal(y, [0.0, 1.0])
    np.testing.assert_array_equal(z, [[3.0, 4.0], [5.0, 6.0]])


# input:    | e.g. Surface "s" { Table = [ 0 1
#           |                            0 1 ] }   (row one value short)
# expected: -> ValueError "All rows in the table must have equal length."
@pytest.mark.parametrize(
    ("build", "rows", "message"),
    [
        (
            build_table_2d,
            [[0.0, "high"], [0.0, 1.0, 2.0]],
            "Header row must contain only numbers, got 'high'.",
        ),
        (
            build_table_2d,
            [[0.0, 1.0], [0.0, 1.0]],
            "All rows in the table must have equal length.",
        ),
        (
            build_table_2d,
            [[0.0, 1.0], ["01-01-2024", 3.0, 4.0]],
            "Error in table row, input must be numbers.",
        ),
        (
            build_table_2d_dated,
            [[0.0, 1.0], [0.0, "01-01-2024", 2.0]],
            "Error in table row, input must be numbers.",
        ),
        (
            build_table_2d_dated,
            [[0.0, 1.0], ["01-01-2024", 3.0, 4.0], [2030.0, 5.0, 6.0]],
            "All 'x' values in table must be consistently number or date.",
        ),
    ],
    ids=["text_header", "short_row", "date_in_undated_table", "date_value", "mixed_x"],
)
def test_a_malformed_2d_table_is_rejected(build, rows, message):
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        build(TableData(rows))


# input:    | Table = [
#           | ]
# expected: -> empty float arrays from every builder, with no dates in them
@pytest.mark.parametrize(
    "build",
    [build_table_1d, build_table_1d_dated, build_table_2d, build_table_2d_dated],
)
def test_an_empty_table_builds_empty_float_arrays(build):
    # no cell was a date, so a dated consumer dispatches to its numeric branch
    arrays = build(TableData([]))

    assert all(array.dtype == np.float64 and array.size == 0 for array in arrays)
