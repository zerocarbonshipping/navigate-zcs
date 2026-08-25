# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.util.numeric — inertia and compound growth calculations."""
import numpy as np
import pytest

from navigate.util import YEAR, calculate_compound_growth, calculate_inertia


class TestCalculateInertia:

    def test_one_year_step_returns_inertia(self):
        """For a time-step of exactly one year, result should equal the inertia parameter."""
        assert calculate_inertia(0.8, YEAR) == pytest.approx(0.8)

    def test_zero_step_returns_one(self):
        """For dt=0, inertia^0 = 1.0 regardless of base."""
        assert calculate_inertia(0.5, 0.0) == pytest.approx(1.0)

    def test_half_year_step(self):
        """For half-year step, result should be sqrt(inertia)."""
        result = calculate_inertia(0.64, YEAR / 2)
        assert result == pytest.approx(0.8)

    def test_inertia_one_always_one(self):
        """Inertia of 1.0 remains 1.0 regardless of time-step."""
        assert calculate_inertia(1.0, YEAR) == pytest.approx(1.0)
        assert calculate_inertia(1.0, 100.0) == pytest.approx(1.0)

    def test_inertia_zero_always_zero(self):
        """Inertia of 0.0 is 0.0 for any positive time-step."""
        assert calculate_inertia(0.0, YEAR) == pytest.approx(0.0)


class TestCalculateCompoundGrowth:

    def test_zero_growth(self):
        """With zero growth, all values should equal the initial value."""
        timeline = np.array([0.0, YEAR, 2 * YEAR])
        growth = np.array([0.0, 0.0, 0.0])
        result = calculate_compound_growth(100.0, growth, timeline)
        np.testing.assert_allclose(result, [100.0, 100.0, 100.0])

    def test_constant_growth(self):
        """With constant growth rate, verify exponential increase."""
        timeline = np.array([0.0, YEAR, 2 * YEAR])
        rate = 0.05  # 5% per year
        growth = np.array([rate, rate, rate])
        result = calculate_compound_growth(100.0, growth, timeline)

        # After one year: 100 * exp(ln(1.05) * 1) = 100 * 1.05 = 105
        assert result[0] == pytest.approx(100.0)
        assert result[1] == pytest.approx(105.0, rel=1e-6)
        # After two years: 100 * exp(2 * ln(1.05)) = 100 * 1.05^2
        assert result[2] == pytest.approx(100.0 * 1.05 ** 2, rel=1e-6)

    def test_single_step(self):
        """Minimal timeline with just two points."""
        timeline = np.array([0.0, YEAR])
        growth = np.array([0.10, 0.10])
        result = calculate_compound_growth(50.0, growth, timeline)
        assert result[0] == pytest.approx(50.0)
        assert result[1] == pytest.approx(55.0, rel=1e-6)

    def test_result_shape_matches_timeline(self):
        timeline = np.array([0.0, YEAR, 2 * YEAR, 3 * YEAR])
        growth = np.zeros(4)
        result = calculate_compound_growth(1.0, growth, timeline)
        assert result.shape == timeline.shape
