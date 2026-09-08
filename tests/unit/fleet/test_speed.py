# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Mathematical coherence tests for the speed management pipeline.

Tests verify the correctness of:
  - Mean-to-speeds conversion with clamping (_mean_to_speeds)
  - Rate-limited speed updates (_update_mean_speed)
  - Feasible speed bounds (calculate_speed_bounds)
  - Dual-variable saving formula (_calculate_dual_variable_saving)
"""
import numpy as np
import pytest

from navigate.fleet.marginal_saving import _calculate_dual_variable_saving
from navigate.fleet.power import calculate_speed_bounds
from navigate.fleet.speed import _mean_to_speeds, _update_mean_speed

# ---------------------------------------------------------------------------
# 1. Mean-to-speeds conversion
# ---------------------------------------------------------------------------


class TestMeanToSpeeds:
    """Verify: speeds = clip(mu + deltas, speed_min, speed_max)."""

    @pytest.mark.parametrize('mu, deltas, speed_min, speed_max, expected', [
        # within bounds: output = mu + deltas
        (15., [-2., 0., 2.], [0., 0., 0.], [30., 30., 30.], [13., 15., 17.]),
        # below minimum clamped up: 10 - 5 = 5 → 8
        (10., [-5., 0., 5.], [8., 8., 8.], [30., 30., 30.], [8., 10., 15.]),
        # above maximum clamped down: 19 + 2 = 21 → 20
        (19., [-2., 0., 2.], [0., 0., 0.], [20., 20., 20.], [17., 19., 20.]),
        # per-leg bounds: the second leg's minimum (12) exceeds mu
        (10., [0., 0.], [8., 12.], [20., 16.], [10., 12.]),
        # huge deltas fully clamped to the bounds
        (14., [-1000., 1000.], [8., 8.], [20., 20.], [8., 20.]),
    ])
    def test_clipped_speeds(self, mu, deltas, speed_min, speed_max, expected):
        result = _mean_to_speeds(mu, np.array(deltas), np.array(speed_min), np.array(speed_max))
        np.testing.assert_array_almost_equal(result, expected)


# ---------------------------------------------------------------------------
# 2. Rate-limited speed update
# ---------------------------------------------------------------------------

class TestUpdateMeanSpeed:
    """Verify: mu_actual = mu_ref + clip(mu_target - mu_ref, -max, +max)."""

    @pytest.mark.parametrize('mu_ref, mu_target, max_change, expected', [
        (14., 14., 0.5, 14.),
        (14., 14.3, 0.5, 14.3),
        (14., 10., 0.5, 13.5),
        (14., 20., 0.5, 14.5),
        (14., 5., np.inf, 5.),
        (14., 25., np.inf, 25.),
        # zero max_change → speed cannot change at all
        (14., 20., 0., 14.),
    ])
    def test_rate_limited(self, mu_ref, mu_target, max_change, expected):
        assert _update_mean_speed(mu_ref, mu_target, max_change) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# 3. Feasible speed bounds
# ---------------------------------------------------------------------------

class TestSpeedBounds:
    """Verify calculate_speed_bounds returns (min(speed_min), max(speed_max)) with fallbacks."""

    @pytest.mark.parametrize('speed_min, speed_max, speeds, expected', [
        ([6., 7., 8.], [18., 20., 19.], [12., 14., 16.], (6., 20.)),
        ([8., 8.], [20., 20.], [12., 14.], (8., 20.)),
        # non-finite bounds fall back to the reference speed envelope
        ([-np.inf, -np.inf], [np.inf, np.inf], [10., 18.], (10., 18.)),
        # low >= high falls back to the reference speed envelope
        ([15., 15.], [15., 15.], [10., 20.], (10., 20.)),
    ])
    def test_bounds(self, speed_min, speed_max, speeds, expected):
        low, high = calculate_speed_bounds(np.array(speed_min), np.array(speed_max), np.array(speeds))
        assert (low, high) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# 4. Dual-variable saving formula
# ---------------------------------------------------------------------------

class TestDualVariableSaving:
    """Verify: saving = shadow_price * (baseline - residual)."""

    @pytest.mark.parametrize('residual, baseline, price, expected', [
        (80., 100., 10., 200.),
        (120., 100., 10., -200.),
        (100., 100., 10., 0.),
        # zero shadow price → zero saving regardless of energy change
        (50., 100., 0., 0.),
    ])
    def test_saving(self, residual, baseline, price, expected):
        assert _calculate_dual_variable_saving(residual, baseline, price) == pytest.approx(expected)

    def test_vectorized(self):
        """Works element-wise on arrays."""
        residual = np.array([80., 120., 100.])
        baseline = np.array([100., 100., 100.])
        price = np.array([10., 10., 10.])
        result = _calculate_dual_variable_saving(residual, baseline, price)
        np.testing.assert_array_almost_equal(result, [200., -200., 0.])
