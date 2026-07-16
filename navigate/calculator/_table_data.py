# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Table data container and builder functions.

Provides ``TableData`` (a simple row-list container produced by the grammar)
and functions that convert it into the numpy arrays expected by
``Table1D`` / ``Table2D``.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field

import numpy as np

# ═════════════════════════════════════════════════════════════════════════
# AST container
# ═════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class SourceLoc:
    """Immutable source-location tag attached to every AST node."""

    file: str = ""
    line: int = 0
    deck_line: int = 0


@dataclass
class TableData:
    """Fully-parsed table — rows of typed cells.

    String cells are date literals (converted later via ``string_to_date``).
    Numeric cells are already ``float``.
    """

    rows: list[list[float | str]] = field(default_factory=list)
    source: SourceLoc = field(default_factory=SourceLoc)


# ═════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════

def string_to_date(string: str, msg: str = '') -> np.datetime64:
    """Convert a date string to ``np.datetime64``.

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
            return np.datetime64(dt.date(), 'D')
        except ValueError:
            continue
    raise ValueError(msg)


def parse_table_cells(raw: str) -> list:
    """Parse a raw ``TABLE_BLOCK`` token into typed row-lists.

    Returns a list of rows, where each row is a list of ``float`` or
    ``str`` (for quoted date/header strings — quotes stripped).
    """
    inner = re.sub(r'^Table\s*=?\s*\[\s*', '', raw)
    inner = re.sub(r'\s*]\s*$', '', inner)

    rows: list = []
    for line in inner.split('\n'):
        line = re.sub(r'#.*$', '', line).strip()
        if not line:
            continue

        cells: list = []
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

def build_table_1d(table: TableData, allow_date: bool = False) -> tuple:
    """Build numpy arrays from a 1D TableData.

    Parameters
    ----------
    table
        Pre-parsed table with typed cells.
    allow_date
        Whether the x-column may contain date strings.

    Returns
    -------
    tuple of (x, y) numpy arrays.
    """
    x, y = [], []
    is_date = None

    for row in table.rows:
        if len(row) != 2:
            raise ValueError("Table row must have exactly 2 columns, got {}.".format(len(row)))

        x_val, y_val = row

        if isinstance(x_val, float):
            x_ = x_val
        elif allow_date and isinstance(x_val, str):
            x_ = string_to_date(
                x_val,
                msg="Error in table row, 'x' must be a number or a date "
                    "in format dd-mm-yyyy or dd/mm/yyyy.")
        else:
            raise ValueError("Error in table row, 'x' must be a number.")

        if not isinstance(y_val, float):
            raise ValueError("Error in table row, 'y' must be a number.")

        row_is_date = not isinstance(x_, float)
        if is_date is None:
            is_date = row_is_date
        elif is_date != row_is_date:
            raise ValueError("All 'x' values in table must be consistently number or date.")

        x.append(x_)
        y.append(y_val)

    x_arr = np.array(x, dtype='datetime64[D]' if is_date else np.float64)
    y_arr = np.array(y, dtype=np.float64)
    return x_arr, y_arr


def build_table_2d(table: TableData, allow_date: bool = False) -> tuple:
    """Build numpy arrays from a 2D TableData.

    Parameters
    ----------
    table
        Pre-parsed table with typed cells.
    allow_date
        Whether the x-column (first cell of data rows) may contain date strings.

    Returns
    -------
    tuple of (x, y, z) numpy arrays.
    """
    x, y, z = [], [], []
    col_count = 0
    is_date = None

    for i, row in enumerate(table.rows):
        if i == 0:
            for c in row:
                if not isinstance(c, float):
                    raise ValueError("Header row must contain only numbers, got '{}'.".format(c))
            y = list(row)
            col_count = len(row)
        else:
            vals = []
            for c_idx, cell in enumerate(row):
                if isinstance(cell, float):
                    vals.append(cell)
                elif allow_date and c_idx == 0:
                    vals.append(string_to_date(
                        cell,
                        msg="Error in table row, 'x' must be a number or a date "
                            "in format dd-mm-yyyy or dd/mm/yyyy."))
                else:
                    raise ValueError("Error in table row, input must be numbers.")

            if col_count != len(vals[1:]):
                raise ValueError("All rows in the table must have equal length.")

            row_is_date = not isinstance(vals[0], float)
            if is_date is None:
                is_date = row_is_date
            elif is_date != row_is_date:
                raise ValueError("All 'x' values in table must be consistently number or date.")

            x.append(vals[0])
            z.append(vals[1:])

    x_arr = np.array(x, dtype='datetime64[D]' if is_date else np.float64)
    y_arr = np.array(y, dtype=np.float64)
    z_arr = np.array(z, dtype=np.float64)
    return x_arr, y_arr, z_arr
