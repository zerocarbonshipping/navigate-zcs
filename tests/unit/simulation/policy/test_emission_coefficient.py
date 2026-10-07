# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the policy emission-coefficient helpers.

Tests verify the correctness of:
  - _estimate_port_wtt: the port's WTT overwrite wins, a fuel otherwise takes
    the equal-weight mean of its plants' production plus delivery WTT, and a
    fuel no plant produces is NaN.
  - calculate_policy_emission_coefficients: only the plants producing a fuel
    enter its estimate, read from the current time step onward.
  - _assign_regulation_wtt_factors: the equal-weight mean runs over every port
    on the vessel's route, jurisdiction or not, each port counted once, leaving
    out ports that disallow the fuel or have no estimate.
  - _average_effective_lhv_over_converters: power/efficiency-weighted
    (1 - slip) * LHV over the converters able to burn the fuel.
  - _calculate_threshold_adjusted_levy_emission_coefficient: the PENALTY,
    SUBSIDY and upper-threshold capping arithmetic, given already-evaluated
    threshold arrays and an effective LHV.
  - _assign_levy_emission_coefficients: the thresholds it evaluates once per
    pass stay sliced to timeline[idx:], not the whole timeline, and are
    compared with, and converted back on, the vessel's effective LHV.
  - a NaN WTT factor, from a fuel without an estimate, leaves the regulation
    or levy coefficient unwritten.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from navigate.core.enum_ import LevySchemeID, PolicyScopeID
