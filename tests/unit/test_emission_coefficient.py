# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the policy emission-coefficient helpers.

Tests verify the correctness of:
  - _average_wtt_over_ports: supply-weighted averaging of port bunker WTT,
    including exclusion of zero-supply and bunkering-disallowed ports,
    per-time-step weighting, and the infinite-supply market regime.
  - _average_effective_lhv_over_converters: power/efficiency-weighted
    (1 - slip) * LHV over the converters able to burn the fuel.
  - _assign_levy_emission_coefficients: the levy thresholds are compared with,
    and converted back on, the vessel's effective LHV.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from navigate.core.nodes.converter import Converter
from navigate.core.nodes.emission import Emission
from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.levy import Levy
from navigate.policy.emission_coefficient import (
    _assign_levy_emission_coefficients,
    _average_effective_lhv_over_converters,
    _average_wtt_over_ports,
    _converter_weights,
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
# 4. Effective heating value of a levy
# ---------------------------------------------------------------------------

# the ammonia converters weigh 15 / 0.5 = 30 MW and 4 / 0.4 = 10 MW; the oil
# converter cannot burn ammonia and carries no weight
AMMONIA_LHV = 50.0
MAIN_SLIP = 0.02
AUXILIARY_SLIP = 0.1


def _make_converter(name, fuel_type, power, efficiency, slip):
    converter = Converter(name)
    converter.set_power_capacity(power)
    converter.set_main_fuel_types(fuel_type)
    converter.set_efficiency(efficiency)
    converter.initialize_dependencies({})
    converter.set_slip_fraction(fuel_type, slip)
    converter.initialize()
    return converter


def _make_ammonia():
    fuel = Fuel("ammonia")
    fuel.set_fuel_type("AMMONIA")
    fuel.set_lower_heating_value(AMMONIA_LHV)
    return fuel


def _make_vessel(fuel, main_slip, auxiliary_slip, port):
    vessel = MagicMock()
    vessel.name = "vessel"
    vessel.usable_fuels = {fuel.name: fuel}
    vessel.route.ports = [port]
    vessel.power_system.get_converters.return_value = [
        _make_converter("main", "AMMONIA", 15.0, 0.5, main_slip),
        _make_converter("auxiliary", "AMMONIA", 4.0, 0.4, auxiliary_slip),
        _make_converter("boiler", "OIL", 100.0, 0.5, 0.0),
    ]
    return vessel


class TestEffectiveHeatingValue:
    def test_effective_lhv_is_the_weighted_average_over_burning_converters(self):
        fuel = _make_ammonia()
        vessel = _make_vessel(fuel, MAIN_SLIP, AUXILIARY_SLIP, MagicMock())

        weights = _converter_weights(vessel, fuel)
        result = _average_effective_lhv_over_converters(weights, fuel)

        # (30 * 0.98 * 50 + 10 * 0.9 * 50) / 40 = (1470 + 450) / 40 = 48
        assert result == pytest.approx(48.0)

    def test_zero_efficiency_converter_carries_no_weight(self):
        fuel = _make_ammonia()
        vessel = MagicMock()
        vessel.power_system.get_converters.return_value = [
            _make_converter("main", "AMMONIA", 15.0, 0.5, MAIN_SLIP),
            _make_converter("idle", "AMMONIA", 4.0, 0.0, AUXILIARY_SLIP),
        ]

        weights = _converter_weights(vessel, fuel)
        result = _average_effective_lhv_over_converters(weights, fuel)

        # only the main converter weighs: 0.98 * 50 = 49
        assert result == pytest.approx(49.0)

    def test_no_weighted_converter_falls_back_to_the_lhv(self):
        fuel = _make_ammonia()

        result = _average_effective_lhv_over_converters([], fuel)

        assert result == pytest.approx(AMMONIA_LHV)

    @pytest.mark.parametrize(
        ("main_slip", "auxiliary_slip", "expected"),
        [
            # effective LHV 48: 2.4 / 48 * 1000 = 50 g/MJ, 30 above the
            # threshold, back to 30 * 48 / 1000 = 1.44 t/t
            (MAIN_SLIP, AUXILIARY_SLIP, 1.44),
            # no slip, the raw LHV 50: 2.4 / 50 * 1000 = 48 g/MJ, 28 above
            # the threshold, back to 28 * 50 / 1000 = 1.4 t/t
            (0.0, 0.0, 1.4),
            # full slip, an effective LHV of 0: the fuel delivers no energy, so
            # the threshold allows nothing and the whole 2.4 t/t is levied
            (1.0, 1.0, 2.4),
        ],
        ids=["slip", "no_slip", "full_slip"],
    )
    def test_levy_threshold_is_measured_on_the_effective_lhv(
        self, main_slip, auxiliary_slip, expected
    ):
        fuel = _make_ammonia()
        emission = Emission("carbon_dioxide")
        port = MagicMock()
        port.name = "port"
        port.is_bunkering_allowed.return_value = True
        vessel = _make_vessel(fuel, main_slip, auxiliary_slip, port)

        levy = Levy("levy")
        levy.set_scheme("PENALTY")
        levy.set_lower_threshold(20.0)
        levy.fuels = [fuel]
        levy.emissions = [emission]
        levy.jurisdiction = [port]
        levy.expectation.initialize(1, [emission.name])
        levy.expectation.set_ttw_consumption(
            0, (vessel.name, fuel.name, emission.name), 2.4
        )

        _assign_levy_emission_coefficients(levy, {vessel.name: vessel}, 0)

        result = levy.expectation.get_coefficient(
            (vessel.name, port.name, fuel.name), 0
        )
        assert np.isfinite(result)
        assert result == pytest.approx(expected)
