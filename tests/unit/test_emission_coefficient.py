# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the policy emission-coefficient helpers.

Tests verify the correctness of:
  - _average_wtt_over_ports: supply-weighted averaging of port bunker WTT,
    including exclusion of zero-supply and bunkering-disallowed ports,
    per-time-step weighting, and the infinite-supply market regime.
  - _calculate_threshold_adjusted_levy_emission_coefficient: the PENALTY,
    SUBSIDY and upper-threshold capping arithmetic, given already-evaluated
    threshold arrays.
  - _assign_levy_emission_coefficients: the thresholds it evaluates once per
    pass stay sliced to timeline[idx:], not the whole timeline.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from navigate.core.enum_ import LevySchemeID
from navigate.policy.emission_coefficient import (
    _assign_levy_emission_coefficients,
    _average_wtt_over_ports,
    _calculate_threshold_adjusted_levy_emission_coefficient,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FUEL = MagicMock()
FUEL.name = "fuel_bio"

EMISSION = MagicMock()
EMISSION.name = "carbon_dioxide"


def _make_port(allowed, supply, wtt):
    port = MagicMock()
    port.is_bunkering_allowed.return_value = allowed
    port.expectation.get_bunker_supply.return_value = np.asarray(supply, dtype=float)
    port.expectation.get_bunker_wtt.return_value = np.asarray(wtt, dtype=float)
    return port


# ---------------------------------------------------------------------------
# 1. Zero-supply exclusion (regression for regulation WTT dilution)
# ---------------------------------------------------------------------------


class TestZeroSupplyExclusion:
    def test_zero_supply_port_does_not_dilute_average(self):
        """
        A port that allows bunkering but has no supply must carry no weight.

        Regression test: a jurisdiction port without supply of a fuel has a
        bunker WTT of 0 and previously diluted the average, halving e.g. the
        negative WTT of bio-fuels.
        """
        supplied = _make_port(allowed=True, supply=[100.0], wtt=[-0.9])
        unsupplied = _make_port(allowed=True, supply=[0.0], wtt=[0.0])

        result = _average_wtt_over_ports([supplied, unsupplied], FUEL, EMISSION, idx=0)

        assert result == pytest.approx([-0.9])

    def test_no_supplied_ports_falls_back_to_zero(self):
        a = _make_port(allowed=True, supply=[0.0], wtt=[-0.9])
        b = _make_port(allowed=True, supply=[0.0], wtt=[-0.5])

        result = _average_wtt_over_ports([a, b], FUEL, EMISSION, idx=0)

        assert result == pytest.approx([0.0])

    def test_disallowed_port_is_excluded(self):
        allowed = _make_port(allowed=True, supply=[10.0], wtt=[-0.9])
        disallowed = _make_port(allowed=False, supply=[10.0], wtt=[0.6])

        result = _average_wtt_over_ports([allowed, disallowed], FUEL, EMISSION, idx=0)

        assert result == pytest.approx([-0.9])

    def test_no_allowed_ports_returns_zero(self):
        a = _make_port(allowed=False, supply=[10.0], wtt=[-0.9])

        result = _average_wtt_over_ports([a], FUEL, EMISSION, idx=0)

        assert result == 0.0


# ---------------------------------------------------------------------------
# 2. Supply weighting
# ---------------------------------------------------------------------------


class TestSupplyWeighting:
    def test_supply_weighted_average_over_unequal_ports(self):
        large = _make_port(allowed=True, supply=[30.0], wtt=[-1.0])
        small = _make_port(allowed=True, supply=[10.0], wtt=[-0.6])

        result = _average_wtt_over_ports([large, small], FUEL, EMISSION, idx=0)

        # (30 * -1.0 + 10 * -0.6) / 40 = -0.9
        assert result == pytest.approx([-0.9])

    def test_supply_appearing_mid_timeline_is_weighted_per_time_step(self):
        a = _make_port(allowed=True, supply=[10.0, 10.0], wtt=[-0.9, -0.9])
        b = _make_port(allowed=True, supply=[0.0, 10.0], wtt=[0.0, -0.5])

        result = _average_wtt_over_ports([a, b], FUEL, EMISSION, idx=0)

        assert result == pytest.approx([-0.9, -0.7])


# ---------------------------------------------------------------------------
# 3. Infinite-supply market regime
# ---------------------------------------------------------------------------


class TestInfiniteSupplyRegime:
    def test_infinite_supply_port_dominates_finite_ports(self):
        market = _make_port(allowed=True, supply=[np.inf], wtt=[0.6])
        plant = _make_port(allowed=True, supply=[100.0], wtt=[-0.9])

        result = _average_wtt_over_ports([market, plant], FUEL, EMISSION, idx=0)

        assert result == pytest.approx([0.6])

    def test_infinite_supply_ports_are_weighted_equally(self):
        a = _make_port(allowed=True, supply=[np.inf], wtt=[0.6])
        b = _make_port(allowed=True, supply=[np.inf], wtt=[0.2])
        c = _make_port(allowed=True, supply=[100.0], wtt=[-0.9])

        result = _average_wtt_over_ports([a, b, c], FUEL, EMISSION, idx=0)

        assert result == pytest.approx([0.4])

    def test_infinite_regime_is_evaluated_per_time_step(self):
        a = _make_port(allowed=True, supply=[np.inf, 30.0], wtt=[0.6, -1.0])
        b = _make_port(allowed=True, supply=[100.0, 10.0], wtt=[-0.9, -0.6])

        result = _average_wtt_over_ports([a, b], FUEL, EMISSION, idx=0)

        # t=0: infinite regime, only port a counts; t=1: supply-weighted
        assert result == pytest.approx([0.6, -0.9])


# ---------------------------------------------------------------------------
# 4. Threshold-adjusted levy emission coefficient, given evaluated thresholds
# ---------------------------------------------------------------------------


def _make_levy(scheme):
    levy = MagicMock()
    levy.scheme = scheme
    return levy


def _make_fuel(lower_heating_value):
    fuel = MagicMock()
    fuel.lower_heating_value.get.return_value = lower_heating_value
    return fuel


class TestThresholdAdjustedLevyEmissionCoefficient:
    def test_penalty_clips_the_excess_below_the_lower_threshold(self):
        levy = _make_levy(LevySchemeID.PENALTY)
        fuel = _make_fuel(40.0)
        coefficient = np.array([2.0, 3.0])  # ton emission / ton fuel
        lower_threshold = np.array([40.0, 90.0])

        result = _calculate_threshold_adjusted_levy_emission_coefficient(
            coefficient, levy, fuel, lower_threshold, upper_threshold=None
        )

        # g/MJ: [2, 3] / 40 * 1000 = [50, 75]; minus [40, 90] = [10, -15];
        # PENALTY clips the negative excess to 0: [10, 0];
        # back to ton/ton fuel: * 40 / 1000
        assert result == pytest.approx([0.4, 0.0])

    def test_subsidy_clips_the_excess_above_the_lower_threshold(self):
        levy = _make_levy(LevySchemeID.SUBSIDY)
        fuel = _make_fuel(40.0)
        coefficient = np.array([1.0, 1.0])
        lower_threshold = np.array([20.0, 30.0])

        result = _calculate_threshold_adjusted_levy_emission_coefficient(
            coefficient, levy, fuel, lower_threshold, upper_threshold=None
        )

        # g/MJ: [1, 1] / 40 * 1000 = [25, 25]; minus [20, 30] = [5, -5];
        # SUBSIDY clips the positive excess to 0: [0, -5];
        # back to ton/ton fuel: * 40 / 1000
        assert result == pytest.approx([0.0, -0.2])

    def test_upper_threshold_caps_the_penalty(self):
        levy = _make_levy(LevySchemeID.PENALTY)
        fuel = _make_fuel(40.0)
        coefficient = np.array([3.0, 3.0])
        lower_threshold = np.array([10.0, 10.0])
        upper_threshold = np.array([50.0, 100.0])

        result = _calculate_threshold_adjusted_levy_emission_coefficient(
            coefficient, levy, fuel, lower_threshold, upper_threshold
        )

        # g/MJ: [3, 3] / 40 * 1000 = [75, 75]; minus lower [10, 10] = [65, 65];
        # capped at upper - lower = [40, 90]: [40, 65];
        # back to ton/ton fuel: * 40 / 1000
        assert result == pytest.approx([1.6, 2.6])


# ---------------------------------------------------------------------------
# 5. Levy emission coefficients: thresholds stay sliced to the remaining
#    timeline once their evaluation moves out of the vessel/port/fuel loop
# ---------------------------------------------------------------------------

TIMELINE = np.array([0.0, 365.0, 730.0])


class _ThresholdLookup:
    """
    Stand-in for a Forecast whose value depends on the times it is asked for.

    Bare ``get()`` answers the value cached at the current time step; ``get(times)``
    looks up each of ``times`` in a table, so a slice with the wrong times reads back
    the wrong values, and one with the wrong length raises or fails a length check.
    """

    def __init__(self, table: dict[float, float], current: float) -> None:
        self._table = table
        self._current = current

    def get(self, times=None):
        if times is None:
            return self._current

        return np.array([self._table[time] for time in times], dtype=float)


class TestAssignLevyEmissionCoefficientsSlicing:
    def test_threshold_is_sliced_to_the_remaining_timeline(self):
        """
        The threshold, evaluated once before the loops, must cover only idx onward.

        Regression test: moving the evaluation out of the vessel/port/fuel loop
        must keep it reading timeline[idx:], not the whole timeline.
        """
        idx = 1  # timeline[idx:] == [365.0, 730.0]

        fuel = _make_fuel(40.0)
        fuel.name = "fuel_bio"

        port = MagicMock()
        port.name = "port1"
        port.is_bunkering_allowed.return_value = True

        vessel = MagicMock()
        vessel.name = "vessel1"
        vessel.usable_fuels = {"fuel_bio": fuel}
        vessel.route.ports = [port]

        levy = _make_levy(LevySchemeID.PENALTY)
        levy.emissions = [EMISSION]
        levy.fuels = [fuel]
        levy.jurisdiction = [port]
        levy.lower_threshold = _ThresholdLookup(
            {0.0: 10.0, 365.0: 20.0, 730.0: 30.0}, current=10.0
        )
        levy.upper_threshold = None
        levy.expectation.get_wtt.return_value = np.array([3.2, 3.2])
        levy.expectation.get_ttw_consumption.return_value = 0.0
        levy.expectation.get_ttw_slip.return_value = 0.0

        _assign_levy_emission_coefficients(levy, {"vessel1": vessel}, TIMELINE, idx)

        call_idx, key, coefficient = levy.expectation.set_coefficient.call_args[0]

        # lower threshold at idx onward is [20, 30]; g/MJ: 3.2 / 40 * 1000 = 80
        # for both steps; minus [20, 30] = [60, 50]; back to ton/ton fuel: * 40 / 1000
        assert call_idx == idx
        assert key == ("vessel1", "port1", "fuel_bio")
        assert len(coefficient) == 2
        assert coefficient == pytest.approx([2.4, 2.0])
