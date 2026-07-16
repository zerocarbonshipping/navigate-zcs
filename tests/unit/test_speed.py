# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Mathematical coherence tests for the speed management pipeline.

Tests verify the correctness of:
  - Mean-to-speeds conversion with clamping (_mean_to_speeds)
  - Rate-limited speed updates (_update_mean_speed)
  - Speed anchor shifting (_shift_speed_to_anchor)
  - Feasible speed bounds (calculate_speed_bounds)
  - Dual-variable saving formula (_calculate_dual_variable_saving)
"""
import numpy as np
import pytest
from scipy.optimize import minimize_scalar

from navigate.route.speed import SpeedResult, _mean_to_speeds, _update_mean_speed
from navigate.vessel.heuristic import _calculate_dual_variable_saving
from navigate.vessel.power import calculate_speed_bounds

# ---------------------------------------------------------------------------
# 1. Mean-to-speeds conversion
# ---------------------------------------------------------------------------

class TestMeanToSpeeds:
    """Verify: speeds = clip(mu + deltas, speed_min, speed_max)."""

    def test_unclamped_preserves_shape(self):
        """When within bounds, output = mu + deltas."""
        deltas = np.array([-2., 0., 2.])
        speed_min = np.array([0., 0., 0.])
        speed_max = np.array([30., 30., 30.])
        result = _mean_to_speeds(15., deltas, speed_min, speed_max)
        np.testing.assert_array_almost_equal(result, [13., 15., 17.])

    def test_identity_at_reference_mean(self):
        """When mu equals the original mean, output matches reference speeds."""
        speeds_ref = np.array([12., 14., 16.])
        mu_ref = np.mean(speeds_ref)
        deltas = speeds_ref - mu_ref
        speed_min = np.full(3, 5.)
        speed_max = np.full(3, 25.)
        result = _mean_to_speeds(mu_ref, deltas, speed_min, speed_max)
        np.testing.assert_array_almost_equal(result, speeds_ref)

    def test_clamped_to_minimum(self):
        """Speeds below minimum are clamped up."""
        deltas = np.array([-5., 0., 5.])
        speed_min = np.array([8., 8., 8.])
        speed_max = np.array([30., 30., 30.])
        result = _mean_to_speeds(10., deltas, speed_min, speed_max)
        assert result[0] == pytest.approx(8.)  # 10-5=5 → clamped to 8
        assert result[1] == pytest.approx(10.)
        assert result[2] == pytest.approx(15.)

    def test_clamped_to_maximum(self):
        """Speeds above maximum are clamped down."""
        deltas = np.array([-2., 0., 2.])
        speed_min = np.array([0., 0., 0.])
        speed_max = np.array([20., 20., 20.])
        result = _mean_to_speeds(19., deltas, speed_min, speed_max)
        assert result[0] == pytest.approx(17.)
        assert result[1] == pytest.approx(19.)
        assert result[2] == pytest.approx(20.)  # 19+2=21 → clamped to 20

    def test_all_outputs_within_bounds(self):
        """Regardless of mu, all outputs respect [min, max]."""
        deltas = np.array([-3., -1., 0., 1., 3.])
        speed_min = np.full(5, 6.)
        speed_max = np.full(5, 18.)
        for mu in [5., 10., 15., 20.]:
            result = _mean_to_speeds(mu, deltas, speed_min, speed_max)
            assert np.all(result >= speed_min)
            assert np.all(result <= speed_max)

    def test_per_leg_bounds(self):
        """Each leg can have different min/max bounds."""
        deltas = np.array([0., 0.])
        speed_min = np.array([8., 12.])
        speed_max = np.array([20., 16.])
        result = _mean_to_speeds(10., deltas, speed_min, speed_max)
        assert result[0] == pytest.approx(10.)
        assert result[1] == pytest.approx(12.)  # 10 < 12 → clamped up

    def test_uniform_shift(self):
        """Changing mu by +1 shifts all unclamped speeds by +1."""
        deltas = np.array([-2., 0., 2.])
        speed_min = np.full(3, 0.)
        speed_max = np.full(3, 30.)
        speeds_a = _mean_to_speeds(14., deltas, speed_min, speed_max)
        speeds_b = _mean_to_speeds(15., deltas, speed_min, speed_max)
        np.testing.assert_array_almost_equal(speeds_b - speeds_a, [1., 1., 1.])


# ---------------------------------------------------------------------------
# 2. Rate-limited speed update
# ---------------------------------------------------------------------------

class TestUpdateMeanSpeed:
    """Verify: mu_actual = mu_ref + clip(mu_target - mu_ref, -max, +max)."""

    def test_no_change_needed(self):
        """Target equals reference → no change."""
        assert _update_mean_speed(14., 14., 0.5) == pytest.approx(14.)

    def test_small_change_within_limit(self):
        """Change within maximum → target reached exactly."""
        assert _update_mean_speed(14., 14.3, 0.5) == pytest.approx(14.3)

    def test_large_decrease_clipped(self):
        """Large decrease → clipped to mu_ref - max_change."""
        assert _update_mean_speed(14., 10., 0.5) == pytest.approx(13.5)

    def test_large_increase_clipped(self):
        """Large increase → clipped to mu_ref + max_change."""
        assert _update_mean_speed(14., 20., 0.5) == pytest.approx(14.5)

    def test_symmetric_clipping(self):
        """Same magnitude increase and decrease are clipped symmetrically."""
        up = _update_mean_speed(14., 20., 1.0)
        down = _update_mean_speed(14., 8., 1.0)
        assert up - 14. == pytest.approx(14. - down)

    def test_infinite_max_change(self):
        """Infinite max_change → no constraint, target reached."""
        assert _update_mean_speed(14., 5., np.inf) == pytest.approx(5.)
        assert _update_mean_speed(14., 25., np.inf) == pytest.approx(25.)

    def test_zero_max_change(self):
        """Zero max_change → speed cannot change at all."""
        assert _update_mean_speed(14., 20., 0.) == pytest.approx(14.)

    @pytest.mark.parametrize('mu_ref,mu_target,max_change', [
        (10., 12., 0.5),
        (15., 11., 1.0),
        (20., 20., 0.1),
    ])
    def test_result_within_bounds(self, mu_ref, mu_target, max_change):
        """Result is always within [mu_ref - max, mu_ref + max]."""
        result = _update_mean_speed(mu_ref, mu_target, max_change)
        assert result >= mu_ref - max_change - 1e-10
        assert result <= mu_ref + max_change + 1e-10


# ---------------------------------------------------------------------------
# 3. Speed anchor shifting
# ---------------------------------------------------------------------------

class TestSpeedAnchorShift:
    """Verify: mu_adjusted = anchor_ref + (mu_optimal - anchor_opt).

    Tests the formula directly rather than _shift_speed_to_anchor (which
    mutates a SpeedResult with vessel expectations). The math is:
      adjusted = reference_anchor + (current_optimal - initial_optimal)
    """

    @staticmethod
    def _anchor_shift(anchor_ref, anchor_opt, mu_optimal):
        return anchor_ref + (mu_optimal - anchor_opt)

    def test_no_shift_when_optimal_unchanged(self):
        """If optimal hasn't moved from initial, result = reference anchor."""
        assert self._anchor_shift(14., 12., 12.) == pytest.approx(14.)

    def test_positive_shift(self):
        """1-knot improvement in optimal → 1-knot shift from reference."""
        assert self._anchor_shift(14., 12., 13.) == pytest.approx(15.)

    def test_negative_shift(self):
        """Optimal worsens by 2 knots → reference shifts down by 2."""
        assert self._anchor_shift(14., 12., 10.) == pytest.approx(12.)

    def test_shift_is_additive(self):
        """The shift is purely additive — independent of absolute levels."""
        delta = 0.5
        for anchor_ref in [10., 14., 20.]:
            for anchor_opt in [8., 12., 18.]:
                result = self._anchor_shift(anchor_ref, anchor_opt, anchor_opt + delta)
                assert result == pytest.approx(anchor_ref + delta)


