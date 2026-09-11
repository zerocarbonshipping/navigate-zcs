# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Mathematical coherence tests for the speed management pipeline.

Tests verify the correctness of:
  - Mean-to-speeds conversion with clamping (_mean_to_speeds)
  - Rate-limited speed updates (_update_mean_speed)
  - Feasible speed bounds (calculate_speed_bounds)
  - Dual-variable saving formula (_calculate_dual_variable_saving)
"""

from __future__ import annotations

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

    @pytest.mark.parametrize(
        "mu, deltas, speed_min, speed_max, expected",
        [
            # within bounds: output = mu + deltas
            (
                15.0,
                [-2.0, 0.0, 2.0],
                [0.0, 0.0, 0.0],
                [30.0, 30.0, 30.0],
                [13.0, 15.0, 17.0],
            ),
            # below minimum clamped up: 10 - 5 = 5 → 8
            (
                10.0,
                [-5.0, 0.0, 5.0],
                [8.0, 8.0, 8.0],
                [30.0, 30.0, 30.0],
                [8.0, 10.0, 15.0],
            ),
            # above maximum clamped down: 19 + 2 = 21 → 20
            (
                19.0,
                [-2.0, 0.0, 2.0],
                [0.0, 0.0, 0.0],
                [20.0, 20.0, 20.0],
                [17.0, 19.0, 20.0],
            ),
            # per-leg bounds: the second leg's minimum (12) exceeds mu
            (10.0, [0.0, 0.0], [8.0, 12.0], [20.0, 16.0], [10.0, 12.0]),
            # huge deltas fully clamped to the bounds
            (14.0, [-1000.0, 1000.0], [8.0, 8.0], [20.0, 20.0], [8.0, 20.0]),
        ],
    )
    def test_clipped_speeds(self, mu, deltas, speed_min, speed_max, expected):
        result = _mean_to_speeds(
            mu, np.array(deltas), np.array(speed_min), np.array(speed_max)
        )
        np.testing.assert_array_almost_equal(result, expected)


# ---------------------------------------------------------------------------
# 2. Rate-limited speed update
# ---------------------------------------------------------------------------


class TestUpdateMeanSpeed:
    """Verify: mu_actual = mu_ref + clip(mu_target - mu_ref, -max, +max)."""

    @pytest.mark.parametrize(
        "mu_ref, mu_target, max_change, expected",
        [
            (14.0, 14.0, 0.5, 14.0),
            (14.0, 14.3, 0.5, 14.3),
            (14.0, 10.0, 0.5, 13.5),
            (14.0, 20.0, 0.5, 14.5),
            (14.0, 5.0, np.inf, 5.0),
            (14.0, 25.0, np.inf, 25.0),
            # zero max_change → speed cannot change at all
            (14.0, 20.0, 0.0, 14.0),
        ],
    )
    def test_rate_limited(self, mu_ref, mu_target, max_change, expected):
        assert _update_mean_speed(mu_ref, mu_target, max_change) == pytest.approx(
            expected
        )


# ---------------------------------------------------------------------------
# 3. Feasible speed bounds
# ---------------------------------------------------------------------------


class TestSpeedBounds:
    """Verify calculate_speed_bounds returns (min(speed_min), max(speed_max)) with fallbacks."""

    @pytest.mark.parametrize(
        "speed_min, speed_max, speeds, expected",
        [
            ([6.0, 7.0, 8.0], [18.0, 20.0, 19.0], [12.0, 14.0, 16.0], (6.0, 20.0)),
            ([8.0, 8.0], [20.0, 20.0], [12.0, 14.0], (8.0, 20.0)),
            # non-finite bounds fall back to the reference speed envelope
            ([-np.inf, -np.inf], [np.inf, np.inf], [10.0, 18.0], (10.0, 18.0)),
            # low >= high falls back to the reference speed envelope
            ([15.0, 15.0], [15.0, 15.0], [10.0, 20.0], (10.0, 20.0)),
        ],
    )
    def test_bounds(self, speed_min, speed_max, speeds, expected):
        low, high = calculate_speed_bounds(
            np.array(speed_min), np.array(speed_max), np.array(speeds)
        )
        assert (low, high) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# 4. Dual-variable saving formula
# ---------------------------------------------------------------------------


class TestDualVariableSaving:
    """Verify: saving = shadow_price * (baseline - residual)."""

    @pytest.mark.parametrize(
        "residual, baseline, price, expected",
        [
            (80.0, 100.0, 10.0, 200.0),
            (120.0, 100.0, 10.0, -200.0),
            (100.0, 100.0, 10.0, 0.0),
            # zero shadow price → zero saving regardless of energy change
            (50.0, 100.0, 0.0, 0.0),
        ],
    )
    def test_saving(self, residual, baseline, price, expected):
        assert _calculate_dual_variable_saving(
            residual, baseline, price
        ) == pytest.approx(expected)

    def test_vectorized(self):
        """Works element-wise on arrays."""
        residual = np.array([80.0, 120.0, 100.0])
        baseline = np.array([100.0, 100.0, 100.0])
        price = np.array([10.0, 10.0, 10.0])
        result = _calculate_dual_variable_saving(residual, baseline, price)
        np.testing.assert_array_almost_equal(result, [200.0, -200.0, 0.0])
