# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Interpolation inside a calculator table, for every 'Interpolate' mode.

The tables are small enough that each expected value is read off by hand: a
lookup between two rows, and a lookup exactly halfway, where NEAREST and
NEAREST_UP part ways.
"""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core.nodes.curve import Curve
from navigate.core.nodes.surface import Surface
from navigate.core.table_data import TableData

# y against x: 0 -> 0, 1 -> 10, 2 -> 40
CURVE_ROWS = [[0.0, 0.0], [1.0, 10.0], [2.0, 40.0]]

# header row holds y = [0, 10]; below it x = 0 and x = 2:
# z(0, 0) = 0, z(0, 10) = 10, z(2, 0) = 4, z(2, 10) = 30
SURFACE_ROWS = [[0.0, 10.0], [0.0, 0.0, 10.0], [2.0, 4.0, 30.0]]


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
