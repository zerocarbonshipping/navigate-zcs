# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Mathematical stability tests for the calculator pipeline.

Tests verify the correctness of:
  - Addition/multiplier transforms: output = truncate(multiplier * (table(x) + addition))
  - Bound application: internal vs external bounds widen the envelope
  - Convexity detection on piecewise-linear functions
  - _Table1D interpolation with transforms, reverse lookup, pickle round-trip
  - _Table2D bilinear interpolation, reverse lookup, convexity, pickle round-trip
  - Variable scalar transform chain
"""
import pickle

import numpy as np
import pytest

from navigate.core.nodes._calculator import _Calculator
from navigate.core.nodes._table1d import _Table1D
from navigate.core.nodes._table2d import _Table2D

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TABLE_X = np.array([0., 1., 2., 3., 4.])
TABLE_Y = np.array([0., 1., 4., 9., 16.])  # ~ x^2, convex


def _make_table1d(x=TABLE_X, y=TABLE_Y, extrapolate='LINEAR'):
    t = _Table1D()
    t.set_extrapolate(extrapolate)
    t._set_table(x, y)
    return t


# ---------------------------------------------------------------------------
# 1. _Calculator base — truncation and bound logic
# ---------------------------------------------------------------------------

class TestTruncateTransform:
    """Verify: output = truncate(multiplier * (value + addition))."""

    def test_identity_transform(self):
        """Default multiplier=1, addition=0 is the identity."""
        c = _Calculator()
        assert c._truncate(5.0) == 5.0

    def test_multiplier_scales(self):
        t = _make_table1d()
        t.set_multiplier(2.0)
        # At x=2 the raw table gives 4.0; output = 2 * (4 + 0) = 8
        assert t.calculate(2.0) == pytest.approx(8.0)

    def test_addition_shifts(self):
        t = _make_table1d()
        t.set_addition(10.0)
        # At x=2: output = 1 * (4 + 10) = 14
        assert t.calculate(2.0) == pytest.approx(14.0)

    def test_combined_multiplier_addition(self):
        t = _make_table1d()
        t.set_multiplier(3.0)
        t.set_addition(-1.0)
        # At x=2: output = 3 * (4 + (-1)) = 9
        assert t.calculate(2.0) == pytest.approx(9.0)

    def test_negative_multiplier_flips_curve(self):
        t = _make_table1d()
        t.set_multiplier(-1.0)
        # At x=2: output = -1 * (4 + 0) = -4
        assert t.calculate(2.0) == pytest.approx(-4.0)

    def test_zero_multiplier_collapses_output(self):
        t = _make_table1d()
        t.set_multiplier(0.0)
        # At x=2: output = 0 * (4 + 0) = 0 regardless of input
        assert t.calculate(2.0) == pytest.approx(0.0)
        assert t.calculate(4.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 2. Bound application — internal vs external
# ---------------------------------------------------------------------------

class TestBoundApplication:
    """Applied bounds tighten: applied_lower = max(external, internal),
    applied_upper = min(external, internal).
    Truncate then clamps: output = max(min(value, upper), lower)."""

    def test_truncate_clamps_to_applied_bounds(self):
        """Direct _truncate with manually set applied bounds."""
        c = _Calculator()
        c._applied_lower_bound = 2.0
        c._applied_upper_bound = 8.0
        assert c._truncate(1.0) == pytest.approx(2.0)
        assert c._truncate(5.0) == pytest.approx(5.0)
        assert c._truncate(10.0) == pytest.approx(8.0)

    def test_truncate_works_on_arrays(self):
        c = _Calculator()
        c._applied_lower_bound = 2.0
        c._applied_upper_bound = 8.0
        result = c._truncate(np.array([0., 5., 12.]))
        np.testing.assert_array_almost_equal(result, [2., 5., 8.])

    def test_lower_bound_clamps(self):
        t = _make_table1d()
        t.set_lower_bound(5.0)
        # At x=1, raw=1.0 → clamped to 5
        assert t.calculate(1.0) == pytest.approx(5.0)

    def test_upper_bound_clamps(self):
        t = _make_table1d()
        t.set_upper_bound(3.0)
        # At x=2, raw=4.0 → clamped to 3
        assert t.calculate(2.0) == pytest.approx(3.0)

    def test_tightening_logic_lower(self):
        """applied_lower = max(external, internal) — the tighter (most restrictive) wins."""
        c = _Calculator()
        c.set_lower_bound(3.0)
        c.set_internal_lower_bound(5.0)
        c._assign_applied_bounds()
        # max(3, 5) = 5
        assert c._applied_lower_bound == pytest.approx(5.0)

    def test_tightening_logic_upper(self):
        """applied_upper = min(external, internal) — the tighter (most restrictive) wins."""
        c = _Calculator()
        c.set_upper_bound(8.0)
        c.set_internal_upper_bound(5.0)
        c._assign_applied_bounds()
        # min(8, 5) = 5
        assert c._applied_upper_bound == pytest.approx(5.0)

    def test_bounds_with_array_input(self):
        t = _make_table1d()
        t.set_lower_bound(2.0)
        t.set_upper_bound(10.0)
        result = t.calculate(np.array([0., 1., 2., 3., 4.]))
        assert np.all(result >= 2.0 - 1e-12)
        assert np.all(result <= 10.0 + 1e-12)


# ---------------------------------------------------------------------------
# 3. Convexity detection
# ---------------------------------------------------------------------------

class TestConvexity:
    """_test_convexity checks d2y/dx2 >= 0 for piecewise-linear (x, y)."""

    def test_convex_quadratic(self):
        """x^2 sampled at integers is convex."""
        x = np.array([0., 1., 2., 3., 4.])
        y = x ** 2
        assert _Calculator._test_convexity(x, y) is True

    def test_concave_function(self):
        """sqrt(x) is concave."""
        x = np.array([1., 4., 9., 16.])
        y = np.sqrt(x)  # [1, 2, 3, 4] — but slopes decrease: 1/3, 1/5, 1/7
        assert _Calculator._test_convexity(x, y) is False

    def test_linear_is_convex(self):
        """A straight line has d2y/dx2 = 0, which counts as convex."""
        x = np.array([0., 1., 2., 3.])
        y = 2.0 * x + 5.0
        assert _Calculator._test_convexity(x, y) is True

    def test_two_points_always_convex(self):
        """With < 3 points, short-circuits to True."""
        x = np.array([0., 1.])
        y = np.array([0., 100.])
        assert _Calculator._test_convexity(x, y) is True

    def test_single_point_always_convex(self):
        x = np.array([0.])
        y = np.array([0.])
        assert _Calculator._test_convexity(x, y) is True

    def test_nearly_convex_within_rounding(self):
        """A tiny concavity below 10^-5 is rounded away (ROUND_OFF=5)."""
        x = np.array([0., 1., 2.])
        # slopes: 1.0 and 1.0 - 1e-7 → d2y ~ -1e-7, rounds to 0
        y = np.array([0., 1.0, 2.0 - 1e-7])
        assert _Calculator._test_convexity(x, y) is True

    def test_clearly_concave_not_rounded_away(self):
        """A concavity of ~0.01 is NOT rounded away."""
        x = np.array([0., 1., 2.])
        y = np.array([0., 1.0, 1.99])  # slopes: 1.0, 0.99 → d2y = -0.01
        assert _Calculator._test_convexity(x, y) is False

    def test_convexity_propagates_to_table1d(self):
        """_Table1D sets is_convex on construction."""
        t = _make_table1d()  # x^2 data
        assert t.is_convex() is True

        t2 = _make_table1d(y=np.sqrt(TABLE_X + 1))  # concave
        assert t2.is_convex() is False


# ---------------------------------------------------------------------------
# 4. _Table1D — reverse lookup
# ---------------------------------------------------------------------------

class TestTable1DReverseLookup:
    """reverse_lookup finds x given y on a monotonically increasing curve."""

    def test_exact_grid_point(self):
        t = _make_table1d()
        x = t.reverse_lookup(4.0)
        assert x == pytest.approx(2.0)

    def test_interpolated_point(self):
        """Midpoint between y=1 (x=1) and y=4 (x=2) → x ≈ 1.5 via linear interp on the transformed curve."""
        x = np.array([0., 1., 2., 3.])
        y = np.array([0., 2., 4., 6.])  # strictly increasing, linear
        t = _make_table1d(x=x, y=y)
        result = t.reverse_lookup(3.0)
        assert result == pytest.approx(1.5)

    def test_non_monotonic_returns_none(self):
        """Non-monotonic y-values → reverse_lookup returns None."""
        x = np.array([0., 1., 2., 3.])
        y = np.array([0., 5., 3., 8.])  # not strictly increasing
        t = _make_table1d(x=x, y=y)
        assert t.reverse_lookup(4.0) is None

    def test_reverse_lookup_nearest(self):
        """Non-interpolating reverse lookup snaps to nearest grid point."""
        x = np.array([0., 1., 2., 3.])
        y = np.array([0., 2., 4., 6.])
        t = _make_table1d(x=x, y=y)
        result = t.reverse_lookup(3.1, interpolate=False)
        assert result == pytest.approx(2.0)  # nearest to y=4? No, find_nearest to 3.1 → y=4 at x=2


# ---------------------------------------------------------------------------
# 5. _Table1D — pickle round-trip
# ---------------------------------------------------------------------------

class TestTable1DPickle:
    """interp1d is not picklable; _Table1D handles this via __getstate__/__setstate__."""

    def test_pickle_preserves_results(self):
        t = _make_table1d()
        original = t.calculate(np.array([0.5, 1.5, 2.5]))

        data = pickle.dumps(t)
        t2 = pickle.loads(data)

        np.testing.assert_array_almost_equal(
            t2.calculate(np.array([0.5, 1.5, 2.5])),
            original
        )

    def test_pickle_preserves_settings(self):
        t = _make_table1d()
        t.set_multiplier(2.0)
        t.set_addition(3.0)
        t.set_lower_bound(1.0)

        data = pickle.dumps(t)
        t2 = pickle.loads(data)

        assert t2.get_multiplier() == pytest.approx(2.0)
        assert t2.get_addition() == pytest.approx(3.0)
        assert t2.calculate(0.0) == pytest.approx(max(2.0 * (0.0 + 3.0), 1.0))


# ---------------------------------------------------------------------------
# 6. _Table2D — bilinear interpolation
# ---------------------------------------------------------------------------

# Simple 3x3 grid: z = x + y
T2D_X = np.array([0., 1., 2.])
T2D_Y = np.array([0., 10., 20.])
T2D_Z = np.array([[0., 10., 20.],
                  [1., 11., 21.],
                  [2., 12., 22.]])  # z[i,j] = x[i] + y[j]


def _make_table2d(x=T2D_X, y=T2D_Y, z=T2D_Z, extrapolate='LINEAR'):
    t = _Table2D()
    t.set_extrapolate(extrapolate)
    t._set_table(x, y, z)
    return t


class TestTable2DInterpolation:
    """Bilinear interpolation on z = x + y surface."""

    def test_exact_grid_points(self):
        t = _make_table2d()
        assert t.calculate(1.0, 10.0) == pytest.approx(11.0)
        assert t.calculate(0.0, 0.0) == pytest.approx(0.0)
        assert t.calculate(2.0, 20.0) == pytest.approx(22.0)

    def test_midpoint_interpolation(self):
        """Midpoint on a bilinear surface of z=x+y should be exact."""
        t = _make_table2d()
        assert t.calculate(0.5, 5.0) == pytest.approx(5.5)
        assert t.calculate(1.5, 15.0) == pytest.approx(16.5)

    def test_array_inputs(self):
        t = _make_table2d()
        x = np.array([0., 1., 2.])
        y = np.array([0., 10., 20.])
        result = t.calculate(x, y)
        np.testing.assert_array_almost_equal(result, [0., 11., 22.])

    def test_scalar_array_broadcast(self):
        """Scalar x with array y broadcasts correctly."""
        t = _make_table2d()
        result = t.calculate(1.0, np.array([0., 10., 20.]))
        np.testing.assert_array_almost_equal(result, [1., 11., 21.])

    def test_multiplier_addition_applied(self):
        t = _make_table2d()
        t.set_multiplier(2.0)
        t.set_addition(1.0)
        # At (1, 10): raw=11, output = 2*(11+1) = 24
        assert t.calculate(1.0, 10.0) == pytest.approx(24.0)


# ---------------------------------------------------------------------------
# 7. _Table2D — convexity
# ---------------------------------------------------------------------------

class TestTable2DConvexity:
    """Convexity is checked along all x-direction paths."""

    def test_linear_surface_is_convex(self):
        """z = x + y is linear in x → convex."""
        t = _make_table2d()
        assert t.is_convex()

    def test_convex_surface(self):
        """z = x^2 + y is convex in x."""
        x = np.array([0., 1., 2., 3.])
        y = np.array([0., 1.])
        z = np.array([[0., 1.],
                      [1., 2.],
                      [4., 5.],
                      [9., 10.]])
        t = _make_table2d(x=x, y=y, z=z)
        assert t.is_convex()

    def test_concave_surface(self):
        """z = sqrt(x) + y is concave in x."""
        x = np.array([1., 4., 9., 16.])
        y = np.array([0., 1.])
        z = np.array([[1., 2.],
                      [2., 3.],
                      [3., 4.],
                      [4., 5.]])  # sqrt(x) + y
        t = _make_table2d(x=x, y=y, z=z)
        assert not t.is_convex()


# ---------------------------------------------------------------------------
# 8. _Table2D — reverse lookup
# ---------------------------------------------------------------------------

class TestTable2DReverseLookup:
    """Reverse lookup finds x given z along y-slices."""

    def test_exact_reverse(self):
        """On z=x+y, reverse_lookup(z=11, y=[10]) should give x=1."""
        t = _make_table2d()
        result = t.reverse_lookup(11.0, y=np.array([10.0]))
        assert result is not None
        np.testing.assert_array_almost_equal(result, [1.0])

    def test_reverse_interpolated(self):
        """On z=x+y, reverse_lookup(z=5.5, y=[5]) → x=0.5."""
        t = _make_table2d()
        result = t.reverse_lookup(5.5, y=np.array([5.0]))
        assert result is not None
        np.testing.assert_array_almost_equal(result, [0.5])

    def test_reverse_multiple_slices(self):
        t = _make_table2d()
        result = t.reverse_lookup(11.0, y=np.array([0., 10., 20.]))
        # z=11, y=0  → x=11 (extrapolated); y=10 → x=1; y=20 → x<0 (extrapolated)
        assert result is not None
        assert result.shape == (3,)
        np.testing.assert_almost_equal(result[1], 1.0)


# ---------------------------------------------------------------------------
# 9. _Table2D — pickle round-trip
# ---------------------------------------------------------------------------

class TestTable2DPickle:

    def test_pickle_preserves_results(self):
        t = _make_table2d()
        original = t.calculate(np.array([0.5, 1.5]), np.array([5.0, 15.0]))

        data = pickle.dumps(t)
        t2 = pickle.loads(data)

        np.testing.assert_array_almost_equal(
            t2.calculate(np.array([0.5, 1.5]), np.array([5.0, 15.0])),
            original
        )


# ---------------------------------------------------------------------------
# 10. Variable — transform chain
# ---------------------------------------------------------------------------

class TestVariable:
    """Variable.get() applies: truncate(multiplier * (value + addition))."""

    def test_plain_value(self):
        from navigate.core.nodes.variable import Variable
        v = Variable('test')
        v.set_value(5.0)
        assert v.get() == pytest.approx(5.0)

    def test_multiplier_addition(self):
        from navigate.core.nodes.variable import Variable
        v = Variable('test')
        v.set_value(5.0)
        v.set_multiplier(2.0)
        v.set_addition(3.0)
        # output = 2 * (5 + 3) = 16
        assert v.get() == pytest.approx(16.0)

    def test_bounds_clamp(self):
        from navigate.core.nodes.variable import Variable
        v = Variable('test')
        v.set_value(100.0)
        v.set_upper_bound(50.0)
        assert v.get() == pytest.approx(50.0)

    def test_get_ignores_dummy_args(self):
        """get(x, y) signature accepts but ignores positional args."""
        from navigate.core.nodes.variable import Variable
        v = Variable('test')
        v.set_value(7.0)
        assert v.get(x=99., y=99.) == pytest.approx(7.0)
