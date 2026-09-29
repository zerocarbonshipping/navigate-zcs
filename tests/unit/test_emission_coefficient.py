# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the policy emission-coefficient helpers.

Tests verify the correctness of:
  - _average_wtt_over_ports: supply-weighted averaging of port bunker WTT,
    including exclusion of zero-supply and bunkering-disallowed ports,
    per-time-step weighting, and the infinite-supply market regime.
  - _assign_regulation_wtt_factors: the average runs over every port on the
    vessel's route, jurisdiction or not, each port counted once.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from navigate.policy.emission_coefficient import (
    _assign_regulation_wtt_factors,
    _average_wtt_over_ports,
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

        Regression test: a route port without supply of a fuel has a
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
# 4. Route-wide port selection
# ---------------------------------------------------------------------------

VESSEL_NAME = "vessel"


def _assigned_regulation_wtt(route_ports, jurisdiction):
    """Run the regulation WTT assignment for one vessel and return its factor."""
    regulation = MagicMock()
    regulation.fuels = [FUEL]
    regulation.emissions = [EMISSION]
    regulation.fuel_wtt = {(FUEL.name, EMISSION.name): None}
    regulation.jurisdiction = jurisdiction
    regulation.in_jurisdiction_vessel = {VESSEL_NAME: True}
    # a GWP of 1 makes the assigned factor the averaged WTT itself
    regulation.expectation.get_global_warming_potential.return_value = 1.0

    vessel = MagicMock()
    vessel.route.ports = route_ports
    vessel.usable_fuels = {FUEL.name: FUEL}

    _assign_regulation_wtt_factors(
        regulation, {VESSEL_NAME: vessel}, timeline=np.array([0.0]), idx=0
    )

    _, key, factor = regulation.expectation.set_wtt.call_args.args
    assert key == (VESSEL_NAME, FUEL.name, EMISSION.name)
    return factor


class TestRouteWidePortSelection:
    def test_supply_outside_jurisdiction_sets_the_wtt(self):
        """
        A vessel bunkering only outside the jurisdiction gets that port's WTT.

        The jurisdiction port has no supply, so averaging over it alone would
        give 0 instead of the WTT of the fuel the vessel actually bunkers.
        """
        inside = _make_port(allowed=True, supply=[0.0], wtt=[0.0])
        outside = _make_port(allowed=True, supply=[50.0], wtt=[-0.9])

        factor = _assigned_regulation_wtt([inside, outside], jurisdiction=[inside])

        assert factor == pytest.approx([-0.9])

    def test_port_visited_twice_counts_once(self):
        a = _make_port(allowed=True, supply=[10.0], wtt=[-1.0])
        b = _make_port(allowed=True, supply=[10.0], wtt=[0.2])

        factor = _assigned_regulation_wtt([a, b, a], jurisdiction=[a, b])

        # (10 * -1.0 + 10 * 0.2) / 20 = -0.4; counting a twice would give -0.6
        assert factor == pytest.approx([-0.4])