# ---------------------------------------------------------------------------
# 4. Feasible speed bounds
# ---------------------------------------------------------------------------

class TestSpeedBounds:
    """Verify calculate_speed_bounds returns correct feasible range."""

    def test_normal_case(self):
        """Returns (min(speed_min), max(speed_max))."""
        speed_min = np.array([6., 7., 8.])
        speed_max = np.array([18., 20., 19.])
        speeds = np.array([12., 14., 16.])
        low, high = calculate_speed_bounds(speed_min, speed_max, speeds)
        assert low == pytest.approx(6.)
        assert high == pytest.approx(20.)

    def test_scalar_bounds(self):
        speed_min = np.array([8., 8.])
        speed_max = np.array([20., 20.])
        speeds = np.array([12., 14.])
        low, high = calculate_speed_bounds(speed_min, speed_max, speeds)
        assert low == pytest.approx(8.)
        assert high == pytest.approx(20.)

    def test_fallback_on_infinite_bounds(self):
        """Non-finite bounds → falls back to reference speed envelope."""
        speed_min = np.array([-np.inf, -np.inf])
        speed_max = np.array([np.inf, np.inf])
        speeds = np.array([10., 18.])
        low, high = calculate_speed_bounds(speed_min, speed_max, speeds)
        assert low == pytest.approx(10.)
        assert high == pytest.approx(18.)

    def test_fallback_on_invalid_range(self):
        """Low >= high → falls back to reference speed envelope."""
        speed_min = np.array([15., 15.])
        speed_max = np.array([15., 15.])
        speeds = np.array([10., 20.])
        low, high = calculate_speed_bounds(speed_min, speed_max, speeds)
        assert low == pytest.approx(10.)
        assert high == pytest.approx(20.)


