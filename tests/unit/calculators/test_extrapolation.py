# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Lookups beyond a calculator table, for every 'Extrapolate' mode.

Covers LINEAR, which continues the end segments; FLAT, which holds Below/Above
on a Curve and Outside on a Surface; FALSE, which refuses the lookup; and the
mode pairings a table refuses before it is ever looked up.
"""

from __future__ import annotations

import pytest

from navigate.core.nodes.curve import Curve
from navigate.core.nodes.surface import Surface
from navigate.core.nodes.timetable import Timetable
from navigate.core.table_data import TableData

# y against x: 0 -> 0, 1 -> 10, 2 -> 40; end slopes 10 and 30
CURVE_ROWS = [[0.0, 0.0], [1.0, 10.0], [2.0, 40.0]]

# header row holds y = [0, 10]; below it x = 0 and x = 2:
# z(0, 0) = 0, z(0, 10) = 10, z(2, 0) = 4, z(2, 10) = 30
SURFACE_ROWS = [[0.0, 10.0], [0.0, 0.0, 10.0], [2.0, 4.0, 30.0]]


def _curve(extrapolate: str, below: float | None = None, above: float | None = None):
    curve = Curve("c")
    curve.set_extrapolate(extrapolate)
    if below is not None:
        curve.set_below(below)
    if above is not None:
        curve.set_above(above)
    curve.set_table(TableData(rows=CURVE_ROWS))
    curve.build_table()
    return curve


def _surface(extrapolate: str, outside: float | None = None) -> Surface:
    surface = Surface("s")
    surface.set_extrapolate(extrapolate)
    if outside is not None:
        surface.set_outside(outside)
    surface.set_table(TableData(rows=SURFACE_ROWS))
    surface.build_table()
    return surface


# reads a Curve one step before its first row and one step after its last row
# with LINEAR extrapolation; each side follows the slope of its own end segment.
# catches: extrapolating from the overall slope instead of the end segment, so
# x = 3 reads 60 instead of 70.
def test_curve_linear_extrapolation_continues_the_end_segments():
    curve = _curve("LINEAR")

    # first segment slope 10: 0 - 10 * 1 = -10
    assert curve.get(-1.0) == pytest.approx(-10.0)
    # last segment slope 30: 40 + 30 * 1 = 70
    assert curve.get(3.0) == pytest.approx(70.0)


# reads a FLAT Curve outside its table, once with Below/Above set and once
# without, where the first and last y-values are used instead.
# catches: an unset Above falling back to 0 or NaN, so x = 3 reads 0 instead
# of the last value 40.
@pytest.mark.parametrize(
    ("below", "above", "expected_below", "expected_above"),
    [
        # the values set are held on each side
        (-5.0, 99.0, -5.0, 99.0),
        # unset, the first and last y-values are held
        (None, None, 0.0, 40.0),
    ],
    ids=["below_above_set", "below_above_unset"],
)
def test_curve_flat_extrapolation_holds_a_value(
    below, above, expected_below, expected_above
):
    curve = _curve("FLAT", below=below, above=above)

    assert curve.get(-1.0) == pytest.approx(expected_below)
    assert curve.get(3.0) == pytest.approx(expected_above)
    # inside the table the lookup is untouched
    assert curve.get(1.0) == pytest.approx(10.0)


# reads a Curve with Extrapolate = FALSE below and above its table and expects
# an error both times.
# catches: FALSE quietly treated as FLAT, so an out-of-range year silently gets
# an end value instead of an error.
@pytest.mark.parametrize("x", [-1.0, 3.0], ids=["below", "above"])
def test_curve_without_extrapolation_refuses_a_lookup_outside(x):
    with pytest.raises(ValueError, match="interpolation range"):
        _curve("FALSE").get(x)


# reads a Surface outside its grid with LINEAR (continues the slope) and with
# FLAT (returns Outside), and checks a point inside is unchanged.
# catches: Outside ignored by FLAT, so a lookup off the grid reads the edge
# value 4 instead of -1.
@pytest.mark.parametrize(
    ("extrapolate", "outside", "expected"),
    [
        # along y = 0, z rises 4 over x 0 -> 2, slope 2: 4 + 2 * 1 = 6
        ("LINEAR", None, 6.0),
        # Outside everywhere off the grid
        ("FLAT", -1.0, -1.0),
    ],
)
def test_surface_extrapolates_by_its_mode(extrapolate, outside, expected):
    surface = _surface(extrapolate, outside)

    assert surface.get(3.0, 0.0) == pytest.approx(expected)
    # inside the grid the lookup is untouched: the mean of the four corners
    assert surface.get(1.0, 5.0) == pytest.approx((0.0 + 10.0 + 4.0 + 30.0) / 4)


# reads a Surface with Extrapolate = FALSE outside its grid and expects an error.
# catches: the 2D table built with bounds checks off, so an off-grid lookup
# returns a made-up value instead of failing.
def test_surface_without_extrapolation_refuses_a_lookup_outside():
    with pytest.raises(ValueError, match="out of bounds"):
        _surface("FALSE").get(3.0, 0.0)


# builds a Curve with PREVIOUS or NEXT interpolation and the default LINEAR
# extrapolation and expects the build to fail.
# catches: the consistency check dropped, so a step table is extended with a
# slope it does not have.
@pytest.mark.parametrize("interpolate", ["PREVIOUS", "NEXT"])
def test_step_interpolation_refuses_linear_extrapolation(interpolate):
    # a step table continued linearly has no meaningful slope; LINEAR is the
    # default, so leaving 'Extrapolate' unset is refused too
    curve = Curve("c")
    curve.set_interpolate(interpolate)
    curve.set_table(TableData(rows=CURVE_ROWS))

    with pytest.raises(ValueError, match="'Extrapolate' must not be LINEAR"):
        curve.build_table()


# asks a Surface and a Timetable with FLAT extrapolation but no Outside value to
# check themselves, and expects an error.
# catches: a FLAT 2D table without Outside accepted, so an off-grid lookup has
# no value to return and fails mid-run instead of at deck load.
@pytest.mark.parametrize("node_class", [Surface, Timetable])
def test_flat_2d_table_requires_outside(node_class):
    node = node_class("t")
    node.set_extrapolate("FLAT")

    with pytest.raises(ValueError, match="'Outside' must be defined"):
        node.check_consistency()
