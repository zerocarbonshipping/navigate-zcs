# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Interpolation inside a calculator table, for every 'Interpolate' mode.

The tables are small enough that each expected value is read off by hand: a
lookup between two rows, and a lookup exactly halfway, where NEAREST and
NEAREST_UP part ways. A LINEAR table is infinite wherever an infinite point
weighs in, up to its finite neighbours, which keep their own values.
"""

from __future__ import annotations

import logging

import numpy as np
import pytest

from navigate.core.nodes.curve import Curve
from navigate.core.nodes.surface import Surface
from navigate.core.table_data import TableData

INF = np.inf

# y against x: 0 -> 0, 1 -> 10, 2 -> 40
CURVE_ROWS = [[0.0, 0.0], [1.0, 10.0], [2.0, 40.0]]

# header row holds y = [0, 10]; below it x = 0 and x = 2:
# z(0, 0) = 0, z(0, 10) = 10, z(2, 0) = 4, z(2, 10) = 30
SURFACE_ROWS = [[0.0, 10.0], [0.0, 0.0, 10.0], [2.0, 4.0, 30.0]]

# y against x: 0 -> 1, 1 -> 2, 2 -> INF, 3 -> 5
INFINITE_CURVE_ROWS = [[0.0, 1.0], [1.0, 2.0], [2.0, INF], [3.0, 5.0]]

# header row holds y = [0, 1, 2]; below it x = 0, 1 and 2, with INF at the centre:
# z(0, .) = 1, 2, 3; z(1, .) = 4, INF, 6; z(2, .) = 7, 8, 9
INFINITE_SURFACE_ROWS = [
    [0.0, 1.0, 2.0],
    [0.0, 1.0, 2.0, 3.0],
    [1.0, 4.0, INF, 6.0],
    [2.0, 7.0, 8.0, 9.0],
]


def _curve(interpolate: str) -> Curve:
    curve = Curve("c")
    curve.set_interpolate(interpolate)
    # PREVIOUS and NEXT refuse the default LINEAR extrapolation
    curve.set_extrapolate("FLAT")
    curve.set_table(TableData(rows=CURVE_ROWS))
    curve.build_table()
    return curve


def _surface(interpolate: str) -> Surface:
    surface = Surface("s")
    surface.set_interpolate(interpolate)
    surface.set_table(TableData(rows=SURFACE_ROWS))
    surface.build_table()
    return surface


# looks up a small Curve between two rows and exactly halfway between two rows,
# for each 1D Interpolate mode, both one value at a time and as an array.
# catches: a mode mapped to the wrong method, e.g. NEAREST and NEAREST_UP
# swapped, so the halfway point 0.5 reads 10 instead of 0.
@pytest.mark.parametrize(
    ("interpolate", "at_half", "at_quarter_past_one"),
    [
        # x = 0.5: halfway from 0 to 10 -> 5; x = 1.25: 10 + 0.25 * 30 -> 17.5
        ("LINEAR", 5.0, 17.5),
        # the row at or before x
        ("PREVIOUS", 0.0, 10.0),
        # the row at or after x
        ("NEXT", 10.0, 40.0),
        # the closer row; a tie at 0.5 goes down to x = 0
        ("NEAREST", 0.0, 10.0),
        # the closer row; a tie at 0.5 goes up to x = 1
        ("NEAREST_UP", 10.0, 10.0),
    ],
)
def test_curve_interpolates_by_its_mode(interpolate, at_half, at_quarter_past_one):
    curve = _curve(interpolate)

    assert curve.get(0.5) == pytest.approx(at_half)
    assert curve.get(1.25) == pytest.approx(at_quarter_past_one)
    # an array input is looked up entry by entry
    np.testing.assert_allclose(
        curve.get(np.array([0.5, 1.25])), [at_half, at_quarter_past_one]
    )


# looks up a 2x2 Surface off the grid points and compares with a bilinear value
# worked out by hand, and with the closest grid point for NEAREST.
# catches: x and y swapped in the 2D lookup, so (0.5, 7.5) reads the wrong
# corner mix instead of 11.5.
@pytest.mark.parametrize(
    ("interpolate", "x", "y", "expected"),
    [
        # x is 1/4 of the way to 2, y is 3/4 of the way to 10:
        # 0.75 * 0.25 * 0 + 0.75 * 0.75 * 10 + 0.25 * 0.25 * 4 + 0.25 * 0.75 * 30
        # = 0 + 5.625 + 0.25 + 5.625 = 11.5
        ("LINEAR", 0.5, 7.5, 11.5),
        # x is 3/4 of the way to 2, y is 1/4 of the way to 10:
        # 0.25 * 0.75 * 0 + 0.25 * 0.25 * 10 + 0.75 * 0.75 * 4 + 0.75 * 0.25 * 30
        # = 0 + 0.625 + 2.25 + 5.625 = 8.5
        ("LINEAR", 1.5, 2.5, 8.5),
        # the closest grid point (0, 10)
        ("NEAREST", 0.5, 7.5, 10.0),
        # the closest grid point (2, 0)
        ("NEAREST", 1.5, 2.5, 4.0),
    ],
)
def test_surface_interpolates_by_its_mode(interpolate, x, y, expected):
    assert _surface(interpolate).get(x, y) == pytest.approx(expected)


# looks up a LINEAR Curve with an infinite point on an ordinary segment, at the
# infinite point's finite neighbours and between them, one value at a time and
# as an array.
# catches: the infinite point weighed only at itself, so x = 1.5 reads NaN or a
# value interpolated towards a finite stand-in, or a neighbour drawn into the
# infinity, so x = 1 or x = 3 reads INF instead of 2 or 5.
@pytest.mark.parametrize(
    ("x", "expected"),
    [
        # an ordinary segment: halfway from 1 to 2
        (0.5, 1.5),
        # the finite neighbours keep their own values
        (1.0, 2.0),
        (3.0, 5.0),
        # wherever the infinite point weighs in, up to its neighbours
        (1.5, INF),
        (2.0, INF),
        (2.5, INF),
    ],
)
def test_linear_curve_is_infinite_up_to_the_neighbours_of_an_infinite_point(
    x, expected
):
    curve = Curve("c")
    # LINEAR extrapolation off the finite end 5, next to INF, is refused
    curve.set_extrapolate("FLAT")
    curve.set_table(TableData(rows=INFINITE_CURVE_ROWS))
    curve.build_table()

    assert curve.get(x) == expected
    assert curve.get(np.array([x]))[0] == expected


# looks up a LINEAR Surface with INF at its centre inside a cell, on an edge
# ending at the INF corner, on an edge between finite corners and at a finite
# corner.
# catches: the INF corner weighed only at its own point, so (0.5, 0.5) reads NaN
# or a finite mix, or a finite edge drawn into the infinity, so (0, 0.5) reads
# INF instead of 1.5.
@pytest.mark.parametrize(
    ("x", "y", "expected"),
    [
        # inside a cell with the INF corner
        (0.5, 0.5, INF),
        # on an edge ending at the INF corner
        (1.0, 0.5, INF),
        # on the edge between the finite corners z(0, 0) = 1 and z(0, 1) = 2
        (0.0, 0.5, 1.5),
        # a finite corner of a cell with the INF corner
        (1.0, 0.0, 4.0),
    ],
)
def test_linear_surface_is_infinite_in_the_cells_of_an_infinite_point(x, y, expected):
    surface = Surface("s")
    # LINEAR extrapolation off the finite edge point z(0, 1), next to INF, is
    # refused
    surface.set_extrapolate("FLAT")
    surface.set_table(TableData(rows=INFINITE_SURFACE_ROWS))
    surface.build_table()

    assert surface.get(x, y) == pytest.approx(expected)


# builds a Curve whose finite point neighbours an infinite one, with LINEAR and
# with PREVIOUS interpolation.
# catches: the warning dropped, so a table meant as a step to no limit loses its
# finite value right after the finite point unannounced; or raised for a step
# table, which already says where the value turns infinite.
@pytest.mark.parametrize(
    ("interpolate", "warns"), [("LINEAR", True), ("PREVIOUS", False)]
)
def test_linear_curve_next_to_an_infinite_point_warns(interpolate, warns, caplog):
    curve = Curve("c")
    curve.set_interpolate(interpolate)
    curve.set_extrapolate("FLAT")
    curve.set_table(TableData(rows=[[0.0, 1.0], [1.0, INF]]))

    with caplog.at_level(logging.WARNING):
        curve.build_table()

    warned = any("PREVIOUS or NEXT" in record.getMessage() for record in caplog.records)
    assert warned is warns
