# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.util.numeric — lookup, growth, inertia, belief smoothing."""

from __future__ import annotations

import numpy as np
import pytest

from navigate.util import (
    YEAR,
    calculate_compound_growth,
    calculate_inertia,
    derive_smoothing_alpha,
    find_nearest,
    find_nearest_index,
    get_increment_origin_index,
    get_increment_origin_indexes,
    interpolate_yearly_flow,
    update_belief_path,
)


class TestCalculateInertia:
    @pytest.mark.parametrize(
        ("inertia", "dt", "expected"),
        [
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
        ],
    )
    def test_inertia(self, inertia, dt, expected):
        assert calculate_inertia(inertia, dt) == pytest.approx(expected)


class TestFindNearest:
    _array = np.array([0.0, 10.0, 20.0])

    def test_scalar_query(self):
        assert find_nearest_index(self._array, 9.0) == 1

    def test_array_query(self):
        result = find_nearest(self._array, np.array([-5.0, 9.0, 25.0]))
        np.testing.assert_array_equal(result, [0, 1, 2])

    def test_below_first_clamps_to_zero(self):
        assert find_nearest_index(self._array, -100.0) == 0

    def test_past_last_clamps_to_last(self):
        assert find_nearest_index(self._array, 100.0) == 2

    def test_equidistant_tie_picks_right_neighbor(self):
        assert find_nearest_index(self._array, 5.0) == 1

    # query kinds the pre-unification scalar/array branch crashed on
    def test_int_query(self):
        assert find_nearest_index(self._array, 9) == 1

    def test_float32_query(self):
        assert find_nearest_index(self._array, np.float32(9.0)) == 1

    def test_zero_dimensional_query(self):
        assert find_nearest_index(self._array, np.array(9.0)) == 1


class TestGetIncrementOriginIndex:
    _years = np.array([2020.0, 2021.0, 2022.0])

    def test_scalar_age(self):
        assert get_increment_origin_index(self._years, 2022.0, 1.2) == 1

    def test_array_ages_clamp_to_start(self):
        origins = get_increment_origin_indexes(
            self._years, 2022.0, np.array([0.0, 1.0, 5.0])
        )
        np.testing.assert_array_equal(origins, [2, 1, 0])


class TestInterpolateYearlyFlow:
    _flow = np.array([100.0, 80.0, 60.0])

    def test_exact_year_hit(self):
        assert interpolate_yearly_flow(self._flow, 1.0) == pytest.approx(80.0)

    def test_interior_fractional_age(self):
        assert interpolate_yearly_flow(self._flow, 0.5) == pytest.approx(90.0)

    def test_age_zero(self):
        assert interpolate_yearly_flow(self._flow, 0.0) == pytest.approx(100.0)

    def test_age_beyond_last_year_clamps(self):
        assert interpolate_yearly_flow(self._flow, 10.0) == pytest.approx(60.0)


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
        assert result[2] == pytest.approx(100.0 * 1.05**2, rel=1e-6)


class TestUpdateBeliefPath:
    # 0.25 and every expected value below are exact in binary floating point,
    # so the paths compare exactly
    _alpha = 0.25

    def test_never_updated_belief_adopts_raw(self):
        belief = np.full(4, np.nan)
        update_belief_path(np.array([1.0, 2.0, 3.0, 4.0]), belief, self._alpha, 0)
        np.testing.assert_array_equal(belief, [1.0, 2.0, 3.0, 4.0])

    def test_zero_prior_is_smoothed_not_readopted(self):
        # a prior of exactly zero is evidence, so the onset ramps as alpha * raw:
        # 0.25 * 8 = 2, 0.25 * 4 = 1, 0.25 * 12 = 3
        belief = np.array([5.0, 0.0, 0.0, 0.0])
        update_belief_path(np.array([9.0, 8.0, 4.0, 12.0]), belief, self._alpha, 1)
        np.testing.assert_array_equal(belief, [5.0, 2.0, 1.0, 3.0])

    def test_nonzero_prior_is_smoothed(self):
        # 0.25 * 8 + 0.75 * 4 = 5, 0.25 * 0 + 0.75 * 8 = 6, 0.25 * 4 + 0.75 * 12 = 10
        belief = np.array([7.0, 4.0, 8.0, 12.0])
        update_belief_path(np.array([100.0, 8.0, 0.0, 4.0]), belief, self._alpha, 1)
        np.testing.assert_array_equal(belief, [7.0, 5.0, 6.0, 10.0])

    def test_entries_before_idx_are_untouched(self):
        # neither a NaN nor a value before idx is written, whatever raw holds there
        belief = np.array([np.nan, 3.0, np.nan, np.nan])
        update_belief_path(np.array([1.0, 1.0, 6.0, 7.0]), belief, self._alpha, 2)
        np.testing.assert_array_equal(belief, [np.nan, 3.0, 6.0, 7.0])

    def test_onset_after_all_zero_update_ramps(self):
        # first update: the price does not bind, belief becomes all zero; second
        # update: the price binds at 4, belief moves to 0.25 * 4 = 1
        belief = np.full(3, np.nan)
        update_belief_path(np.zeros(3), belief, self._alpha, 0)
        update_belief_path(np.array([0.0, 4.0, 4.0]), belief, self._alpha, 1)
        np.testing.assert_array_equal(belief, [0.0, 1.0, 1.0])

    def test_partially_nan_forward_slice_bootstraps_per_entry(self):
        # the documented rule: a NaN entry adopts raw, the other is smoothed,
        # 0.25 * 8 + 0.75 * 4 = 5
        belief = np.array([4.0, np.nan])
        update_belief_path(np.array([8.0, 8.0]), belief, self._alpha, 0)
        np.testing.assert_array_equal(belief, [5.0, 8.0])


class TestDeriveSmoothingAlpha:
    @pytest.mark.parametrize(
        ("timeline", "idx", "horizon", "expected"),
        [
            # docstring: 5-year horizon, 1-year steps → 1 / (1 + 5 / 1)
            (np.array([0.0, YEAR, 2 * YEAR]), 1, 5.0, 1.0 / 6.0),
            # docstring: 3-year horizon, 1-year steps → 1 / (1 + 3 / 1)
            (np.array([0.0, YEAR, 2 * YEAR]), 1, 3.0, 0.25),
            # 2-year horizon, half-year step → 1 / (1 + 2 / 0.5)
            (np.array([0.0, YEAR / 2, YEAR]), 1, 2.0, 0.2),
            # 3-year horizon, 2-year step → 1 / (1 + 3 / 2)
            (np.array([0.0, 2 * YEAR, 4 * YEAR]), 2, 3.0, 0.4),
            # zero horizon trusts the projection fully
            (np.array([0.0, YEAR, 2 * YEAR]), 1, 0.0, 1.0),
            # a zero-length step has no history to weigh against
            (np.array([0.0, YEAR, YEAR]), 2, 3.0, 1.0),
            # an index past the timeline trusts the projection fully
            (np.array([0.0, YEAR, 2 * YEAR]), 3, 3.0, 1.0),
        ],
    )
    def test_alpha(self, timeline, idx, horizon, expected):
        assert derive_smoothing_alpha(idx, horizon, timeline) == pytest.approx(expected)
