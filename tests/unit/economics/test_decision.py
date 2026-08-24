# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.economics.decision."""
import numpy as np
import pytest

from navigate.core.enum_ import UtilityID
from navigate.economics.decision import (
    _apply_limits,
    _beta_from_odds,
    _redistribute_proportional,
    calculate_asset_shares,
    calculate_two_axis_uptake,
    softmax,
)


class TestSoftmax:

    def test_sums_to_one(self):
        shares = softmax(np.array([1., 2., 3.]))
        assert shares.sum() == pytest.approx(1.0)
        assert shares[2] > shares[1] > shares[0]

    def test_numerically_stable_for_large_values(self):
        shares = softmax(np.array([1000., 1001., 1002.]))
        assert np.all(np.isfinite(shares))
        assert shares.sum() == pytest.approx(1.0)

    def test_equal_utilities_uniform(self):
        shares = softmax(np.zeros(4))
        np.testing.assert_array_almost_equal(shares, [0.25, 0.25, 0.25, 0.25])


class TestBetaFromOdds:

    def test_lower_log_ratio(self):
        # a 10% higher metric should halve the odds
        beta = _beta_from_odds(0.5, UtilityID.LOWER_LOG_RATIO)
        assert beta == pytest.approx(-np.log(0.5) / np.log(1.1))
        assert beta > 0.

    def test_higher_log_ratio(self):
        beta = _beta_from_odds(2.0, UtilityID.HIGHER_LOG_RATIO)
        assert beta == pytest.approx(np.log(2.0) / np.log(1.1))
        assert beta > 0.

    def test_signed_reference(self):
        beta = _beta_from_odds(2.0, UtilityID.SIGNED_REFERENCE)
        assert beta == pytest.approx(np.log(2.0) / 0.05)

    def test_unit_odds_gives_zero_beta(self):
        for utility in UtilityID:
            assert _beta_from_odds(1.0, utility) == pytest.approx(0.0)


class TestLowerLogRatio:

    def test_ten_percent_higher_halves_odds(self):
        # the option 10% higher should get half the odds of the cheapest
        shares, msg = calculate_asset_shares([10., 11.], UtilityID.LOWER_LOG_RATIO, 0.5)
        np.testing.assert_array_almost_equal(shares, [2. / 3, 1. / 3])
        assert shares[1] / shares[0] == pytest.approx(0.5)
        assert msg == ''

    def test_unit_odds_uniform(self):
        shares, _ = calculate_asset_shares([10., 20., 30.], UtilityID.LOWER_LOG_RATIO, 1.0)
        np.testing.assert_array_almost_equal(shares, [1. / 3, 1. / 3, 1. / 3])

    def test_nonpositive_falls_back_to_uniform_at_min(self):
        shares, msg = calculate_asset_shares([0., 0., 3.], UtilityID.LOWER_LOG_RATIO, 0.5)
        np.testing.assert_array_almost_equal(shares, [0.5, 0.5, 0.])
        assert 'non-positive' in msg

    def test_negative_value_falls_back(self):
        shares, msg = calculate_asset_shares([-1., 5., 3.], UtilityID.LOWER_LOG_RATIO, 0.5)
        np.testing.assert_array_almost_equal(shares, [1., 0., 0.])
        assert msg != ''


class TestHigherLogRatio:

    def test_ten_percent_higher_doubles_odds(self):
        shares, msg = calculate_asset_shares([10., 11.], UtilityID.HIGHER_LOG_RATIO, 2.0)
        np.testing.assert_array_almost_equal(shares, [1. / 3, 2. / 3])
        assert shares[1] / shares[0] == pytest.approx(2.0)
        assert msg == ''

    def test_zero_demand_gets_zero_share(self):
        shares, _ = calculate_asset_shares([0., 10., 5.], UtilityID.HIGHER_LOG_RATIO, 2.0)
        assert shares[0] == 0.
        assert shares.sum() == pytest.approx(1.0)

    def test_all_zero_demand_returns_zeros(self):
        shares, _ = calculate_asset_shares([0., 0., 0.], UtilityID.HIGHER_LOG_RATIO, 2.0)
        np.testing.assert_array_almost_equal(shares, [0., 0., 0.])