# ---------------------------------------------------------------------------
# 5. Dual-variable saving formula
# ---------------------------------------------------------------------------

class TestDualVariableSaving:
    """Verify: saving = shadow_price * (baseline - residual)."""

    def test_speed_reduction_saves(self):
        """Residual < baseline → positive saving."""
        saving = _calculate_dual_variable_saving(80., 100., 10.)
        assert saving == pytest.approx(200.)  # 10 * (100-80)

    def test_speed_increase_costs(self):
        """Residual > baseline → negative saving."""
        saving = _calculate_dual_variable_saving(120., 100., 10.)
        assert saving == pytest.approx(-200.)  # 10 * (100-120)

    def test_no_change_zero_saving(self):
        """Residual == baseline → zero saving."""
        saving = _calculate_dual_variable_saving(100., 100., 10.)
        assert saving == pytest.approx(0.)

    def test_zero_shadow_price(self):
        """Zero shadow price → zero saving regardless of energy change."""
        saving = _calculate_dual_variable_saving(50., 100., 0.)
        assert saving == pytest.approx(0.)

    def test_vectorized(self):
        """Works element-wise on arrays."""
        residual = np.array([80., 120., 100.])
        baseline = np.array([100., 100., 100.])
        price = np.array([10., 10., 10.])
        result = _calculate_dual_variable_saving(residual, baseline, price)
        np.testing.assert_array_almost_equal(result, [200., -200., 0.])

    def test_proportional_to_shadow_price(self):
        """Doubling shadow price doubles the saving."""
        s1 = _calculate_dual_variable_saving(80., 100., 5.)
        s2 = _calculate_dual_variable_saving(80., 100., 10.)
        assert s2 == pytest.approx(2. * s1)


# ---------------------------------------------------------------------------
# 6. Optimizer convergence and bound handling
# ---------------------------------------------------------------------------

