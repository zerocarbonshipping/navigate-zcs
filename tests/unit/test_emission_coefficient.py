# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the policy emission-coefficient helpers.

Tests verify the correctness of:
  - _average_wtt_over_ports: supply-weighted averaging of port bunker WTT,
    including exclusion of zero-supply and bunkering-disallowed ports,
    per-time-step weighting, and the infinite-supply market regime.
  - _calculate_threshold_adjusted_levy_emission_coefficient: the lower and
    upper threshold are read at every future time step, not frozen at the
    value cached for the current one.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from navigate.core.enum_ import LevySchemeID
from navigate.policy.emission_coefficient import (
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
# 4. Threshold-adjusted levy emission coefficient over a time-varying threshold
# ---------------------------------------------------------------------------

TIMELINE = np.array([0.0, 365.0])


class _StepThreshold:
    """
    Stand-in for a Forecast.

    Bare ``get()`` answers the value cached at the current time step (its
    first entry, in these tests); ``get(times)`` recomputes the value at each
    of ``times``.
    """

    def __init__(self, values: list[float]) -> None:
        self._values = values

    def get(self, times=None):
        if times is None:
            return self._values[0]

        return np.asarray(self._values, dtype=float)


def _make_levy(scheme, lower_threshold, upper_threshold=None):
    levy = MagicMock()
    levy.scheme = scheme
    levy.lower_threshold = _StepThreshold(lower_threshold)
    levy.upper_threshold = (
        _StepThreshold(upper_threshold) if upper_threshold is not None else None
    )
    return levy


def _make_fuel(lower_heating_value):
    fuel = MagicMock()
    fuel.lower_heating_value.get.return_value = lower_heating_value
    return fuel


class TestThresholdAdjustedLevyEmissionCoefficient:
    def test_penalty_uses_the_threshold_at_each_future_time_step(self):
        """
        A future step must use its own threshold, not the value cached at idx.

        Regression test: the coefficient used to read the threshold with a bare
        `.get()`, which answers the value cached at the current time and froze
        every future step to it.
        """
        levy = _make_levy(LevySchemeID.PENALTY, lower_threshold=[40.0, 90.0])
        fuel = _make_fuel(40.0)
        coefficient = np.array([2.0, 3.0])  # ton emission / ton fuel

        result = _calculate_threshold_adjusted_levy_emission_coefficient(
            coefficient, levy, fuel, TIMELINE, idx=0
        )

        # g/MJ: [2, 3] / 40 * 1000 = [50, 75]; minus [40, 90] = [10, -15];
        # PENALTY clips the negative excess to 0: [10, 0];
        # back to ton/ton fuel: * 40 / 1000
        assert result == pytest.approx([0.4, 0.0])

    def test_subsidy_uses_the_threshold_at_each_future_time_step(self):
        levy = _make_levy(LevySchemeID.SUBSIDY, lower_threshold=[20.0, 30.0])
        fuel = _make_fuel(40.0)
        coefficient = np.array([1.0, 1.0])

        result = _calculate_threshold_adjusted_levy_emission_coefficient(
            coefficient, levy, fuel, TIMELINE, idx=0
        )

        # g/MJ: [1, 1] / 40 * 1000 = [25, 25]; minus [20, 30] = [5, -5];
        # SUBSIDY clips the positive excess to 0: [0, -5];
        # back to ton/ton fuel: * 40 / 1000
        assert result == pytest.approx([0.0, -0.2])

    def test_upper_threshold_uses_the_threshold_at_each_future_time_step(self):
        levy = _make_levy(
            LevySchemeID.PENALTY,
            lower_threshold=[10.0, 10.0],
            upper_threshold=[50.0, 100.0],
        )
        fuel = _make_fuel(40.0)
        coefficient = np.array([3.0, 3.0])

        result = _calculate_threshold_adjusted_levy_emission_coefficient(
            coefficient, levy, fuel, TIMELINE, idx=0
        )

        # g/MJ: [3, 3] / 40 * 1000 = [75, 75]; minus lower [10, 10] = [65, 65];
        # capped at upper - lower = [40, 90]: [40, 65];
        # back to ton/ton fuel: * 40 / 1000
        assert result == pytest.approx([1.6, 2.6])
