# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the Levy node.

Tests verify the correctness of:
  - calculate_expectation: a future crossing of the upper threshold below the
    lower threshold, over timeline[idx:], raises the same way check_consistency
    does for a crossing known at parse time; a crossing already behind idx is
    not re-raised.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from navigate.core.nodes.forecast import Forecast
from navigate.core.nodes.levy import Levy

TIMELINE = np.array([0.0, 365.0, 730.0])


def _forecast(y):
    forecast = Forecast("forecast")
    forecast._set_table(TIMELINE, np.asarray(y, dtype=float))
    return forecast


def _make_levy(lower_threshold, upper_threshold):
    levy = Levy("levy")
    levy.set_lower_threshold(_forecast(lower_threshold))
    levy.set_upper_threshold(_forecast(upper_threshold))
    levy.expectation = MagicMock()
    return levy


class TestThresholdCrossingOverTime:
    def test_raises_when_a_future_upper_threshold_falls_below_the_lower_threshold(self):
        """
        Cover the whole horizon, evaluated once at the first call, idx=0.

        check_consistency only sees the cached current value, so a crossing that
        only appears at a later time-step must be caught elsewhere.
        """
        levy = _make_levy(
            lower_threshold=[90.0, 90.0, 90.0],
            upper_threshold=[100.0, 100.0, 80.0],
        )
        match = r'Levy\("levy"\).*730\.0 days'

        with pytest.raises(ValueError, match=match) as exc_info:
            levy.calculate_expectation({}, 100.0, TIMELINE, idx=0)

        assert "'UpperThreshold' must be >= 'LowerThreshold'" in str(exc_info.value)

    @pytest.mark.parametrize(
        ("lower_threshold", "upper_threshold", "idx"),
        [
            # the crossing sits at t=0 only; from idx=1 onward it never crosses
            ([90.0, 10.0, 10.0], [80.0, 100.0, 100.0], 1),
            # the thresholds never cross anywhere on the timeline
            ([10.0, 10.0, 10.0], [50.0, 50.0, 50.0], 0),
        ],
    )
    def test_does_not_raise(self, lower_threshold, upper_threshold, idx):
        levy = _make_levy(lower_threshold, upper_threshold)

        levy.calculate_expectation({}, 100.0, TIMELINE, idx=idx)

    def test_does_not_raise_without_an_upper_threshold(self):
        levy = Levy("levy")
        levy.set_lower_threshold(_forecast([10.0, 10.0, 10.0]))
        levy.expectation = MagicMock()

        levy.calculate_expectation({}, 100.0, TIMELINE, idx=0)