class TestOptimizerStability:
    """Test minimize_scalar(bounded) with synthetic objectives.

    The speed optimizer uses scipy.optimize.minimize_scalar with
    method='bounded' and xatol=0.1. These tests verify convergence,
    bound respect, and behavior on difficult objective shapes that
    mimic Navigate's freight-cost curve:
        objective(mu) = (fuel_cost(mu) + charter_rate) / cargo_miles(mu)
    """

    XATOL = 0.1

    @staticmethod
    def _optimize(objective: callable,
                  bounds: tuple[float, float]
                  ) -> minimize_scalar:
        """Run the same optimizer call as _optimize_vessel_speed."""
        return minimize_scalar(
            objective,
            bounds=bounds,
            method="bounded",
            options={"xatol": TestOptimizerStability.XATOL},
        )

    # -- Convergence on well-behaved objectives --

    def test_convex_quadratic_converges(self):
        """U-shaped cost curve: optimizer finds the interior minimum."""
        # (mu - 12)^2 + 5  →  minimum at mu=12
        res = self._optimize(lambda mu: (mu - 12.) ** 2 + 5., (6., 20.))
        assert res.success
        assert res.x == pytest.approx(12., abs=self.XATOL)

    def test_convex_freight_cost_shape(self):
        """Realistic shape: fuel ~ mu^3, charter ~ 1/mu.

        objective = (a*mu^3 + c) / mu  has minimum at mu = (c/2a)^(1/3).
        """
        a, c = 0.01, 50.
        expected_min = (c / (2. * a)) ** (1. / 3.)  # ~13.57
        res = self._optimize(lambda mu: (a * mu ** 3 + c) / mu, (5., 25.))
        assert res.success
        assert res.x == pytest.approx(expected_min, abs=self.XATOL)

    def test_steep_cubic_converges(self):
        """Very steep objective doesn't cause overflow or divergence."""
        res = self._optimize(lambda mu: (mu - 10.) ** 4, (5., 15.))
        assert res.success
        assert res.x == pytest.approx(10., abs=self.XATOL)

    # -- Minimum at or near bounds --

    def test_monotone_decreasing_finds_upper_bound(self):
        """Decreasing objective → minimum at upper bound."""
        res = self._optimize(lambda mu: -mu, (6., 20.))
        assert res.success
        assert res.x == pytest.approx(20., abs=self.XATOL)

    def test_monotone_increasing_finds_lower_bound(self):
        """Increasing objective → minimum at lower bound."""
        res = self._optimize(lambda mu: mu, (6., 20.))
        assert res.success
        assert res.x == pytest.approx(6., abs=self.XATOL)

    def test_minimum_outside_bounds_clamps(self):
        """True minimum at mu=3, but bounds=[6,20] → result at lower bound."""
        res = self._optimize(lambda mu: (mu - 3.) ** 2, (6., 20.))
        assert res.success
        assert res.x == pytest.approx(6., abs=self.XATOL)

    # -- Flat and near-flat objectives --

    def test_flat_objective_converges(self):
        """Constant objective → optimizer converges (result is arbitrary)."""
        res = self._optimize(lambda mu: 42., (6., 20.))
        assert res.success
        assert 6. <= res.x <= 20.

    def test_nearly_flat_objective_stays_in_bounds(self):
        """Tiny gradient (1e-8 slope) → result stays within bounds."""
        res = self._optimize(lambda mu: 100. + 1e-8 * mu, (6., 20.))
        assert res.success
        assert 6. - 1e-6 <= res.x <= 20. + 1e-6

    # -- Narrow bounds --

    def test_narrow_bounds_converge(self):
        """Bounds narrower than xatol → still converges to feasible point."""
        res = self._optimize(lambda mu: (mu - 10.) ** 2, (9.99, 10.01))
        assert res.success
        assert 9.99 <= res.x <= 10.01

    def test_zero_width_bounds(self):
        """Degenerate bounds (low == high) → returns that point."""
        res = self._optimize(lambda mu: (mu - 5.) ** 2, (10., 10.))
        assert res.success
        assert res.x == pytest.approx(10., abs=self.XATOL)

    # -- Non-convex objectives (local minima risk) --

    def test_bimodal_objective_finds_a_local_minimum(self):
        """Two local minima — bounded Brent finds one of them.

        This documents the known limitation: minimize_scalar(bounded)
        is not global. The result must still be within bounds and be
        a local minimum (lower than its neighbours).
        """
        def bimodal(mu: float) -> float:
            return -np.exp(-((mu - 8.) ** 2)) - 0.8 * np.exp(-((mu - 16.) ** 2))

        res = self._optimize(bimodal, (5., 20.))
        assert res.success
        assert 5. <= res.x <= 20.
        # Verify it's actually a local minimum (lower than nearby points)
        val = bimodal(res.x)
        eps = 0.2
        assert val <= bimodal(max(5., res.x - eps)) + 1e-6
        assert val <= bimodal(min(20., res.x + eps)) + 1e-6

    # -- Result always within bounds --

    @pytest.mark.parametrize('bounds,center', [
        ((6., 20.), 13.),
        ((0.1, 0.5), 0.3),
        ((100., 200.), 150.),
    ])
    def test_result_within_bounds(self, bounds: tuple[float, float],
                                  center: float):
        """Optimizer result never exceeds the specified bounds."""
        res = self._optimize(lambda mu: (mu - center) ** 2, bounds)
        assert res.x >= bounds[0] - 1e-10
        assert res.x <= bounds[1] + 1e-10


# ---------------------------------------------------------------------------
# 7. End-to-end: mean_to_speeds + update + optimizer pipeline invariants
# ---------------------------------------------------------------------------

class TestSpeedPipelineInvariants:
    """Verify invariants that hold across the speed management pipeline."""

    def test_rate_limit_then_clamp_ordering(self):
        """Rate-limited speed, then clamped to legs, stays within bounds."""
        mu_ref, mu_target, max_change = 14., 20., 1.0
        mu_actual = _update_mean_speed(mu_ref, mu_target, max_change)

        deltas = np.array([-3., 0., 3.])
        speed_min = np.full(3, 10.)
        speed_max = np.full(3, 18.)
        speeds = _mean_to_speeds(mu_actual, deltas, speed_min, speed_max)

        assert np.all(speeds >= speed_min)
        assert np.all(speeds <= speed_max)

    def test_idempotent_when_converged(self):
        """Once target == reference, repeated calls produce no change."""
        mu = 14.
        for _ in range(10):
            mu = _update_mean_speed(mu, 14., 0.5)
        assert mu == pytest.approx(14.)

    def test_monotone_approach_to_target(self):
        """Successive rate-limited steps monotonically approach the target."""
        mu = 10.
        target = 16.
        max_change = 0.5
        previous_gap = abs(target - mu)
        for _ in range(50):
            mu = _update_mean_speed(mu, target, max_change)
            gap = abs(target - mu)
            assert gap <= previous_gap + 1e-10
            previous_gap = gap
        assert mu == pytest.approx(target, abs=1e-10)

    def test_extreme_deltas_fully_clamped(self):
        """Huge deltas are clamped — output equals bounds, not mu+delta."""
        deltas = np.array([-1000., 1000.])
        speed_min = np.array([8., 8.])
        speed_max = np.array([20., 20.])
        speeds = _mean_to_speeds(14., deltas, speed_min, speed_max)
        assert speeds[0] == pytest.approx(8.)
        assert speeds[1] == pytest.approx(20.)
