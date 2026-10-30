# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Reading a `Table = [...]` block: its cells, its dates, and its arrays.

The grammar reads the block into rows of numbers and dates, a date in any of
its three forms, and the `build_table_*` builders turn the rows into the
arrays a calculator holds: undated for Curve and Surface, dated for Forecast
and Timetable. What a calculator then does with the arrays, and which arrays
it refuses, is in the calculator tests.
"""

from __future__ import annotations

import re

import numpy as np
import pytest

from navigate.core.table_data import (
    TableData,
    build_table_1d,
    build_table_1d_dated,
    build_table_2d,
    build_table_2d_dated,
)
from navigate.exceptions import DeckError
from navigate.parser._syntax import parse_include_content

DATE_A = np.datetime64("2024-01-01", "D")
DATE_B = np.datetime64("2030-01-01", "D")

# three header values, then one row per x: the x-value first
SURFACE_ROWS = [
    [0.0, 1.0, 2.0],
    [0.0, 0.0, 1.0, 2.0],
    [10.0, 3.0, 4.0, 12.0],
]


def _rows(block: str) -> list[list[float | np.datetime64]]:
    """Parse a table block inside a Curve and return its rows."""
    [declaration] = parse_include_content(f'Curve "c" {{\n{block}\n}}')
    [assignment] = declaration.body
    assert isinstance(assignment.value, TableData)
    return assignment.value.rows


# ── cells ─────────────────────────────────────────────────────────────────────


# input:    | Table = [ # header
#           | 2020, 0.5; # inline
#           |
#           | 2030, 1.0;
#           | ]
# expected: -> [[2020.0, 0.5], [2030.0, 1.0]] (comments and blank lines dropped)
@pytest.mark.parametrize(
    ("block", "expected"),
    [
        ("Table = [\n]", []),
        ("Table = [ 2020, 0.5;\n2030, 1.0;\n]", [[2020.0, 0.5], [2030.0, 1.0]]),
        ("Table = [ 2020, 0.5;\n2030, 1.0\n]", [[2020.0, 0.5], [2030.0, 1.0]]),
        ("Table = [ 2020, 0.5; 2030, 1.0 ]", [[2020.0, 0.5], [2030.0, 1.0]]),
        (
            "Table = [ # header\n2020, 0.5; # inline\n\n2030, 1.0;\n]",
            [[2020.0, 0.5], [2030.0, 1.0]],
        ),
        ("Table=[\n\t1,\t-2e-1;\n]", [[1.0, -0.2]]),
        (
            'Table = [ "01-01-2024", 100;\n"2030-01-01", 200;\n2024-01-01, 300;\n]',
            [[DATE_A, 100.0], [DATE_B, 200.0], [DATE_A, 300.0]],
        ),
        ("Table = [ 0, 1, 2;\n0, 0, 1, 2;\n]", [[0.0, 1.0, 2.0], [0.0, 0.0, 1.0, 2.0]]),
        ("Table = [ 1, INF;\n2, -INF;\n]", [[1.0, float("inf")], [2.0, float("-inf")]]),
    ],
    ids=[
        "empty",
        "rows",
        "last_row_without_semicolon",
        "rows_on_one_line",
        "comments_and_blank_lines",
        "tabs_and_no_spaces",
        "dates",
        "2d",
        "infinities",
    ],
)
def test_table_rows(block, expected):
    assert _rows(block) == expected


# input:    | Table = [ 1, high ]   (also a quoted header and a row without commas)
# expected: -> DeckError: a cell is a number or a date, nothing else
@pytest.mark.parametrize(
    "block",
    [
        "Table = [ 1, high;\n]",
        'Table = [ "col_a", "col_b";\n1.0, 2.0;\n]',
        "Table = [1 2]",
    ],
    ids=["word", "quoted_header", "whitespace"],
)
def test_a_cell_is_a_number_or_a_date(block):
    with pytest.raises(DeckError):
        _rows(block)


# ── dates ─────────────────────────────────────────────────────────────────────


# input:    | Date "15-06-2030"  /  Date "15/06/2030"  /  Date "2030-06-15"
# expected: -> np.datetime64("2030-06-15") for each, at day resolution
@pytest.mark.parametrize(
    "text", ["15-06-2030", "15/06/2030", "2030-06-15"], ids=["dash", "slash", "iso"]
)
def test_a_date_is_read_in_each_form(text):
    [statement] = parse_include_content(f'Date "{text}"\n')

    assert statement.date == np.datetime64("2030-06-15")
    assert statement.date.dtype == np.dtype("datetime64[D]")


# input:    | e.g. Date "31-02-2025"  (no 31 February)  /  Date "2030"
# expected: -> DeckError '... line 1: "31-02-2025" is not a calendar date.', and
#              a syntax error naming the date the grammar expected for "2030"
@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("99-99-9999", '"99-99-9999" is not a calendar date.'),
        ("31-02-2025", '"31-02-2025" is not a calendar date.'),
        ("06-15-2030", '"06-15-2030" is not a calendar date.'),
        ("2030/06/15", "- expected date"),
        ("2030", "- expected date"),
    ],
)
def test_text_that_is_no_date_is_rejected_at_its_line(text, reason):
    with pytest.raises(DeckError, match=re.escape(reason)) as raised:
        parse_include_content(f'Date "{text}"\n', file="f.inc")

    assert "line 1" in str(raised.value)


# ── 1D builders: Curve (undated) and Forecast (dated) ────────────────────────


# input:    | Curve "c" { Table = [ 2020, 0.5;
#           |                       2030, 1.0; ] }
# expected: -> x = [2020.0, 2030.0], y = [0.5, 1.0], both float arrays
def test_build_table_1d():
    x, y = build_table_1d(TableData([[2020.0, 0.5], [2030.0, 1.0]]))

    np.testing.assert_array_equal(x, [2020.0, 2030.0])
    np.testing.assert_array_equal(y, [0.5, 1.0])
    assert x.dtype == y.dtype == np.float64


# input:    | Forecast "f" { Table = [ "01-01-2024", 0.5;
#           |                          "2030-01-01", 1.0; ] }
# expected: -> x = [2024-01-01, 2030-01-01] as dates, y = [0.5, 1.0];
#              with numeric x (2020, 2030) the x stays a float array
@pytest.mark.parametrize(
    ("rows", "dtype", "expected_x"),
    [
        ([[2020.0, 0.5], [2030.0, 1.0]], np.float64, [2020.0, 2030.0]),
        ([[DATE_A, 0.5], [DATE_B, 1.0]], "datetime64[D]", [DATE_A, DATE_B]),
    ],
    ids=["numeric_x_stays_numeric", "date_x"],
)
def test_build_table_1d_dated(rows, dtype, expected_x):
    x, y = build_table_1d_dated(TableData(rows))

    assert x.dtype == np.dtype(dtype)
    np.testing.assert_array_equal(x, expected_x)
    np.testing.assert_array_equal(y, [0.5, 1.0])


# input:    | e.g. Curve "c" { Table = [ 2020, 0.5, 1.0; ] }
# expected: -> ValueError "Table row must have exactly 2 columns, got 3."
#              and a date x on a Curve -> "Error in table row, 'x' must be a number."
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
            [[DATE_A, 0.5]],
            "Error in table row, 'x' must be a number.",
        ),
        (
            build_table_1d,
            [[2020.0, DATE_A]],
            "Error in table row, 'y' must be a number.",
        ),
        (
            build_table_1d_dated,
            [[2020.0, 0.5], [DATE_B, 1.0]],
            "All 'x' values in table must be consistently number or date.",
        ),
    ],
    ids=[
        "three_columns",
        "one_column",
        "date_in_undated_table",
        "date_y",
        "mixed_x",
    ],
)
def test_a_malformed_1d_table_is_rejected(build, rows, message):
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        build(TableData(rows))


# ── 2D builders: Surface (undated) and Timetable (dated) ─────────────────────


# input:    | Surface "s" { Table = [  0,  1,  2;
#           |                          0,  0,  1,  2;
#           |                         10,  3,  4, 12; ] }
# expected: -> x = [0, 10], y = [0, 1, 2], z = [[0, 1, 2], [3, 4, 12]]
def test_build_table_2d():
    x, y, z = build_table_2d(TableData(SURFACE_ROWS))

    np.testing.assert_array_equal(x, [0.0, 10.0])
    np.testing.assert_array_equal(y, [0.0, 1.0, 2.0])
    np.testing.assert_array_equal(z, [[0.0, 1.0, 2.0], [3.0, 4.0, 12.0]])


# input:    | Timetable "t" { Table = [               0,  1;
#           |                           "01-01-2024",  3,  4;
#           |                           "01-01-2030",  5,  6; ] }
# expected: -> x = [2024-01-01, 2030-01-01] as dates, y = [0, 1], z = [[3, 4], [5, 6]]
def test_build_table_2d_dated():
    x, y, z = build_table_2d_dated(
        TableData([[0.0, 1.0], [DATE_A, 3.0, 4.0], [DATE_B, 5.0, 6.0]])
    )

    assert x.dtype == np.dtype("datetime64[D]")
    np.testing.assert_array_equal(x, [DATE_A, DATE_B])
    np.testing.assert_array_equal(y, [0.0, 1.0])
    np.testing.assert_array_equal(z, [[3.0, 4.0], [5.0, 6.0]])


# input:    | e.g. Surface "s" { Table = [ 0, 1;
#           |                            0, 1; ] }   (row one value short)
# expected: -> ValueError "All rows in the table must have equal length."
@pytest.mark.parametrize(
    ("build", "rows", "message"),
    [
        (
            build_table_2d,
            [[0.0, DATE_A], [0.0, 1.0, 2.0]],
            "Header row must contain only numbers, got '2024-01-01'.",
        ),
        (
            build_table_2d,
            [[0.0, 1.0], [0.0, 1.0]],
            "All rows in the table must have equal length.",
        ),
        (
            build_table_2d,
            [[0.0, 1.0], [DATE_A, 3.0, 4.0]],
            "Error in table row, input must be numbers.",
        ),
        (
            build_table_2d_dated,
            [[0.0, 1.0], [0.0, DATE_A, 2.0]],
            "Error in table row, input must be numbers.",
        ),
        (
            build_table_2d_dated,
            [[0.0, 1.0], [DATE_A, 3.0, 4.0], [2030.0, 5.0, 6.0]],
            "All 'x' values in table must be consistently number or date.",
        ),
    ],
    ids=["date_header", "short_row", "date_in_undated_table", "date_value", "mixed_x"],
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
