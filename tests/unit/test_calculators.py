# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Mathematical stability tests for the calculator pipeline.

Tests verify the correctness of:
  - Addition/multiplier transforms:
    output = truncate(multiplier * (table(x) + addition))
  - Bound application: the tighter of the internal and external bounds applies
  - Internal-bound tightening: the warning names the node it tightens
  - Exclusive bounds: a value reaching one raises instead of being clamped
  - Public bounds: each rejects the infinity on the other side
  - Convexity detection on piecewise-linear functions
  - _Table1D and _Table2D reverse lookup
  - Variable broadcasting to an array input
  - Deck expressions on the transform and fill-value attributes
  - Curve and Surface settings apply wherever the definition writes them
  - Table input validation: minimum size, non-finite entries
"""

from __future__ import annotations

import logging

import numpy as np
import pytest

from navigate.core.bounds import Bounds
from navigate.core.expression import Expression
from navigate.core.nodes._calculator import _Calculator
from navigate.core.nodes._table1d import _Table1D, check_table1d_input
from navigate.core.nodes._table2d import _Table2D, check_table2d_input
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.surface import Surface
from navigate.core.nodes.variable import Variable
from navigate.core.table_data import TableData

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TABLE_X = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
TABLE_Y = np.array([0.0, 1.0, 4.0, 9.0, 16.0])  # ~ x^2, convex

# Simple 3x3 grid: z = x + y
T2D_X = np.array([0.0, 1.0, 2.0])
T2D_Y = np.array([0.0, 10.0, 20.0])
T2D_Z = np.array(
    [[0.0, 10.0, 20.0], [1.0, 11.0, 21.0], [2.0, 12.0, 22.0]]
)  # z[i,j] = x[i] + y[j]

# y = 10 * x on 0 <= x <= 2
CURVE_ROWS = [[0.0, 0.0], [1.0, 10.0], [2.0, 20.0]]

# y-values in the header row, then one row per x-value: z = x + y
SURFACE_ROWS = [
    [0.0, 10.0],
    [0.0, 0.0, 10.0],
    [1.0, 1.0, 11.0],
]


def _make_table1d(x=TABLE_X, y=TABLE_Y, extrapolate="LINEAR"):
    t = _Table1D()
    t.set_extrapolate(extrapolate)
    t._set_table(x, y)
    return t


def _make_table2d(x=T2D_X, y=T2D_Y, z=T2D_Z, extrapolate="LINEAR"):
    t = _Table2D()
    t.set_extrapolate(extrapolate)
    t._set_table(x, y, z)
    return t


def _variable(value):
    variable = Variable("v")
    variable.set_value(value)
    return variable


def _curve():
    curve = Curve("c")
    curve.set_table(TableData(rows=CURVE_ROWS))
    curve.build_table()
    return curve


# ---------------------------------------------------------------------------
# 1. Transform and bound application
# ---------------------------------------------------------------------------


def test_addition_applies_inside_the_multiplier():
    # at x=2 the table gives 4: 3 * (4 + (-1)) = 9, where 3 * 4 - 1 would be 11
    t = _make_table1d()
    t.set_multiplier(3.0)
    t.set_addition(-1.0)
    assert t.calculate(2.0) == pytest.approx(9.0)


class TestBoundApplication:
    """
    Applied bounds tighten to the tighter of the external and internal bounds.

    applied_lower = max(external, internal), applied_upper = min(external, internal).
    Truncate then clamps: output = max(min(value, upper), lower).
    """

    @pytest.mark.parametrize(
        (
            "lower_bound",
            "upper_bound",
            "internal_lower",
            "internal_upper",
            "x",
            "expected",
        ),
        [
            # external upper bound alone clamps: at x=2, raw=4.0 → clamped to 3
            (-np.inf, 3.0, -np.inf, np.inf, 2.0, 3.0),
            # applied_lower = max(external, internal) = max(3, 5) = 5 — the tighter
            # wins; at x=0, raw=0.0 → clamped up to 5
            (3.0, np.inf, 5.0, np.inf, 0.0, 5.0),
            # applied_upper = min(external, internal) = min(8, 5) = 5 — the tighter
            # wins; at x=4, raw=16.0 → clamped down to 5
            (-np.inf, 8.0, -np.inf, 5.0, 4.0, 5.0),
        ],
    )
    def test_bound_tightening(
        self, lower_bound, upper_bound, internal_lower, internal_upper, x, expected
    ):
        t = _make_table1d()
        t.set_lower_bound(lower_bound)
        t.set_upper_bound(upper_bound)
        t.set_internal_bounds(internal_lower, internal_upper)
        assert t.calculate(x) == pytest.approx(expected)


def test_tightening_an_internal_bound_warns_naming_the_node(caplog):
    # the node is a Variable, so this also pins that it renders as its name
    # rather than its value
    v = _variable(1.0)
    v.set_internal_bounds(2.0, np.inf)

    with caplog.at_level(logging.WARNING):
        v.set_internal_bounds(3.0, np.inf)

    assert [record.getMessage() for record in caplog.records] == [
        'Variable("v"): Internal lower bound tightened from 2.0 to 3.0.'
    ]


@pytest.mark.parametrize(
    ("setter", "value"),
    [(Variable.set_upper_bound, -np.inf), (Variable.set_lower_bound, np.inf)],
    ids=["upper_at_minus_inf", "lower_at_inf"],
)
def test_public_bound_rejects_the_infinity_on_the_other_side(setter, value):
    # UpperBound takes INF for no upper bound, LowerBound -INF for no lower one
    with pytest.raises(ValueError, match=f"must be finite, but got {value}"):
        setter(_variable(1.0), value)


class TestExclusiveBounds:
    """
    A value reaching an exclusive internal bound raises instead of being clamped.

    The bound is exclusive only while it is the one applied: a public bound
    strictly inside it clamps inclusively. Merging offers, a strictly tighter
    one replaces the bound and its flag, and an equal exclusive one makes the
    bound exclusive.
    """

    @pytest.mark.parametrize(
        ("make_node", "args", "owner"),
        [
            (lambda: _variable(0.0), (), r'Variable\("v"\)'),
            # y = 10 * x, so only the entry at x = 0 is on the bound
            (_curve, (np.array([1.0, 0.0, 2.0]),), r'Curve\("c"\)'),
        ],
        ids=["scalar", "array_entry"],
    )
    def test_value_on_an_exclusive_bound_raises(self, make_node, args, owner):
        node = make_node()
        node.set_internal_bounds(0.0, np.inf, inclusive_lower=False)

        with pytest.raises(ValueError, match=rf"{owner}: must be > 0\.0, but got 0\.0"):
            node.get(*args)

    def test_public_bound_inside_an_exclusive_bound_clamps(self):
        # the public bound 1 is applied, not the exclusive 0, so -1 is clamped
        # up to 1 instead of raising
        v = _variable(-1.0)
        v.set_internal_bounds(0.0, np.inf, inclusive_lower=False)
        v.set_lower_bound(1.0)
        assert v.get() == pytest.approx(1.0)

    def test_public_bound_equal_to_an_exclusive_bound_stays_exclusive(self):
        v = _variable(0.0)
        v.set_internal_bounds(0.0, np.inf, inclusive_lower=False)
        v.set_lower_bound(0.0)

        with pytest.raises(ValueError, match=r"must be > 0\.0, but got 0\.0"):
            v.get()

    @pytest.mark.parametrize(
        ("first", "second", "expected"),
        [
            # an equal exclusive offer makes the inclusive bound exclusive
            ((0.0, True), (0.0, False), Bounds(0.0, np.inf, False, True)),
            # a strictly tighter inclusive offer replaces bound and flag
            ((0.0, False), (1.0, True), Bounds(1.0, np.inf, True, True)),
            # a looser exclusive offer is ignored
            ((0.0, True), (-1.0, False), Bounds(0.0, np.inf, True, True)),
        ],
        ids=["exclusive_wins_a_tie", "tighter_replaces", "looser_ignored"],
    )
    def test_merged_offers(self, first, second, expected):
        v = _variable(1.0)
        for lower, inclusive_lower in (first, second):
            v.set_internal_bounds(lower, np.inf, inclusive_lower=inclusive_lower)

        assert v.internal_bounds == expected

    @pytest.mark.parametrize(
        ("value", "bounds", "message"),
        [
            (
                np.array([1.0, np.nan, np.inf]),
                Bounds(0.0, np.inf, True, False),
                "must be finite, but got inf",
            ),
            (
                np.array([np.nan, -2.0, 1.0]),
                Bounds(0.0, np.inf, False, True),
                r"must be > 0\.0, but got -2\.0",
            ),
        ],
        ids=["inf_beside_nan", "below_beside_nan"],
    )
    def test_message_names_the_breaking_entry_beside_nan(self, value, bounds, message):
        # a NaN entry breaks no bound, so it is not the value reported
        with pytest.raises(ValueError, match=rf"^owner: {message}$"):
            bounds.check_exclusive(value, "owner")


# ---------------------------------------------------------------------------
# 2. Convexity detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("x", "y", "expected"),
    [
        # sqrt(x) is concave: y = [1, 2, 3, 4], but slopes decrease: 1/3, 1/5, 1/7
        (
            np.array([1.0, 4.0, 9.0, 16.0]),
            np.sqrt(np.array([1.0, 4.0, 9.0, 16.0])),
            False,
        ),
        # a straight line has d2y/dx2 = 0, which counts as convex
        (
            np.array([0.0, 1.0, 2.0, 3.0]),
            2.0 * np.array([0.0, 1.0, 2.0, 3.0]) + 5.0,
            True,
        ),
        # with < 3 points there is no second derivative, which counts as convex
        (np.array([0.0, 1.0]), np.array([0.0, 100.0]), True),
        # a tiny concavity below 10^-5 is rounded away (ROUND_OFF=5)
        (np.array([0.0, 1.0, 2.0]), np.array([0.0, 1.0, 2.0 - 1e-7]), True),
        # a concavity of ~0.01 is NOT rounded away: slopes 1.0, 0.99 → d2y = -0.01
        (np.array([0.0, 1.0, 2.0]), np.array([0.0, 1.0, 1.99]), False),
    ],
)
def test_convexity(x, y, expected):
    """_test_convexity checks d2y/dx2 >= 0 for piecewise-linear (x, y)."""
    assert _Calculator._test_convexity(x, y) is expected


def test_table2d_with_one_concave_slice_is_not_convex():
    # convexity is checked along every y-slice: the slice at y=0 is x^2, convex,
    # the one at y=1 has slopes 3, 1, 0.5, concave
    x = np.array([0.0, 1.0, 2.0, 3.0])
    y = np.array([0.0, 1.0])
    z = np.array([[0.0, 0.0], [1.0, 3.0], [4.0, 4.0], [9.0, 4.5]])
    assert not _make_table2d(x=x, y=y, z=z).is_convex()


# ---------------------------------------------------------------------------
# 3. Reverse lookup
# ---------------------------------------------------------------------------


class TestTable1DReverseLookup:
    """reverse_lookup finds x given y on a strictly increasing curve."""

    def test_non_monotonic_returns_none(self):
        x = np.array([0.0, 1.0, 2.0, 3.0])
        y = np.array([0.0, 5.0, 3.0, 8.0])  # not strictly increasing
        t = _make_table1d(x=x, y=y)
        assert t.reverse_lookup(4.0) is None

    def test_looks_up_the_transformed_curve(self):
        # the multiplier and addition apply before the lookup, so the power a
        # deck scaled its load to is the one a speed is found for:
        # 2 * (x^2 + 1) = [2, 4, 10, 20, 34], and 15 lies halfway from x=2 to x=3;
        # the raw table would give 3 + 6/7
        t = _make_table1d()
        t.set_multiplier(2.0)
        t.set_addition(1.0)
        assert t.reverse_lookup(15.0) == pytest.approx(2.5)


def test_table2d_reverse_lookup_clamps_to_the_table_ends():
    # on z = x + y with x in [0, 2], z = 11 lies beyond the y=0 slice [0, 2], on
    # the y=10 slice [10, 12] at x = 1, and below the y=20 slice [20, 22]; the
    # lookup clamps to the end x-values rather than extrapolating. The speed
    # limits in fleet/power.py rely on this: a power capacity beyond the
    # propulsion load's range gives the load's own end speed
    t = _make_table2d()
    result = t.reverse_lookup(11.0, y=np.array([0.0, 10.0, 20.0]))
    np.testing.assert_array_almost_equal(result, [2.0, 1.0, 0.0])


# ---------------------------------------------------------------------------
# 4. Broadcasting
# ---------------------------------------------------------------------------


def test_table2d_scalar_x_broadcasts_over_array_y():
    np.testing.assert_array_almost_equal(
        _make_table2d().calculate(1.0, np.array([0.0, 10.0, 20.0])), [1.0, 11.0, 21.0]
    )


def test_variable_array_x_broadcasts_the_value_to_its_shape():
    """An array x broadcasts the transformed value, like Scalar.get."""
    v = _variable(5.0)
    v.set_multiplier(2.0)
    v.set_addition(3.0)
    x = np.zeros((2, 3))
    # output = 2 * (5 + 3) = 16, broadcast to x's shape
    result = v.get(x)
    assert isinstance(result, np.ndarray)
    np.testing.assert_array_equal(result, np.full((2, 3), 16.0))


# ---------------------------------------------------------------------------
# 5. Deck expressions on the transform and fill-value attributes
# ---------------------------------------------------------------------------


def _read_no_reference(reference_string, location):
    raise AssertionError(f"unexpected node reference {reference_string}")


def _resolve(node, *expressions):
    """Resolve expressions the way the parser does once the deck is read."""
    for expression in expressions:
        expression.resolve(node, _read_no_reference)


def test_transform_expressions_are_evaluated():
    t = _make_table1d()
    multiplier = Expression("1.5 * 2")
    addition = Expression("0.5 + 0.5")
    t.set_multiplier(multiplier)
    t.set_addition(addition)
    _resolve(t, multiplier, addition)
    # table(1) = 1, table(2) = 4: output = [3 * (1 + 1), 3 * (4 + 1)]
    np.testing.assert_array_almost_equal(t.calculate(np.array([1.0, 2.0])), [6.0, 15.0])


def _table1d_with_fill_expressions():
    t = _Table1D()
    below = Expression("-1 * 2")
    above = Expression("10 + 5")
    t.set_extrapolate("FLAT")
    t.set_below(below)
    t.set_above(above)
    t._set_table(TABLE_X, TABLE_Y)
    return t, (below, above)


def _table2d_with_fill_expression():
    t = _Table2D()
    outside = Expression("3 * 3")
    t.set_extrapolate("FLAT")
    t.set_outside(outside)
    t._set_table(T2D_X, T2D_Y, T2D_Z)
    return t, (outside,)


@pytest.mark.parametrize(
    ("make_table", "args", "expected"),
    [
        # inside the table x^2; below it -2, above it 15
        (
            _table1d_with_fill_expressions,
            (np.array([-1.0, 2.0, 5.0]),),
            [-2.0, 4.0, 15.0],
        ),
        # inside the grid z = x + y; outside it 9
        (
            _table2d_with_fill_expression,
            (np.array([1.0, 5.0]), np.array([10.0, 10.0])),
            [11.0, 9.0],
        ),
    ],
    ids=["table1d_below_above", "table2d_outside"],
)
def test_fill_value_expressions_are_evaluated(make_table, args, expected):
    # the table is built before the expressions are resolved, so the values
    # must be read on lookup
    t, expressions = make_table()
    _resolve(t, *expressions)
    np.testing.assert_array_almost_equal(t.calculate(*args), expected)


# ---------------------------------------------------------------------------
# 6. Curve and Surface — settings read when the table is built
# ---------------------------------------------------------------------------


def _set_curve_extrapolation(curve):
    curve.set_extrapolate("FLAT")
    curve.set_below(5.0)


def _set_surface_extrapolation(surface):
    surface.set_extrapolate("FLAT")
    surface.set_outside(9.0)


class TestTableSettingsOrder:
    """The extrapolation settings apply whether written before or after Table."""

    @pytest.mark.parametrize("settings_first", [True, False])
    @pytest.mark.parametrize(
        ("node_class", "rows", "set_extrapolation", "args", "expected"),
        [
            # below the table the flat value 5, not the linear extrapolation -10
            (Curve, CURVE_ROWS, _set_curve_extrapolation, (-1.0,), 5.0),
            # outside the table the flat value 9, not the linear extrapolation 13
            (Surface, SURFACE_ROWS, _set_surface_extrapolation, (3.0, 10.0), 9.0),
        ],
        ids=["curve", "surface"],
    )
    def test_settings_apply(
        self, node_class, rows, set_extrapolation, args, expected, settings_first
    ):
        node = node_class("t")
        if settings_first:
            set_extrapolation(node)
        node.set_table(TableData(rows=rows))
        if not settings_first:
            set_extrapolation(node)
        node.build_table()
        assert node.get(*args) == pytest.approx(expected)

    def test_curve_rejects_a_step_interpolation_set_after_the_table(self):
        # PREVIOUS with the default LINEAR extrapolation is refused
        curve = Curve("c")
        curve.set_table(TableData(rows=CURVE_ROWS))
        curve.set_interpolate("PREVIOUS")
        with pytest.raises(ValueError, match="'Extrapolate' must not be LINEAR"):
            curve.build_table()


# ---------------------------------------------------------------------------
# 7. Table input validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rows", "match"),
    [
        pytest.param(
            [[0.0, 1.0], [0.0, 5.0, 6.0]],
            r"'x' \(1\) and 'y' \(2\) must each be at least of length 2",
            id="single_data_row",
        ),
        pytest.param(
            [[0.0], [0.0, 5.0], [1.0, 6.0]],
            r"'x' \(2\) and 'y' \(1\) must each be at least of length 2",
            id="single_y_column",
        ),
    ],
)
def test_surface_shorter_than_2x2_is_rejected(rows, match):
    with pytest.raises(ValueError, match=match):
        Surface("s").set_table(TableData(rows=rows))


INF = np.inf
NAN = np.nan


class TestNonFiniteTableInput:
    """
    A table rejects NaN anywhere and an infinite coordinate; an INF value passes.

    Interpolating across an infinite coordinate gives NaN, and NaN passes every
    bound, as a comparison with it is always false. An INF value is left to the
    bounds of the attribute the table is assigned to.
    """

    @pytest.mark.parametrize(
        ("check", "arrays", "match"),
        [
            (check_table1d_input, ([0.0, INF], [1.0, 2.0]), "'x' must be finite"),
            (check_table1d_input, ([0.0, 1.0], [1.0, NAN]), "'y' must not be NaN"),
            (
                check_table2d_input,
                ([0.0, 1.0], [0.0, 1.0], [[1.0, NAN], [3.0, 4.0]]),
                "'z' must not be NaN",
            ),
        ],
        ids=["1d_inf_x", "1d_nan_y", "2d_nan_z"],
    )
    def test_rejects(self, check, arrays, match):
        with pytest.raises(ValueError, match=match):
            check(*(np.array(a) for a in arrays))

    @pytest.mark.parametrize(
        ("check", "arrays"),
        [
            (check_table1d_input, ([0.0, 1.0], [1.0, INF])),
            (check_table2d_input, ([0.0, 1.0], [0.0, 1.0], [[1.0, INF], [-INF, 4.0]])),
        ],
        ids=["1d", "2d"],
    )
    def test_accepts_an_infinite_value(self, check, arrays):
        assert check(*(np.array(a) for a in arrays)) is None
