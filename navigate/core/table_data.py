# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Container for a parsed table and the builders turning it into numpy arrays.

A date is a permission rather than a mode: the dated builders return a float
x-array for a numeric table, and the consumer dispatches on the dtype.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from navigate.util.types_ import DateArray, FloatArray

type Cell = float | np.datetime64


@dataclass
class TableData:
    """A table as the deck writes it: rows of numbers and dates."""

    rows: list[list[Cell]] = field(default_factory=list)


def build_table_1d(table: TableData) -> tuple[FloatArray, FloatArray]:
    """
    Build numpy arrays from a 1D TableData whose x-column is numeric.

    Parameters
    ----------
    table
        The table as the deck wrote it.

    Returns
    -------
    FloatArray
        The x-column.
    FloatArray
        The y-column.
    """
    x, y = _table_1d_columns(table, allow_date=False)

    return np.array(x, dtype=np.float64), np.array(y, dtype=np.float64)


def build_table_1d_dated(table: TableData) -> tuple[FloatArray | DateArray, FloatArray]:
    """
    Build numpy arrays from a 1D TableData whose x-column may hold dates.

    Parameters
    ----------
    table
        The table as the deck wrote it.

    Returns
    -------
    FloatArray | DateArray
        The x-column, float or date.
    FloatArray
        The y-column.
    """
    x, y = _table_1d_columns(table, allow_date=True)

    return _x_array(x), np.array(y, dtype=np.float64)


def build_table_2d(table: TableData) -> tuple[FloatArray, FloatArray, FloatArray]:
    """
    Build numpy arrays from a 2D TableData whose x-column is numeric.

    Parameters
    ----------
    table
        The table as the deck wrote it.

    Returns
    -------
    FloatArray
        The x-column.
    FloatArray
        The y-column, read from the header row.
    FloatArray
        The value cells, one row per x.
    """
    x, y, z = _table_2d_columns(table, allow_date=False)

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
        The table as the deck wrote it.

    Returns
    -------
    FloatArray | DateArray
        The x-column, float or date.
    FloatArray
        The y-column, read from the header row.
    FloatArray
        The value cells, one row per x.
    """
    x, y, z = _table_2d_columns(table, allow_date=True)

    return (
        _x_array(x),
        np.array(y, dtype=np.float64),
        np.array(z, dtype=np.float64),
    )


def _table_1d_columns(
    table: TableData, allow_date: bool
) -> tuple[list[Cell], list[float]]:
    """Read the x- and y-column of a 1D table."""
    x_error = "Error in table row, 'x' must be a number."
    y_error = "Error in table row, 'y' must be a number."

    x: list[Cell] = []
    y: list[float] = []

    for row in table.rows:
        if len(row) != 2:
            raise ValueError(f"Table row must have exactly 2 columns, got {len(row)}.")

        x_cell, y_cell = row

        x.append(_read_x(x_cell, allow_date, x_error))
        y.extend(_read_numbers([y_cell], y_error))

    return x, y


def _table_2d_columns(
    table: TableData, allow_date: bool
) -> tuple[list[Cell], list[float], list[list[float]]]:
    """Read the x-, y- and z-column of a 2D table."""
    if not table.rows:
        return [], [], []

    header, *data = table.rows
    y = _read_numbers(header, "Header row must contain only numbers, got '{cell}'.")

    x: list[Cell] = []
    z: list[list[float]] = []

    for row in data:
        x_value, values = _table_2d_row(row, allow_date)

        if len(values) != len(y):
            raise ValueError("All rows in the table must have equal length.")

        x.append(x_value)
        z.append(values)

    return x, y, z


def _table_2d_row(row: list[Cell], allow_date: bool) -> tuple[Cell, list[float]]:
    """Read one data row of a 2D table, the first cell of which carries x."""
    error = "Error in table row, input must be numbers."
    x_cell, *value_cells = row

    return _read_x(x_cell, allow_date, error), _read_numbers(value_cells, error)


def _read_x(cell: Cell, allow_date: bool, error: str) -> Cell:
    """Read an x-cell, a number or, where allowed, a date."""
    if isinstance(cell, float) or allow_date:
        return cell

    raise ValueError(error)


def _read_numbers(cells: list[Cell], error: str) -> list[float]:
    """Read cells that must all be numbers."""
    values = []

    for cell in cells:
        if not isinstance(cell, float):
            raise ValueError(error.format(cell=cell))

        values.append(cell)

    return values


def _x_array(x: list[Cell]) -> FloatArray | DateArray:
    """Turn the x-column into an array of the dtype its cells carry."""
    is_date = [isinstance(value, np.datetime64) for value in x]

    if not any(is_date):
        return np.array(x, dtype=np.float64)

    if not all(is_date):
        raise ValueError("All 'x' values in table must be consistently number or date.")

    return np.array(x, dtype=np.dtype("datetime64[D]"))
