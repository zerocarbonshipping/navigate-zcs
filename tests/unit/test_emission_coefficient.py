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
  - _average_effective_lhv_over_converters: power/efficiency-weighted
    (1 - slip) * LHV over the converters able to burn the fuel.
  - _calculate_threshold_adjusted_levy_emission_coefficient: the PENALTY,
    SUBSIDY and upper-threshold capping arithmetic, given already-evaluated
    threshold arrays and an effective LHV.
  - _assign_levy_emission_coefficients: the thresholds it evaluates once per
    pass are read over timeline[idx:], not the whole timeline, and are
    compared with, and converted back on, the vessel's effective LHV.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from navigate.core.enum_ import LevySchemeID
from navigate.core.nodes.converter import Converter
from navigate.core.nodes.emission import Emission
from navigate.core.nodes.forecast import Forecast
from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.levy import Levy
from navigate.core.table_data import TableData
from navigate.policy.emission_coefficient import (
    _assign_levy_emission_coefficients,
    _assign_regulation_wtt_factors,
    _average_effective_lhv_over_converters,
    _average_wtt_over_ports,
    _calculate_threshold_adjusted_levy_emission_coefficient,
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

        Regression test: a route port without supply of a fuel has a
        bunker WTT of 0 and previously diluted the average, halving e.g. the
        negative WTT of bio-fuels.
        """
        supplied = _make_port(allowed=True, supply=[100.0], wtt=[-0.9])
        unsupplied = _make_port(allowed=True, supply=[0.0], wtt=[0.0])

        result = _average_wtt_over_ports([supplied, unsupplied], FUEL, EMISSION, idx=0)

        assert result == pytest.approx([-0.9])

    @pytest.mark.parametrize(
        ("allowed", "supply"),
        [(True, 0.0), (False, 10.0)],
        ids=["no_supply", "no_allowed_port"],
    )
    def test_no_weighted_port_falls_back_to_zero(self, allowed, supply):
        a = _make_port(allowed=allowed, supply=[supply], wtt=[-0.9])
        b = _make_port(allowed=allowed, supply=[supply], wtt=[-0.5])

        result = _average_wtt_over_ports([a, b], FUEL, EMISSION, idx=0)

        assert np.all(np.asarray(result) == 0.0)

    def test_disallowed_port_is_excluded(self):
        allowed = _make_port(allowed=True, supply=[10.0], wtt=[-0.9])
        disallowed = _make_port(allowed=False, supply=[10.0], wtt=[0.6])

        result = _average_wtt_over_ports([allowed, disallowed], FUEL, EMISSION, idx=0)

        assert result == pytest.approx([-0.9])


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


# ---------------------------------------------------------------------------
# 5. Effective heating value of a levy
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
            # effective LHV 48: 2.4 / 48 * 1000 = 50 g/MJ, [30, 20] above the
            # thresholds, back to [30, 20] * 48 / 1000 t/t
            (MAIN_SLIP, AUXILIARY_SLIP, [1.44, 0.96]),
            # no slip, the raw LHV 50: 2.4 / 50 * 1000 = 48 g/MJ, [28, 18]
            # above the thresholds, back to [28, 18] * 50 / 1000 t/t
            (0.0, 0.0, [1.4, 0.9]),
            # full slip, an effective LHV of 0: the fuel delivers no energy, so
            # the threshold allows nothing and the whole 2.4 t/t is levied
            (1.0, 1.0, [2.4, 2.4]),
        ],
        ids=["slip", "no_slip", "full_slip"],
    )
    def test_levy_threshold_is_measured_on_the_effective_lhv(
        self, main_slip, auxiliary_slip, expected
    ):
        # the threshold rises from 10 g/MJ at day 0 to 30 at day 730, so read
        # from idx 1 onward it is [20, 30]; reading the whole timeline instead
        # would return three values starting at 10
        idx = 1
        timeline = np.array([0.0, 365.0, 730.0])
        threshold = Forecast("threshold")
        threshold.set_table(TableData(rows=[[0.0, 10.0], [730.0, 30.0]]))
        threshold.replace_reference_table(np.datetime64("2026-01-01"))

        fuel = _make_ammonia()
        emission = Emission("carbon_dioxide")
        port = MagicMock()
        port.name = "port"
        port.is_bunkering_allowed.return_value = True
        vessel = _make_vessel(fuel, main_slip, auxiliary_slip, port)

        levy = Levy("levy")
        levy.set_scheme("PENALTY")
        levy.set_lower_threshold(threshold)
        levy.fuels = [fuel]
        levy.emissions = [emission]
        levy.jurisdiction = [port]
        levy.expectation.initialize(timeline.size, [emission.name])
        levy.expectation.set_ttw_consumption(
            idx, (vessel.name, fuel.name, emission.name), 2.4
        )

        _assign_levy_emission_coefficients(
            levy, {vessel.name: vessel}, timeline=timeline, idx=idx
        )

        key = (vessel.name, port.name, fuel.name)
        result = [levy.expectation.get_coefficient(key, i) for i in (1, 2)]
        assert np.all(np.isfinite(result))
        assert result == pytest.approx(expected)


# ---------------------------------------------------------------------------
# 6. Threshold-adjusted levy emission coefficient, given evaluated thresholds
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
        coefficient = np.array([2.0, 3.0])  # ton emission / ton fuel
        lower_threshold = np.array([40.0, 90.0])

        result = _calculate_threshold_adjusted_levy_emission_coefficient(
            coefficient, levy, 40.0, lower_threshold, upper_threshold=None
        )

        # g/MJ: [2, 3] / 40 * 1000 = [50, 75]; minus [40, 90] = [10, -15];
        # PENALTY clips the negative excess to 0: [10, 0];
        # back to ton/ton fuel: * 40 / 1000
        assert result == pytest.approx([0.4, 0.0])

    def test_subsidy_clips_the_excess_above_the_lower_threshold(self):
        levy = _make_levy(LevySchemeID.SUBSIDY)
        coefficient = np.array([1.0, 1.0])
        lower_threshold = np.array([20.0, 30.0])

        result = _calculate_threshold_adjusted_levy_emission_coefficient(
            coefficient, levy, 40.0, lower_threshold, upper_threshold=None
        )

        # g/MJ: [1, 1] / 40 * 1000 = [25, 25]; minus [20, 30] = [5, -5];
        # SUBSIDY clips the positive excess to 0: [0, -5];
        # back to ton/ton fuel: * 40 / 1000
        assert result == pytest.approx([0.0, -0.2])

    def test_upper_threshold_caps_the_penalty(self):
        levy = _make_levy(LevySchemeID.PENALTY)
        coefficient = np.array([3.0, 3.0])
        lower_threshold = np.array([10.0, 10.0])
        upper_threshold = np.array([50.0, 100.0])

        result = _calculate_threshold_adjusted_levy_emission_coefficient(
            coefficient, levy, 40.0, lower_threshold, upper_threshold
        )

        # g/MJ: [3, 3] / 40 * 1000 = [75, 75]; minus lower [10, 10] = [65, 65];
        # capped at upper - lower = [40, 90]: [40, 65];
        # back to ton/ton fuel: * 40 / 1000
        assert result == pytest.approx([1.6, 2.6])
