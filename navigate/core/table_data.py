# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Container for a parsed table and the builders turning it into numpy arrays.

A date is a permission rather than a mode: the dated builders return a float
x-array for a numeric table, and the consumer dispatches on the dtype.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from navigate.util.types_ import DateArray, FloatArray


@dataclass
class TableData:
    """
    Fully-parsed table: rows of typed cells.

    String cells are date literals (converted later via ``string_to_date``).
    Numeric cells are already ``float``.
    """

    rows: list[list[float | str]] = field(default_factory=list)  # the table, row by row


# the x-column rejection names the formats 'string_to_date' accepts
_DATE_FORMAT_ERROR = (
    "Error in table row, 'x' must be a number or a date in format "
    "dd-mm-yyyy, dd/mm/yyyy or yyyy-mm-dd."
)


def string_to_date(string: str, msg: str = "") -> np.datetime64:
    """
    Convert a date string to ``np.datetime64``.

    Supported formats: ``dd-mm-yyyy``, ``dd/mm/yyyy``, ``yyyy-mm-dd`` (ISO 8601).

    Parameters
    ----------
    string
        Date string (may contain surrounding whitespace/quotes).
    msg
        Error message for raised ``ValueError``.

    Returns
    -------
    np.datetime64
        The parsed date, at day resolution.
    """
    string = string.strip(' \n\t"')
    for date_format in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            parsed_date = datetime.datetime.strptime(string, date_format)
            return np.datetime64(parsed_date.date(), "D")
        except ValueError:
            continue
    raise ValueError(msg)


def parse_table_cells(table_block: str) -> list[list[float | str]]:
    """
    Parse a raw ``TABLE_BLOCK`` token into typed row-lists.

    Parameters
    ----------
    table_block
        The token as the grammar read it, brackets and comments included.

    Returns
    -------
    list[list[float | str]]
        One list per row, of ``float`` and ``str`` cells (quoted date and
        header strings, quotes stripped).
    """
    inner = re.sub(r"^Table\s*=?\s*\[\s*", "", table_block)
    inner = re.sub(r"\s*]\s*$", "", inner)

    rows: list[list[float | str]] = []
    for line in inner.split("\n"):
        line = re.sub(r"#.*$", "", line).strip()
        if not line:
            continue

        cells: list[float | str] = []
        for token in re.findall(r'"[^"]*"|[^\s]+', line):
            if token.startswith('"'):
                cells.append(token[1:-1])
            else:
                try:
                    cells.append(float(token))
                except ValueError:
                    cells.append(token)
        rows.append(cells)
    return rows


def build_table_1d(table: TableData) -> tuple[FloatArray, FloatArray]:
    """
    Build numpy arrays from a 1D TableData whose x-column is numeric.

    Parameters
    ----------
    table
        Pre-parsed table with typed cells.

    Returns
    -------
    FloatArray
        The x-column.
    FloatArray
        The y-column.
    """
    x, y, _ = _table_1d_columns(table, allow_date=False)

    return np.array(x, dtype=np.float64), np.array(y, dtype=np.float64)


def build_table_1d_dated(table: TableData) -> tuple[FloatArray | DateArray, FloatArray]:
    """
    Build numpy arrays from a 1D TableData whose x-column may hold dates.

    Parameters
    ----------
    table
        Pre-parsed table with typed cells.

    Returns
    -------
    FloatArray | DateArray
        The x-column, float or date.
    FloatArray
        The y-column.
    """
    x, y, is_date = _table_1d_columns(table, allow_date=True)

    return _x_array(x, is_date), np.array(y, dtype=np.float64)


def build_table_2d(table: TableData) -> tuple[FloatArray, FloatArray, FloatArray]:
    """
    Build numpy arrays from a 2D TableData whose x-column is numeric.

    Parameters
    ----------
    table
        Pre-parsed table with typed cells.

    Returns
    -------
    FloatArray
        The x-column.
    FloatArray
        The y-column, read from the header row.
    FloatArray
        The value cells, one row per x.
    """
    x, y, z, _ = _table_2d_columns(table, allow_date=False)

    return (
        np.array(x, dtype=np.float64),
        np.array(y, dtype=np.float64),
        np.array(z, dtype=np.float64),
    )


def build_table_2d_dated(
    table: TableData,
) -> tuple[FloatArray | DateArray, FloatArray, FloatArray]:
    """
    Build numpy arrays from a 2D TableData whose x-column may hold dates.

    Parameters
    ----------
    table
        Pre-parsed table with typed cells.

    Returns
    -------
    FloatArray | DateArray
        The x-column, float or date.
    FloatArray
        The y-column, read from the header row.
    FloatArray
        The value cells, one row per x.
    """
    x, y, z, is_date = _table_2d_columns(table, allow_date=True)

    return (
        _x_array(x, is_date),
        np.array(y, dtype=np.float64),
        np.array(z, dtype=np.float64),
    )


