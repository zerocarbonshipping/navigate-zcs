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
    update_belief_path,
)

# compound growth goes through exp(log(1 + r)), which round-trips only to
# within float rounding of the hand-computed powers
GROWTH_RTOL = 1e-6


def test_inertia_compounds_over_the_time_step():
    # the inertia parameter is per year, so a half-year step takes its root
    assert calculate_inertia(0.64, YEAR / 2) == pytest.approx(0.8)


class TestFindNearest:
    _array = np.array([0.0, 10.0, 20.0])

    def test_queries_beyond_the_ends_clamp(self):
        result = find_nearest(self._array, np.array([-100.0, 9.0, 100.0]))
        np.testing.assert_array_equal(result, [0, 1, 2])

    def test_equidistant_tie_picks_right_neighbor(self):
        assert find_nearest_index(self._array, 5.0) == 1


class TestCalculateCompoundGrowth:
    def test_constant_growth(self):
        timeline = np.array([0.0, YEAR, 2 * YEAR])
        rate = 0.05  # 5% per year
        growth = np.array([rate, rate, rate])
        result = calculate_compound_growth(100.0, growth, timeline)

        # After one year: 100 * exp(ln(1.05) * 1) = 100 * 1.05 = 105
        assert result[0] == pytest.approx(100.0)
        assert result[1] == pytest.approx(105.0, rel=GROWTH_RTOL)
        # After two years: 100 * exp(2 * ln(1.05)) = 100 * 1.05^2
        assert result[2] == pytest.approx(100.0 * 1.05**2, rel=GROWTH_RTOL)

    def test_growth_at_a_step_applies_over_the_step_that_follows(self):
        # the growth at index t compounds over t -> t+1 for that step's length,
        # so the last entry is never applied: 100 * 1.1 over the first year,
        # then * 1.2 ** 2 over the two-year step. Applying the growth at t+1
        # instead would give 120 and 270
        timeline = np.array([0.0, YEAR, 3 * YEAR])
        growth = np.array([0.1, 0.2, 0.5])

        result = calculate_compound_growth(100.0, growth, timeline)

        np.testing.assert_allclose(
            result, [100.0, 110.0, 110.0 * 1.2**2], rtol=GROWTH_RTOL
        )


class TestUpdateBeliefPath:
    # 0.25 and every expected value below are exact in binary floating point,
    # so the paths compare exactly
    _alpha = 0.25

    def test_never_updated_belief_adopts_raw(self):
        belief = np.full(4, np.nan)
        update_belief_path(np.array([1.0, 2.0, 3.0, 4.0]), belief, self._alpha, 0)
        np.testing.assert_array_equal(belief, [1.0, 2.0, 3.0, 4.0])

    def test_a_prior_is_smoothed_even_when_it_is_zero(self):
        # a prior of exactly zero is evidence, so a price appearing after a
        # stretch of zeros ramps up as alpha * raw rather than being adopted:
        # 0.25 * 8 = 2 and 0.25 * 12 = 3 from zero, 0.25 * 8 + 0.75 * 4 = 5
        # from a nonzero prior
        belief = np.array([5.0, 0.0, 4.0, 0.0])
        update_belief_path(np.array([9.0, 8.0, 8.0, 12.0]), belief, self._alpha, 1)
        np.testing.assert_array_equal(belief, [5.0, 2.0, 5.0, 3.0])

    def test_entries_before_idx_are_untouched(self):
        # neither a NaN nor a value before idx is written, whatever raw holds there
        belief = np.array([np.nan, 3.0, np.nan, np.nan])
        update_belief_path(np.array([1.0, 1.0, 6.0, 7.0]), belief, self._alpha, 2)
        np.testing.assert_array_equal(belief, [np.nan, 3.0, 6.0, 7.0])

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
            # 2-year horizon, half-year step → 1 / (1 + 2 / 0.5)
            (np.array([0.0, YEAR / 2, YEAR]), 1, 2.0, 0.2),
            # a zero-length step has no history to weigh against
            (np.array([0.0, YEAR, YEAR]), 2, 3.0, 1.0),
            # the first step has no prior step to weigh against
            (np.array([0.0, YEAR, 2 * YEAR]), 0, 3.0, 1.0),
            # an index past the timeline trusts the projection fully
            (np.array([0.0, YEAR, 2 * YEAR]), 3, 3.0, 1.0),
        ],
    )
    def test_alpha(self, timeline, idx, horizon, expected):
        assert derive_smoothing_alpha(idx, horizon, timeline) == pytest.approx(expected)
