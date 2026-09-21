# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Table data container and builder functions.

Provides ``TableData`` (a simple row-list container produced by the grammar)
and functions that convert it into the numpy arrays expected by
``_Table1D`` / ``_Table2D``.

A date is a permission rather than a mode: the dated builders return a float
x-array for a numeric table, and the consumer dispatches on the dtype.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

# ═════════════════════════════════════════════════════════════════════════
# AST container
# ═════════════════════════════════════════════════════════════════════════


@dataclass
class TableData:
    """
    Fully-parsed table — rows of typed cells.

    String cells are date literals (converted later via ``string_to_date``).
    Numeric cells are already ``float``.
    """

    rows: list[list[float | str]] = field(default_factory=list)


# ═════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════


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
    """
    string = string.strip(' \n\t"')
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(string, fmt)
            return np.datetime64(dt.date(), "D")
        except ValueError:
            continue
    raise ValueError(msg)


def parse_table_cells(raw: str) -> list[list[float | str]]:
    """
    Parse a raw ``TABLE_BLOCK`` token into typed row-lists.

    Returns a list of rows, where each row is a list of ``float`` or
    ``str`` (for quoted date/header strings — quotes stripped).
    """
    inner = re.sub(r"^Table\s*=?\s*\[\s*", "", raw)
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


# ═════════════════════════════════════════════════════════════════════════
# Builders
# ═════════════════════════════════════════════════════════════════════════


def build_table_1d(
    table: TableData,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """
    Build numpy arrays from a 1D TableData whose x-column is numeric.

    Parameters
    ----------
    table
        Pre-parsed table with typed cells.

    Returns
    -------
    npt.NDArray[np.float64]
        The x-column.
    npt.NDArray[np.float64]
        The y-column.
    """
    x, y, _ = _table_1d_columns(table, allow_date=False)

    return np.array(x, dtype=np.float64), np.array(y, dtype=np.float64)


def build_table_1d_dated(
    table: TableData,
) -> tuple[
    npt.NDArray[np.float64] | npt.NDArray[np.datetime64], npt.NDArray[np.float64]
]:
    """
    Build numpy arrays from a 1D TableData whose x-column may hold dates.

    Parameters
    ----------
    table
        Pre-parsed table with typed cells.

    Returns
    -------
    npt.NDArray[np.float64] | npt.NDArray[np.datetime64]
        The x-column, float or date.
    npt.NDArray[np.float64]
        The y-column.
    """
    x, y, is_date = _table_1d_columns(table, allow_date=True)

    return _x_array(x, is_date), np.array(y, dtype=np.float64)


def build_table_2d(
    table: TableData,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """
    Build numpy arrays from a 2D TableData whose x-column is numeric.

    Parameters
    ----------
    table
        Pre-parsed table with typed cells.

    Returns
    -------
    npt.NDArray[np.float64]
        The x-column.
    npt.NDArray[np.float64]
        The y-column, read from the header row.
    npt.NDArray[np.float64]
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
) -> tuple[
    npt.NDArray[np.float64] | npt.NDArray[np.datetime64],
    npt.NDArray[np.float64],
    npt.NDArray[np.float64],
]:
    """
    Build numpy arrays from a 2D TableData whose x-column may hold dates.

    Parameters
    ----------
    table
        Pre-parsed table with typed cells.

    Returns
    -------
    npt.NDArray[np.float64] | npt.NDArray[np.datetime64]
        The x-column, float or date.
    npt.NDArray[np.float64]
        The y-column, read from the header row.
    npt.NDArray[np.float64]
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
    """Read the x- and y-column of a 1D table, and whether x holds dates."""
    x: list[float | np.datetime64] = []
    y: list[float] = []
    is_date = None

    for row in table.rows:
        if len(row) != 2:
            raise ValueError(f"Table row must have exactly 2 columns, got {len(row)}.")

        x_val, y_val = row

        if isinstance(x_val, float):
            x_: float | np.datetime64 = x_val
        elif allow_date and isinstance(x_val, str):
            x_ = string_to_date(x_val, msg=_DATE_FORMAT_ERROR)
        else:
            raise ValueError("Error in table row, 'x' must be a number.")

        if not isinstance(y_val, float):
            raise ValueError("Error in table row, 'y' must be a number.")

        is_date = _consistent_is_date(is_date, x_)

        x.append(x_)
        y.append(y_val)

    return x, y, bool(is_date)


def _table_2d_columns(
    table: TableData, allow_date: bool
) -> tuple[
    list[float | np.datetime64],
    list[float],
    list[list[float]],
    bool,
]:
    """Read the x-, y- and z-column of a 2D table, and whether x holds dates."""
    if not table.rows:
        return [], [], [], False

    header, *data = table.rows
    y = _header_row(header)

    x: list[float | np.datetime64] = []
    z: list[list[float]] = []
    is_date = None

    for row in data:
        x_val, values = _table_2d_row(row, allow_date)

        if len(values) != len(y):
            raise ValueError("All rows in the table must have equal length.")

        is_date = _consistent_is_date(is_date, x_val)

        x.append(x_val)
        z.append(values)

    return x, y, z, bool(is_date)


def _header_row(row: list[float | str]) -> list[float]:
    """Read the header row of a 2D table, which carries the y-axis."""
    values = []

    for cell in row:
        if not isinstance(cell, float):
            raise ValueError(f"Header row must contain only numbers, got '{cell}'.")

        values.append(cell)

    return values


def _table_2d_row(
    row: list[float | str], allow_date: bool
) -> tuple[float | np.datetime64, list[float]]:
    """Read one data row of a 2D table, the first cell of which carries x."""
    x_cell, *value_cells = row

    if isinstance(x_cell, float):
        x_val: float | np.datetime64 = x_cell
    elif allow_date:
        x_val = string_to_date(x_cell, msg=_DATE_FORMAT_ERROR)
    else:
        raise ValueError("Error in table row, input must be numbers.")

    values = []
    for cell in value_cells:
        if not isinstance(cell, float):
            raise ValueError("Error in table row, input must be numbers.")

        values.append(cell)

    return x_val, values


def _consistent_is_date(is_date: bool | None, x_val: float | np.datetime64) -> bool:
    """Confirm the x-column keeps the kind the rows before it established."""
    row_is_date = not isinstance(x_val, float)

    if (is_date is not None) and (is_date != row_is_date):
        raise ValueError("All 'x' values in table must be consistently number or date.")

    return row_is_date


def _x_array(
    x: list[float | np.datetime64], is_date: bool
) -> npt.NDArray[np.float64] | npt.NDArray[np.datetime64]:
    """Turn the x-column into an array of the dtype its cells carry."""
    if is_date:
        return np.array(x, dtype=np.dtype("datetime64[D]"))

    return np.array(x, dtype=np.float64)
