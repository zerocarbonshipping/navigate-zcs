# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for shore power: regulation integration, expected-scope transfer, and gate logic."""
from collections import defaultdict
from unittest.mock import MagicMock

import pytest

from navigate.bunker.coefficients import calculate_regulation_coefficients
from navigate.bunker.transfer.shore_power import transfer_shore_power
from navigate.core import Scalar
from navigate.core.enum_ import (
    BunkerScopeID,
    RegulationMeasureID,
)
from navigate.core.unit import TON_TO_KG


def _make_emission(name):
    e = MagicMock()
    e.name = name
    return e


def _make_port_expectation(shore_ef, shore_cost=0., connection_share=1.0, capacity=10.):
    """Create a mock port expectation with shore power attributes."""
    exp = MagicMock()
    exp.get_shore_power_emission_factor = lambda emission_name, idx=None: shore_ef.get(emission_name, 0.)
    exp.get_shore_power_cost.return_value = shore_cost
    exp.get_shore_power_connection_share.return_value = connection_share
    return exp


def _make_regulation(name, measure, emissions, gwp=None):
    """Create a mock regulation with standard methods."""
    reg = MagicMock()
    reg.name = name
    reg.measure = measure
    reg.emissions = emissions
    reg.is_active.return_value = True

    gwp = gwp or {}
    reg_exp = MagicMock()
    reg_exp.get_global_warming_potential = lambda e: gwp.get(e, 1.)
    reg.expectation = reg_exp

    reg.vessel_threshold = defaultdict(lambda: Scalar(0.))

    return reg


