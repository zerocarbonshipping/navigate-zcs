# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.economics.decision."""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core.enum_ import UtilityID
from navigate.economics.decision import (
    _redistribute_proportional,
    calculate_asset_shares,
    calculate_two_axis_uptake,
    softmax,
)


def test_softmax_is_numerically_stable_for_large_values():
    shares = softmax(np.array([1000.0, 1001.0, 1002.0]))
    assert np.all(np.isfinite(shares))
    assert shares.sum() == pytest.approx(1.0)


@pytest.mark.parametrize("utility", list(UtilityID))
def test_unit_odds_give_uniform_shares(utility):
    # an odds ratio of 1 calibrates the sensitivity to zero, whatever the metric
    shares, _ = calculate_asset_shares(
        [10.0, 20.0, 30.0], utility, 1.0, reference=100.0
    )
    np.testing.assert_array_almost_equal(shares, [1.0 / 3, 1.0 / 3, 1.0 / 3])


class TestLowerLogRatio:
    def test_ten_percent_higher_halves_odds(self):
        # the option 10% higher should get half the odds of the cheapest
        shares, msg = calculate_asset_shares(
            [10.0, 11.0], UtilityID.LOWER_LOG_RATIO, 0.5
        )
        np.testing.assert_array_almost_equal(shares, [2.0 / 3, 1.0 / 3])
        assert msg == ""

    @pytest.mark.parametrize(
        ("values", "expected"),
        [
            pytest.param([0.0, 0.0, 3.0], [0.5, 0.5, 0.0], id="zero"),
            pytest.param([-1.0, 5.0, 3.0], [1.0, 0.0, 0.0], id="negative"),
        ],
    )
    def test_nonpositive_falls_back_to_uniform_at_min(self, values, expected):
        shares, msg = calculate_asset_shares(values, UtilityID.LOWER_LOG_RATIO, 0.5)
        np.testing.assert_array_almost_equal(shares, expected)
        assert "non-positive" in msg


class TestHigherLogRatio:
    def test_ten_percent_higher_doubles_odds(self):
        shares, msg = calculate_asset_shares(
            [10.0, 11.0], UtilityID.HIGHER_LOG_RATIO, 2.0
        )
        np.testing.assert_array_almost_equal(shares, [1.0 / 3, 2.0 / 3])
        assert msg == ""

    @pytest.mark.parametrize(
        ("values", "expected"),
        [
            # the positive options share as if the zero were absent: 11 is 10%
            # above 10, so it gets double the odds
            pytest.param([0.0, 11.0, 10.0], [0.0, 2.0 / 3, 1.0 / 3], id="one_zero"),
            pytest.param([0.0, 0.0, 0.0], [0.0, 0.0, 0.0], id="all_zero"),
        ],
    )
    def test_zero_demand_gets_zero_share(self, values, expected):
        shares, _ = calculate_asset_shares(values, UtilityID.HIGHER_LOG_RATIO, 2.0)
        np.testing.assert_array_almost_equal(shares, expected)


class TestSignedReference:
    def test_advantage_of_five_percent_doubles_odds(self):
        # NPV advantage of 5 against a reference of 100 (i.e. 5%) should double the odds
        shares, msg = calculate_asset_shares(
            [0.0, 5.0], UtilityID.SIGNED_REFERENCE, 2.0, reference=100.0
        )
        np.testing.assert_array_almost_equal(shares, [1.0 / 3, 2.0 / 3])
        assert msg == ""

    @pytest.mark.parametrize("reference", [0.0, None], ids=["zero", "missing"])
    def test_nonpositive_reference_falls_back_to_uniform(self, reference):
        shares, msg = calculate_asset_shares(
            [1.0, 2.0, 3.0], UtilityID.SIGNED_REFERENCE, 2.0, reference=reference
        )
        np.testing.assert_array_almost_equal(shares, [1.0 / 3, 1.0 / 3, 1.0 / 3])
        assert "reference" in msg


class TestRedistributeProportional:
    def test_user_example(self):
        shares = np.array([0.5, 0.1, 0.3, 0.1])  # sums to 1
        limits = np.array([0.2, 1.0, 1.0, 1.0])
        result = _redistribute_proportional(shares, limits)
        # surplus 0.3 spread across [0.1, 0.3, 0.1] proportionally
        # → factor 0.8/0.5 = 1.6
        np.testing.assert_array_almost_equal(result, [0.2, 0.16, 0.48, 0.16])
        assert result.sum() == pytest.approx(1.0)

    def test_cascading_saturation(self):
        shares = np.array([0.5, 0.4, 0.1])
        limits = np.array([0.3, 0.3, 1.0])
        result = _redistribute_proportional(shares, limits)
        np.testing.assert_array_almost_equal(result, [0.3, 0.3, 0.4])


@pytest.mark.parametrize(
    ("limits", "expected", "warning"),
    [
        # uniform start [1/3]*3, index 0 capped at 0.2, surplus rescaled
        # across the rest
        pytest.param([0.2, 1.0, 1.0], [0.2, 0.4, 0.4], "", id="feasible"),
        # the limits sum below one, so every option saturates
        pytest.param([0.2, 0.2, 0.2], [0.2, 0.2, 0.2], "infeasible", id="infeasible"),
    ],
)
def test_limits_cap_asset_shares(limits, expected, warning):
    shares, msg = calculate_asset_shares(
        [10.0, 20.0, 30.0], UtilityID.LOWER_LOG_RATIO, 1.0, limits=limits
    )
    np.testing.assert_array_almost_equal(shares, expected)
    assert warning in msg
    assert bool(msg) == bool(warning)


def test_two_axis_limits_compose_to_per_asset_bound():
    # equal metrics and odds of 1 give uniform shares, so every binding limit
    # saturates: group 'a' caps at 0.2 + 0.3 and its members at exactly their
    # per-asset bounds
    uptake = calculate_two_axis_uptake(
        ["a", "a", "b"],
        [100.0, 100.0, 100.0],
        [100.0, 100.0, 100.0],
        intra_utility=UtilityID.LOWER_LOG_RATIO,
        inter_utility=UtilityID.LOWER_LOG_RATIO,
        intra_odds=1.0,
        inter_odds=1.0,
        limits=np.array([0.2, 0.3, 1.0]),
    )
    np.testing.assert_array_almost_equal(uptake, [0.2, 0.3, 0.5])
