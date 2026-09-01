# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests for the fuel-conversion business case (navigate/fleet/conversion.py)."""
from unittest.mock import MagicMock

import numpy as np

from navigate.core.increment import Increment
from navigate.core.nodes.fleet import Fleet
from navigate.fleet.conversion import apply_fuel_conversions
from navigate.util import dates_to_days


class TestApplyFuelConversionExpenses:
    """Conversion expenses anchor to elapsed years, not time-step indices."""

    def test_installments_land_on_calendar_timeline(self):
        vessel_a, vessel_b = MagicMock(), MagicMock()
        vessel_a.name = "a"
        vessel_b.name = "b"

        fleet = Fleet.__new__(Fleet)
        fleet.assets = [vessel_a, vessel_b]
        fleet.profile = MagicMock()
        fleet.increments = [[Increment(10., 5., 1., package_uptake=np.array([1., 0.]))], []]

        # calendar years are 365 or 366 days, so years = timeline / YEAR drifts
        # off the step indices; at idx=1 (365 days elapsed) years[1] < 1
        dates = np.array([np.datetime64(f"{year}-01-01") for year in range(2025, 2030)])
        timeline = dates_to_days(dates)
        fleet.fuel_conversion_expenses = np.zeros_like(timeline)

        idx = 1
        costs = np.array([30., 30., 30.])
        proposals = {("a", 0): {"age": 5., "dt": 1.,
                                "costs_per_vessel": {"b": costs},
                                "conversions": {"b": 2.}}}
        apply_fuel_conversions(fleet, proposals, idx=idx, timeline=timeline)

        expected = np.zeros_like(timeline)
        expected[idx:idx + costs.size] = 2. * costs[0]
        np.testing.assert_array_almost_equal(fleet.fuel_conversion_expenses, expected)