class TestShoreRegulationCoefficient:
    """Test shore power regulation emission factor and spend coefficient computation."""

    def test_absolute_regulation_coefficient_equals_emission_factor(self):
        """For ABSOLUTE measure, spend coefficient equals emission factor (no threshold subtraction)."""
        from navigate.bunker.bunker_algorithm import BunkerAlgorithm

        algo = BunkerAlgorithm()

        # minimal state
        v = "vessel_1"
        r = "reg_1"
        algo.idx = 0
        algo.scope = BunkerScopeID.EXISTING
        algo.emissions = {"co2": _make_emission("co2")}

        # shore power variable at port index 0
        sp_var = MagicMock()
        algo.shore_power = {(v, 0): sp_var}

        # port with shore power emission factor
        port = MagicMock()
        port_exp = _make_port_expectation(shore_ef={"co2": 0.05})
        port.expectation = port_exp

        route = MagicMock()
        route.ports = [port]

        vessel = MagicMock()
        vessel.name = v
        vessel.route = route
        vessel.power_system.get_converters.return_value = ()

        # regulation: ABSOLUTE, targets all emissions
        regulation = _make_regulation(
            name=r,
            measure=RegulationMeasureID.ABSOLUTE,
            emissions=[_make_emission("co2")],
        )
        algo.active_regulations = {r: regulation}
        algo.effective_lhv = {}
        algo.regulation_emission_factor = {}
        algo.regulation_spend_coefficient = {}
        algo.shore_power_regulation_emission_factor = {}
        algo.shore_power_regulation_coefficient = {}

        calculate_regulation_coefficients(algo, vessel)

        # shore power EF should be 0.05 ton/GJ
        assert algo.shore_power_regulation_emission_factor[(v, 0, r)] == pytest.approx(0.05)
        # for ABSOLUTE, coefficient == emission factor
        assert algo.shore_power_regulation_coefficient[(v, 0, r)] == pytest.approx(0.05)

    def test_intensity_regulation_subtracts_threshold(self):
        """For INTENSITY measure, threshold / TON_TO_KG * 1.0 is subtracted from EF."""
        from navigate.bunker.bunker_algorithm import BunkerAlgorithm

        algo = BunkerAlgorithm()

        v = "vessel_1"
        r = "reg_1"
        algo.idx = 0
        algo.scope = BunkerScopeID.EXISTING
        algo.emissions = {"co2": _make_emission("co2")}

        sp_var = MagicMock()
        algo.shore_power = {(v, 0): sp_var}

        port = MagicMock()
        port_exp = _make_port_expectation(shore_ef={"co2": 0.05})
        port.expectation = port_exp

        route = MagicMock()
        route.ports = [port]

        vessel = MagicMock()
        vessel.name = v
        vessel.route = route
        vessel.power_system.get_converters.return_value = ()

        threshold = 10.0  # ton CO2/ton fuel equivalent
        regulation = _make_regulation(
            name=r,
            measure=RegulationMeasureID.INTENSITY,
            emissions=[_make_emission("co2")],
        )
        regulation.vessel_threshold = defaultdict(lambda: Scalar(threshold))

        algo.active_regulations = {r: regulation}
        algo.effective_lhv = {}
        algo.regulation_emission_factor = {}
        algo.regulation_spend_coefficient = {}
        algo.shore_power_regulation_emission_factor = {}
        algo.shore_power_regulation_coefficient = {}

        calculate_regulation_coefficients(algo, vessel)

        expected_ef = 0.05
        expected_coeff = 0.05 - threshold / TON_TO_KG * 1.0

        assert algo.shore_power_regulation_emission_factor[(v, 0, r)] == pytest.approx(expected_ef)
        assert algo.shore_power_regulation_coefficient[(v, 0, r)] == pytest.approx(expected_coeff)

    def test_gwp_conversion_applied(self):
        """When regulation uses GWP units, shore power EF is multiplied by GWP."""
        from navigate.bunker.bunker_algorithm import BunkerAlgorithm

        algo = BunkerAlgorithm()

        v = "vessel_1"
        r = "reg_1"
        algo.idx = 0
        algo.scope = BunkerScopeID.EXISTING
        algo.emissions = {"co2": _make_emission("co2"), "ch4": _make_emission("ch4")}

        sp_var = MagicMock()
        algo.shore_power = {(v, 0): sp_var}

        port = MagicMock()
        port_exp = _make_port_expectation(shore_ef={"co2": 0.05, "ch4": 0.001})
        port.expectation = port_exp

        route = MagicMock()
        route.ports = [port]

        vessel = MagicMock()
        vessel.name = v
        vessel.route = route
        vessel.power_system.get_converters.return_value = ()

        gwp = {"co2": 1.0, "ch4": 28.0}
        regulation = _make_regulation(
            name=r,
            measure=RegulationMeasureID.ABSOLUTE,
            emissions=[_make_emission("co2"), _make_emission("ch4")],
            gwp=gwp,
        )
        algo.active_regulations = {r: regulation}
        algo.effective_lhv = {}
        algo.regulation_emission_factor = {}
        algo.regulation_spend_coefficient = {}
        algo.shore_power_regulation_emission_factor = {}
        algo.shore_power_regulation_coefficient = {}

        calculate_regulation_coefficients(algo, vessel)

        # co2: 0.05 * 1.0 + ch4: 0.001 * 28.0 = 0.078
        expected = 0.05 * 1.0 + 0.001 * 28.0
        assert algo.shore_power_regulation_emission_factor[(v, 0, r)] == pytest.approx(expected)

    def test_no_shore_power_no_coefficient(self):
        """Ports without shore power variables get no regulation coefficient."""
        from navigate.bunker.bunker_algorithm import BunkerAlgorithm

        algo = BunkerAlgorithm()

        v = "vessel_1"
        r = "reg_1"
        algo.idx = 0
        algo.scope = BunkerScopeID.EXISTING
        algo.emissions = {"co2": _make_emission("co2")}
        algo.shore_power = {}  # no shore power

        port = MagicMock()
        port_exp = _make_port_expectation(shore_ef={"co2": 0.05})
        port.expectation = port_exp

        route = MagicMock()
        route.ports = [port]

        vessel = MagicMock()
        vessel.name = v
        vessel.route = route
        vessel.power_system.get_converters.return_value = ()

        regulation = _make_regulation(
            name=r,
            measure=RegulationMeasureID.ABSOLUTE,
            emissions=[_make_emission("co2")],
        )
        algo.active_regulations = {r: regulation}
        algo.effective_lhv = {}
        algo.regulation_emission_factor = {}
        algo.regulation_spend_coefficient = {}
        algo.shore_power_regulation_emission_factor = {}
        algo.shore_power_regulation_coefficient = {}

        calculate_regulation_coefficients(algo, vessel)

        assert (v, 0, r) not in algo.shore_power_regulation_emission_factor
        assert (v, 0, r) not in algo.shore_power_regulation_coefficient


