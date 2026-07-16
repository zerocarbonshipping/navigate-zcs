# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests for the policy emission-coefficient helpers.

Tests verify the correctness of:
  - _average_wtt_over_ports: supply-weighted averaging of port bunker WTT,
    including exclusion of zero-supply and bunkering-disallowed ports,
    per-time-step weighting, and the infinite-supply market regime.
"""
from unittest.mock import MagicMock

import numpy as np
import pytest

from navigate.policy.coefficient import _average_wtt_over_ports

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FUEL = MagicMock()
FUEL.get_name.return_value = 'fuel_bio'

EMISSION = MagicMock()
EMISSION.get_name.return_value = 'carbon_dioxide'


def _make_port(allowed, supply, wtt):
    port = MagicMock()
    port.is_bunkering_allowed.return_value = allowed
    port.expectation.get_bunker_supply.return_value = np.asarray(supply, dtype=float)
    port.expectation.get_bunker_WTT.return_value = np.asarray(wtt, dtype=float)
    return port


# ---------------------------------------------------------------------------
# 1. Zero-supply exclusion (regression for regulation WTT dilution)
# ---------------------------------------------------------------------------

class TestZeroSupplyExclusion:

    def test_zero_supply_port_does_not_dilute_average(self):
        """A port that allows bunkering but has no supply must carry no weight.

        Regression test: a jurisdiction port without supply of a fuel has a
        bunker WTT of 0 and previously diluted the average, halving e.g. the
        negative WTT of bio-fuels.
        """
        supplied = _make_port(allowed=True, supply=[100.], wtt=[-0.9])
        unsupplied = _make_port(allowed=True, supply=[0.], wtt=[0.])

        result = _average_wtt_over_ports([supplied, unsupplied], FUEL, EMISSION, idx=0)

        assert result == pytest.approx([-0.9])

    def test_no_supplied_ports_falls_back_to_zero(self):
        a = _make_port(allowed=True, supply=[0.], wtt=[-0.9])
        b = _make_port(allowed=True, supply=[0.], wtt=[-0.5])

        result = _average_wtt_over_ports([a, b], FUEL, EMISSION, idx=0)

        assert result == pytest.approx([0.])

    def test_disallowed_port_is_excluded(self):
        allowed = _make_port(allowed=True, supply=[10.], wtt=[-0.9])
        disallowed = _make_port(allowed=False, supply=[10.], wtt=[0.6])

        result = _average_wtt_over_ports([allowed, disallowed], FUEL, EMISSION, idx=0)

        assert result == pytest.approx([-0.9])

    def test_no_allowed_ports_returns_zero(self):
        a = _make_port(allowed=False, supply=[10.], wtt=[-0.9])

        result = _average_wtt_over_ports([a], FUEL, EMISSION, idx=0)

        assert result == 0.


# ---------------------------------------------------------------------------
# 2. Supply weighting
# ---------------------------------------------------------------------------

class TestSupplyWeighting:

    def test_supply_weighted_average_over_unequal_ports(self):
        large = _make_port(allowed=True, supply=[30.], wtt=[-1.0])
        small = _make_port(allowed=True, supply=[10.], wtt=[-0.6])

        result = _average_wtt_over_ports([large, small], FUEL, EMISSION, idx=0)

        # (30 * -1.0 + 10 * -0.6) / 40 = -0.9
        assert result == pytest.approx([-0.9])

    def test_supply_appearing_mid_timeline_is_weighted_per_time_step(self):
        a = _make_port(allowed=True, supply=[10., 10.], wtt=[-0.9, -0.9])
        b = _make_port(allowed=True, supply=[0., 10.], wtt=[0., -0.5])

        result = _average_wtt_over_ports([a, b], FUEL, EMISSION, idx=0)

        assert result == pytest.approx([-0.9, -0.7])


# ---------------------------------------------------------------------------
# 3. Infinite-supply market regime
# ---------------------------------------------------------------------------

class TestInfiniteSupplyRegime:

    def test_infinite_supply_port_dominates_finite_ports(self):
        market = _make_port(allowed=True, supply=[np.inf], wtt=[0.6])
        plant = _make_port(allowed=True, supply=[100.], wtt=[-0.9])

        result = _average_wtt_over_ports([market, plant], FUEL, EMISSION, idx=0)

        assert result == pytest.approx([0.6])

    def test_infinite_supply_ports_are_weighted_equally(self):
        a = _make_port(allowed=True, supply=[np.inf], wtt=[0.6])
        b = _make_port(allowed=True, supply=[np.inf], wtt=[0.2])
        c = _make_port(allowed=True, supply=[100.], wtt=[-0.9])

        result = _average_wtt_over_ports([a, b, c], FUEL, EMISSION, idx=0)

        assert result == pytest.approx([0.4])

    def test_infinite_regime_is_evaluated_per_time_step(self):
        a = _make_port(allowed=True, supply=[np.inf, 30.], wtt=[0.6, -1.0])
        b = _make_port(allowed=True, supply=[100., 10.], wtt=[-0.9, -0.6])

        result = _average_wtt_over_ports([a, b], FUEL, EMISSION, idx=0)

        # t=0: infinite regime, only port a counts; t=1: supply-weighted
        assert result == pytest.approx([0.6, -0.9])
