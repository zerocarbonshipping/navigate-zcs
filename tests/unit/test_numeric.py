# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.util.numeric — inertia and compound growth calculations."""
import numpy as np
import pytest

from navigate.util import YEAR, calculate_compound_growth, calculate_inertia


class TestCalculateInertia:

    @pytest.mark.parametrize('inertia, dt, expected', [
        # for a time-step of exactly one year, result equals the inertia parameter
        (0.8, YEAR, 0.8),
        # dt=0 → inertia^0 = 1.0 regardless of base
        (0.5, 0.0, 1.0),
        # half-year step → sqrt(inertia)
        (0.64, YEAR / 2, 0.8),
        # inertia of 1.0 remains 1.0 regardless of time-step
        (1.0, YEAR, 1.0),
        (1.0, 100.0, 1.0),
        # inertia of 0.0 is 0.0 for any positive time-step
        (0.0, YEAR, 0.0),
    ])
    def test_inertia(self, inertia, dt, expected):
        assert calculate_inertia(inertia, dt) == pytest.approx(expected)


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