class TestShoreTransferExpected:
    """Test shore power transfer for expected scope."""

    def test_expected_scope_transfers_energy_and_cost(self):
        """Expected scope should transfer shore power energy and cost to vessel expectation."""
        from navigate.bunker.bunker_algorithm import BunkerAlgorithm

        algo = BunkerAlgorithm()

        v = "vessel_1"
        algo.idx = 5
        algo.scope = BunkerScopeID.EXPECTED
        algo.emissions = {"co2": _make_emission("co2")}

        options = MagicMock()
        options.solution_tolerance = 1e-6
        algo.options = options

        # shore power variable with solution value
        sp_var = MagicMock()
        sp_var.X = 100.0  # 100 GJ
        algo.shore_power = {(v, 0): sp_var}

        # port with cost
        port = MagicMock()
        port_exp = MagicMock()
        port_exp.get_shore_power_cost.return_value = 25.0  # $/GJ
        port.expectation = port_exp

        route = MagicMock()
        route.ports = [port]

        vessel_exp = MagicMock()
        vessel = MagicMock()
        vessel.name = v
        vessel.route = route
        vessel.expectation = vessel_exp

        algo.vessels = {v: vessel}

        transfer_shore_power(algo)

        vessel_exp.add_total_energy.assert_called_once_with(5, 100.0)
        vessel_exp.add_fuel_expenses.assert_called_once_with(5, 2500.0)

    def test_existing_scope_transfers_to_profile(self):
        """Existing scope should transfer shore power to vessel profile (not expectation)."""
        from navigate.bunker.bunker_algorithm import BunkerAlgorithm

        algo = BunkerAlgorithm()

        v = "vessel_1"
        algo.idx = 3
        algo.scope = BunkerScopeID.EXISTING
        algo.emissions = {"co2": _make_emission("co2")}

        options = MagicMock()
        options.solution_tolerance = 1e-6
        algo.options = options

        sp_var = MagicMock()
        sp_var.X = 50.0
        algo.shore_power = {(v, 0): sp_var}

        port = MagicMock()
        port_exp = MagicMock()
        port_exp.get_shore_power_cost.return_value = 20.0
        port_exp.get_shore_power_emission_factor.return_value = 0.05
        port.expectation = port_exp

        route = MagicMock()
        route.ports = [port]

        vessel_profile = MagicMock()
        vessel = MagicMock()
        vessel.name = v
        vessel.route = route
        vessel.profile = vessel_profile

        algo.vessels = {v: vessel}

        transfer_shore_power(algo)

        vessel_profile.add_shore_power_energy.assert_called_once_with(3, 50.0)
        vessel_profile.add_shore_power_expenses.assert_called_once_with(3, 1000.0)
        vessel_profile.add_shore_power_emission.assert_called_once_with("co2", 3, 2.5)

    def test_below_tolerance_skipped(self):
        """Shore power below solution tolerance should not be transferred."""
        from navigate.bunker.bunker_algorithm import BunkerAlgorithm

        algo = BunkerAlgorithm()

        v = "vessel_1"
        algo.idx = 0
        algo.scope = BunkerScopeID.EXISTING
        algo.emissions = {}

        options = MagicMock()
        options.solution_tolerance = 1e-6
        algo.options = options

        sp_var = MagicMock()
        sp_var.X = 1e-9  # below tolerance
        algo.shore_power = {(v, 0): sp_var}

        vessel = MagicMock()
        algo.vessels = {v: vessel}

        transfer_shore_power(algo)

        vessel.profile.add_shore_power_energy.assert_not_called()
        vessel.expectation.add_total_energy.assert_not_called()