class TestSignedReference:

    def test_advantage_of_five_percent_doubles_odds(self):
        # NPV advantage of 5 against a reference of 100 (i.e. 5%) should double the odds
        shares, msg = calculate_asset_shares([0., 5.], UtilityID.SIGNED_REFERENCE, 2.0, reference=100.)
        np.testing.assert_array_almost_equal(shares, [1. / 3, 2. / 3])
        assert shares[1] / shares[0] == pytest.approx(2.0)
        assert msg == ''

    def test_handles_negative_npv(self):
        shares, _ = calculate_asset_shares([-10., 0., 10.], UtilityID.SIGNED_REFERENCE, 2.0, reference=100.)
        assert shares[2] > shares[1] > shares[0]
        assert shares.sum() == pytest.approx(1.0)

    def test_nonpositive_reference_falls_back_to_uniform(self):
        shares, msg = calculate_asset_shares([1., 2., 3.], UtilityID.SIGNED_REFERENCE, 2.0, reference=0.)
        np.testing.assert_array_almost_equal(shares, [1. / 3, 1. / 3, 1. / 3])
        assert 'reference' in msg

    def test_missing_reference_falls_back_to_uniform(self):
        shares, msg = calculate_asset_shares([1., 2.], UtilityID.SIGNED_REFERENCE, 2.0)
        np.testing.assert_array_almost_equal(shares, [0.5, 0.5])
        assert msg != ''


class TestRedistributeProportional:

    def test_user_example(self):
        shares = np.array([0.5, 0.1, 0.3, 0.1])  # sums to 1
        limits = np.array([0.2, 1., 1., 1.])
        result = _redistribute_proportional(shares, limits)
        # surplus 0.3 spread across [0.1, 0.3, 0.1] proportionally → factor 0.8/0.5 = 1.6
        np.testing.assert_array_almost_equal(result, [0.2, 0.16, 0.48, 0.16])
        assert result.sum() == pytest.approx(1.0)

    def test_all_within_limits_unchanged(self):
        shares = np.array([0.4, 0.3, 0.3])
        limits = np.array([0.5, 0.5, 0.5])
        result = _redistribute_proportional(shares, limits)
        np.testing.assert_array_almost_equal(result, shares)

    def test_cascading_saturation(self):
        shares = np.array([0.5, 0.4, 0.1])
        limits = np.array([0.3, 0.3, 1.])
        result = _redistribute_proportional(shares, limits)
        np.testing.assert_array_almost_equal(result, [0.3, 0.3, 0.4])

    def test_zero_limit_zeros_option(self):
        shares = np.array([0.5, 0.3, 0.2])
        limits = np.array([0., 1., 1.])
        result = _redistribute_proportional(shares, limits)
        np.testing.assert_array_almost_equal(result, [0., 0.6, 0.4])
        assert result.sum() == pytest.approx(1.0)


class TestApplyLimits:

    def test_limits_enforced_via_calculate_asset_shares(self):
        shares, msg = calculate_asset_shares(
            [10., 20., 30.], UtilityID.LOWER_LOG_RATIO, 1.0, limits=[0.2, 1., 1.],
        )
        # uniform start [1/3]*3, index 0 capped at 0.2, surplus rescaled across the rest
        np.testing.assert_array_almost_equal(shares, [0.2, 0.4, 0.4])
        assert msg == ''

    def test_limits_none_passthrough(self):
        shares, msg = calculate_asset_shares([10., 11.], UtilityID.LOWER_LOG_RATIO, 0.5, limits=None)
        np.testing.assert_array_almost_equal(shares, [2. / 3, 1. / 3])
        assert msg == ''

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            _apply_limits(np.array([0.5, 0.5]), [0.5, 0.5, 0.5])

    def test_infeasible_returns_saturated_with_warning(self):
        shares, msg = calculate_asset_shares(
            [10., 20., 30.], UtilityID.LOWER_LOG_RATIO, 0.5, limits=[0.2, 0.2, 0.2],
        )
        np.testing.assert_array_almost_equal(shares, [0.2, 0.2, 0.2])
        assert 'infeasible' in msg


class TestTwoAxisUptake:

    def test_grouped_shares_sum_to_one(self):
        # two fuel pathways: 'a' (two plants), 'b' (one plant)
        group_keys = ['a', 'a', 'b']
        metrics_intra = [100., 110., 100.]   # LCoF, lower is better
        metrics_inter = [50., 50., 80.]      # expected demand, higher is better
        uptake = calculate_two_axis_uptake(
            group_keys, metrics_intra, metrics_inter,
            intra_utility=UtilityID.LOWER_LOG_RATIO,
            inter_utility=UtilityID.HIGHER_LOG_RATIO,
            intra_odds=0.5, inter_odds=1.25,
        )
        assert uptake.sum() == pytest.approx(1.0)
        # within pathway 'a', the cheaper plant (index 0) gets more share
        assert uptake[0] > uptake[1]

    def test_single_group(self):
        uptake = calculate_two_axis_uptake(
            ['a', 'a'], [100., 200.], [10., 10.],
            intra_utility=UtilityID.LOWER_LOG_RATIO,
            inter_utility=UtilityID.HIGHER_LOG_RATIO,
            intra_odds=0.5, inter_odds=1.25,
        )
        assert uptake.sum() == pytest.approx(1.0)
        assert uptake[0] > uptake[1]