from navigate.core.expectations.plant_expectation import PlantExpectation
from navigate.core.expectations.regulation_expectation import RegulationExpectation
from navigate.core.nodes.converter import Converter
from navigate.core.nodes.emission import Emission
from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.levy import Levy
from navigate.simulation.policy.emission_coefficient import (
    _assign_levy_emission_coefficients,
    _assign_levy_emission_factors,
    _assign_regulation_emission_factors,
    _assign_regulation_wtt_factors,
    _average_effective_lhv_over_converters,
    _calculate_threshold_adjusted_levy_emission_coefficient,
    _converter_weights,
    _estimate_port_wtt,
    calculate_policy_emission_coefficients,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FUEL = MagicMock()
FUEL.name = "fuel_bio"

EMISSION = MagicMock()
EMISSION.name = "carbon_dioxide"


def _make_port(name, overwrite=None, allowed=True, fuel_name=FUEL.name, length=1):
    """Stub a port; `overwrite` is its WTT overwrite of the fuel, None where unset."""
    port = MagicMock()
    port.name = name
    port.is_bunkering_allowed.return_value = allowed
    port.bunker_wtt_overwrite = {(fuel_name, EMISSION.name): overwrite}
    port.expectation.get_bunker_wtt_overwrite.return_value = np.asarray(
        overwrite, dtype=float
    )
    port.expectation.get_shape.return_value = (length,)
    return port


def _make_plant(fuel_name, production, delivery):
    """
    Stub a plant of a fuel with its production and delivery WTT over the timeline.

    `delivery` maps a port name to its delivery WTT; a port left out keeps the
    expectation default of 0, as for a port without a transport assignment.
    """
    expectation = PlantExpectation()
    expectation.initialize(
        len(production),
        dict.fromkeys([EMISSION.name]),
        {},
        dict.fromkeys(["port_a", *delivery]),
        {},
    )
    for t, wtt in enumerate(production):
        expectation.set_production_wtt(t, EMISSION.name, wtt)
    for port_name, wtt in delivery.items():
        expectation.set_delivery_wtt(0, port_name, EMISSION.name, np.asarray(wtt))

    plant = MagicMock()
    plant.fuel.name = fuel_name
    plant.expectation = expectation
    return plant


# ---------------------------------------------------------------------------
# 1. WTT estimate of a fuel at a port
# ---------------------------------------------------------------------------


class TestEstimatePortWtt:
    def test_overwrite_wins_over_the_plants(self):
        port = _make_port("port_a", overwrite=[0.6])
        plants = [_make_plant(FUEL.name, [-0.9], {})]

        result = _estimate_port_wtt(port, FUEL, EMISSION, plants, idx=0)

        assert result == pytest.approx([0.6])

    def test_plant_mean_includes_the_delivery_wtt(self):
        port = _make_port("port_a")
        plants = [
            _make_plant(FUEL.name, [-1.0], {"port_a": [0.2]}),
            _make_plant(FUEL.name, [-0.6], {}),
        ]

        result = _estimate_port_wtt(port, FUEL, EMISSION, plants, idx=0)

        # ((-1.0 + 0.2) + (-0.6 + 0.0)) / 2 = -0.7
        assert result == pytest.approx([-0.7])

    def test_fuel_without_plant_has_no_estimate(self):
        port = _make_port("port_a", length=2)

        result = _estimate_port_wtt(port, FUEL, EMISSION, [], idx=0)

        assert result.shape == (2,)
        assert np.isnan(result).all()


# ---------------------------------------------------------------------------
# 2. Plants enter the estimate of their own fuel only, from idx onward
# ---------------------------------------------------------------------------


def _make_wtt_levy(jurisdiction):
    """Stub an active WTT levy on FUEL whose GWP of 1 leaves the estimate as is."""
    levy = MagicMock()
    levy.is_active.return_value = True
    levy.scope = PolicyScopeID.WTT
    levy.fuels = [FUEL]
    levy.emissions = [EMISSION]
    levy.fuel_wtt = {(FUEL.name, EMISSION.name): None}
    levy.jurisdiction = jurisdiction
    levy.expectation.get_global_warming_potential.return_value = 1.0
    return levy


class TestPlantsByFuel:
    def test_plants_of_other_fuels_are_excluded(self):
        port = _make_port("port_a")
        levy = _make_wtt_levy([port])
        # index 0 lies before idx = 1 and must not be read
        plants = {
            "plant_1": _make_plant(FUEL.name, [9.0, -1.0], {"port_a": [9.0, 0.2]}),
            "plant_2": _make_plant(FUEL.name, [9.0, -0.6], {}),
            "plant_3": _make_plant("fuel_other", [9.0, 5.0], {}),
        }

        calculate_policy_emission_coefficients(
            {}, {"levy": levy}, {}, plants, timeline=np.array([0.0, 365.0]), idx=1
        )

        call_idx, key, factor = levy.expectation.set_wtt.call_args.args
        # ((-1.0 + 0.2) + (-0.6 + 0.0)) / 2 = -0.7; counting fuel_other's plant
        # would give (-0.8 - 0.6 + 5.0) / 3 = 1.2
        assert call_idx == 1
        assert key == ("port_a", FUEL.name, EMISSION.name)
        assert factor == pytest.approx([-0.7])


# ---------------------------------------------------------------------------
# 3. Regulation WTT: equal-weight mean over the route ports
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

    # no plant produces FUEL, so a port without an overwrite has no estimate
    _assign_regulation_wtt_factors(
        regulation, {VESSEL_NAME: vessel}, {}, timeline=np.array([0.0]), idx=0
    )

    _, key, factor = regulation.expectation.set_wtt.call_args.args
    assert key == (VESSEL_NAME, FUEL.name, EMISSION.name)
    return factor


PORT_A = _make_port("port_a", overwrite=[-1.0])
PORT_B = _make_port("port_b", overwrite=[0.2])
PORT_DISALLOWED = _make_port("port_disallowed", overwrite=[5.0], allowed=False)
PORT_WITHOUT_ESTIMATE = _make_port("port_without_estimate")


class TestRegulationRouteMean:
    @pytest.mark.parametrize(
        ("route_ports", "expected"),
        [
            # the disallowed port's 5.0 would give (-1.0 + 5.0) / 2 = 2.0
            ([PORT_A, PORT_DISALLOWED], -1.0),
            # the port without an estimate would make the mean NaN
            ([PORT_A, PORT_WITHOUT_ESTIMATE], -1.0),
            # (-1.0 + 0.2) / 2 = -0.4; counting port_a twice would give -0.6
            ([PORT_A, PORT_B, PORT_A], -0.4),
        ],
        ids=["disallowed_port", "port_without_estimate", "repeated_port"],
    )
    def test_mean_over_the_contributing_route_ports(self, route_ports, expected):
        factor = _assigned_regulation_wtt(route_ports, jurisdiction=route_ports)

        assert factor == pytest.approx([expected])

    def test_port_outside_the_jurisdiction_counts(self):
        """
        A vessel may bunker a fuel outside the jurisdiction and burn it inside.

        Averaging over the jurisdiction port alone would give its -1.0.
        """
        factor = _assigned_regulation_wtt([PORT_A, PORT_B], jurisdiction=[PORT_A])

        # (-1.0 + 0.2) / 2 = -0.4
        assert factor == pytest.approx([-0.4])

    def test_route_without_estimate_gives_a_nan_factor(self):
        factor = _assigned_regulation_wtt(
            [PORT_DISALLOWED, PORT_WITHOUT_ESTIMATE], jurisdiction=[PORT_DISALLOWED]
        )

        assert np.isnan(factor).all()


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

        _assign_levy_emission_coefficients(
            levy, {vessel.name: vessel}, timeline=np.array([0.0]), idx=0
        )

        result = levy.expectation.get_coefficient(
            (vessel.name, port.name, fuel.name), 0
        )
        assert np.isfinite(result)
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


# ---------------------------------------------------------------------------
# 7. Levy emission coefficients: thresholds stay sliced to the remaining
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
        # no converter weighs, so the effective LHV falls back to the fuel's raw LHV
        vessel.power_system.get_converters.return_value = []

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


# ---------------------------------------------------------------------------
# 8. A NaN WTT factor leaves the coefficient unwritten
# ---------------------------------------------------------------------------


class TestNanWttLeavesNoCoefficient:
    """
    A fuel without a WTT estimate keeps its NaN factor out of the coefficients.

    Written from the NaN factor, a coefficient would read back NaN; the getter's
    0.0 for a missing key shows that none was written.
    """

    def test_regulation_route_without_estimate_writes_no_coefficient(self):
        fuel = _make_ammonia()
        emission = Emission("carbon_dioxide")
        # no plant produces the fuel and the port has no overwrite
        port = _make_port("port_a", fuel_name=fuel.name)
        vessel = _make_vessel(fuel, MAIN_SLIP, AUXILIARY_SLIP, port)

        regulation = MagicMock()
        regulation.scope = PolicyScopeID.WTT
        regulation.fuels = [fuel]
        regulation.emissions = [emission]
        regulation.fuel_wtt = {(fuel.name, emission.name): None}
        regulation.in_jurisdiction_vessel = {vessel.name: True}
        regulation.expectation = RegulationExpectation()
        regulation.expectation.initialize(1, [emission.name], {})
        regulation.expectation.set_global_warming_potential(emission.name, 1.0)

        _assign_regulation_emission_factors(
            regulation, {vessel.name: vessel}, {}, timeline=np.array([0.0]), idx=0
        )

        wtt = regulation.expectation.get_wtt((vessel.name, fuel.name, emission.name), 0)
        coefficient = regulation.expectation.get_coefficient(
            (vessel.name, "main", fuel.name), 0
        )
        assert np.isnan(wtt)
        assert coefficient == 0.0

    def test_levy_port_without_estimate_writes_no_coefficient(self):
        fuel = _make_ammonia()
        emission = Emission("carbon_dioxide")
        port_with_estimate = _make_port("port_a", overwrite=[2.4], fuel_name=fuel.name)
        port_without_estimate = _make_port("port_b", fuel_name=fuel.name)
        vessel = _make_vessel(fuel, 0.0, 0.0, port_with_estimate)
        vessel.route.ports = [port_with_estimate, port_without_estimate]

        levy = Levy("levy")
        levy.set_scheme("PENALTY")
        levy.set_scope("WTT")
        levy.fuels = [fuel]
        levy.emissions = [emission]
        levy.fuel_wtt = {(fuel.name, emission.name): None}
        levy.jurisdiction = [port_with_estimate, port_without_estimate]
        levy.expectation.initialize(1, [emission.name])
        levy.expectation.set_global_warming_potential(emission.name, 1.0)

        _assign_levy_emission_factors(
            levy, {vessel.name: vessel}, {}, timeline=np.array([0.0]), idx=0
        )

        wtt = levy.expectation.get_wtt(("port_b", fuel.name, emission.name), 0)
        coefficient = levy.expectation.get_coefficient(
            (vessel.name, "port_b", fuel.name), 0
        )
        assert np.isnan(wtt)
        assert coefficient == 0.0

        # the port with an estimate keeps its coefficient: the overwrite of
        # 2.4 t/t against the default lower threshold of 0
        coefficient = levy.expectation.get_coefficient(
            (vessel.name, "port_a", fuel.name), 0
        )
        assert coefficient == pytest.approx(2.4)
