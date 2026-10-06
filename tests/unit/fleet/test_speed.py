# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests for the feasible mean-speed bounds (calculate_speed_bounds)."""

from __future__ import annotations

import numpy as np
import pytest

from navigate.fleet.power import calculate_speed_bounds


class TestSpeedBounds:
    """Unusable technical bounds fall back on the envelope of the given speeds."""

    @pytest.mark.parametrize(
        ("speed_min", "speed_max", "speeds", "expected"),
        [
            # finite, ordered bounds: the widest technical envelope across legs
            ([6.0, 7.0, 8.0], [18.0, 20.0, 19.0], [12.0, 14.0, 16.0], (6.0, 20.0)),
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