def _table_1d_columns(
    table: TableData, allow_date: bool
) -> tuple[list[float | np.datetime64], list[float], bool]:
    """
    Read the x- and y-column of a 1D table, and whether x holds dates.

    Parameters
    ----------
    table
        Pre-parsed table with typed cells.
    allow_date
        Whether a date literal is accepted in the x-column.

    Returns
    -------
    list[float | np.datetime64]
        The x-column.
    list[float]
        The y-column.
    bool
        Whether the x-column holds dates.
    """
    x: list[float | np.datetime64] = []
    y: list[float] = []
    is_date = None

    for row in table.rows:
        if len(row) != 2:
            raise ValueError(f"Table row must have exactly 2 columns, got {len(row)}.")

        x_cell, y_cell = row

        if isinstance(x_cell, float):
            x_value: float | np.datetime64 = x_cell
        elif allow_date and isinstance(x_cell, str):
            x_value = string_to_date(x_cell, msg=_DATE_FORMAT_ERROR)
        else:
            raise ValueError("Error in table row, 'x' must be a number.")

        if not isinstance(y_cell, float):
            raise ValueError("Error in table row, 'y' must be a number.")

        is_date = _consistent_is_date(is_date, x_value)

        x.append(x_value)
        y.append(y_cell)

    return x, y, bool(is_date)


def _table_2d_columns(
    table: TableData, allow_date: bool
) -> tuple[
    list[float | np.datetime64],
    list[float],
    list[list[float]],
    bool,
]:
    """
    Read the x-, y- and z-column of a 2D table, and whether x holds dates.

    Parameters
    ----------
    table
        Pre-parsed table with typed cells.
    allow_date
        Whether a date literal is accepted in the x-column.

    Returns
    -------
    list[float | np.datetime64]
        The x-column.
    list[float]
        The y-column, read from the header row.
    list[list[float]]
        The value cells, one row per x.
    bool
        Whether the x-column holds dates.
    """
    if not table.rows:
        return [], [], [], False

    header, *data = table.rows
    y = _header_row(header)

    x: list[float | np.datetime64] = []
    z: list[list[float]] = []
    is_date = None

    for row in data:
        x_value, values = _table_2d_row(row, allow_date)

        if len(values) != len(y):
            raise ValueError("All rows in the table must have equal length.")

        is_date = _consistent_is_date(is_date, x_value)

        x.append(x_value)
        z.append(values)

    return x, y, z, bool(is_date)


def _header_row(row: list[float | str]) -> list[float]:
    """
    Read the header row of a 2D table, which carries the y-axis.

    Parameters
    ----------
    row
        The first row of the table.

    Returns
    -------
    list[float]
        The y-column.
    """
    values = []

    for cell in row:
        if not isinstance(cell, float):
            raise ValueError(f"Header row must contain only numbers, got '{cell}'.")

        values.append(cell)

    return values


def _table_2d_row(
    row: list[float | str], allow_date: bool
) -> tuple[float | np.datetime64, list[float]]:
    """
    Read one data row of a 2D table, the first cell of which carries x.

    Parameters
    ----------
    row
        One data row, its x-cell first.
    allow_date
        Whether a date literal is accepted in the x-cell.

    Returns
    -------
    float | np.datetime64
        The x-value of the row.
    list[float]
        The value cells of the row.
    """
    x_cell, *value_cells = row

    if isinstance(x_cell, float):
        x_value: float | np.datetime64 = x_cell
    elif allow_date:
        x_value = string_to_date(x_cell, msg=_DATE_FORMAT_ERROR)
    else:
        raise ValueError("Error in table row, input must be numbers.")

    values = []
    for cell in value_cells:
        if not isinstance(cell, float):
            raise ValueError("Error in table row, input must be numbers.")

        values.append(cell)

    return x_value, values


def _consistent_is_date(is_date: bool | None, x_value: float | np.datetime64) -> bool:
    """
    Confirm the x-column keeps the kind the rows before it established.

    Parameters
    ----------
    is_date
        The kind established so far, ``None`` before the first row.
    x_value
        The x-value of the current row.

    Returns
    -------
    bool
        Whether the current x-value is a date.
    """
    row_is_date = not isinstance(x_value, float)

    if (is_date is not None) and (is_date != row_is_date):
        raise ValueError("All 'x' values in table must be consistently number or date.")

    return row_is_date


def _x_array(x: list[float | np.datetime64], is_date: bool) -> FloatArray | DateArray:
    """
    Turn the x-column into an array of the dtype its cells carry.

    Parameters
    ----------
    x
        The x-column cells.
    is_date
        Whether the cells hold dates.

    Returns
    -------
    FloatArray | DateArray
        The x-column, float or date.
    """
    if is_date:
        return np.array(x, dtype=np.dtype("datetime64[D]"))

    return np.array(x, dtype=np.float64)
