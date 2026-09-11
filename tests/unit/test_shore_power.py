# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests shore power: regulation integration, expected-scope transfer, gate logic."""

from __future__ import annotations

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


def _make_port_expectation(
    shore_ef, shore_cost=0.0, connection_share=1.0, capacity=10.0
):
    """Create a mock port expectation with shore power attributes."""
    exp = MagicMock()
    exp.get_shore_power_emission_factor = lambda emission_name, idx=None: shore_ef.get(
        emission_name, 0.0
    )
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
    reg_exp.get_global_warming_potential = lambda e: gwp.get(e, 1.0)
    reg.expectation = reg_exp

    reg.vessel_threshold = defaultdict(lambda: Scalar(0.0))

    return reg


class TestShoreRegulationCoefficient:
    """Test shore power regulation emission factor and spend coefficient computation."""

    @staticmethod
    def _run(measure, shore_ef, gwp=None, threshold=0.0, has_shore_power=True):
        from navigate.bunker.bunker_algorithm import BunkerAlgorithm

        algo = BunkerAlgorithm()

        v = "vessel_1"
        r = "reg_1"
        algo.idx = 0
        algo.scope = BunkerScopeID.EXISTING
        algo.emissions = {name: _make_emission(name) for name in shore_ef}
        algo.shore_power = {(v, 0): MagicMock()} if has_shore_power else {}

        port = MagicMock()
        port.expectation = _make_port_expectation(shore_ef=shore_ef)

        route = MagicMock()
        route.ports = [port]

        vessel = MagicMock()
        vessel.name = v
        vessel.route = route
        vessel.power_system.get_converters.return_value = ()

        regulation = _make_regulation(
            name=r,
            measure=measure,
            emissions=[_make_emission(name) for name in shore_ef],
            gwp=gwp,
        )
        if threshold:
            regulation.vessel_threshold = defaultdict(lambda: Scalar(threshold))

        algo.active_regulations = {r: regulation}
        algo.effective_lhv = {}
        algo.regulation_emission_factor = {}
        algo.regulation_spend_coefficient = {}
        algo.shore_power_regulation_emission_factor = {}
        algo.shore_power_regulation_coefficient = {}

        calculate_regulation_coefficients(algo, vessel)

        return algo, (v, 0, r)

    @pytest.mark.parametrize(
        "measure, shore_ef, gwp, threshold, has_shore_power, "
        "expected_ef, expected_coeff",
        [
            # ABSOLUTE: coefficient equals the emission factor, no threshold subtraction
            pytest.param(
                RegulationMeasureID.ABSOLUTE,
                {"co2": 0.05},
                None,
                0.0,
                True,
                0.05,
                0.05,
                id="absolute_equals_emission_factor",
            ),
            # INTENSITY: threshold / TON_TO_KG * 1.0 is subtracted from the emission
            # factor
            pytest.param(
                RegulationMeasureID.INTENSITY,
                {"co2": 0.05},
                None,
                10.0,
                True,
                0.05,
                0.05 - 10.0 / TON_TO_KG * 1.0,
                id="intensity_subtracts_threshold",
            ),
            # co2: 0.05 * 1.0 + ch4: 0.001 * 28.0 = 0.078
            pytest.param(
                RegulationMeasureID.ABSOLUTE,
                {"co2": 0.05, "ch4": 0.001},
                {"co2": 1.0, "ch4": 28.0},
                0.0,
                True,
                0.05 * 1.0 + 0.001 * 28.0,
                None,
                id="gwp_conversion_applied",
            ),
            # ports without a shore power variable get no regulation coefficient
            pytest.param(
                RegulationMeasureID.ABSOLUTE,
                {"co2": 0.05},
                None,
                0.0,
                False,
                None,
                None,
                id="no_shore_power_no_coefficient",
            ),
        ],
    )
    def test_regulation_coefficient(
        self,
        measure,
        shore_ef,
        gwp,
        threshold,
        has_shore_power,
        expected_ef,
        expected_coeff,
    ):
        algo, key = self._run(
            measure,
            shore_ef,
            gwp=gwp,
            threshold=threshold,
            has_shore_power=has_shore_power,
        )

        if not has_shore_power:
            assert key not in algo.shore_power_regulation_emission_factor
            assert key not in algo.shore_power_regulation_coefficient
            return

        assert algo.shore_power_regulation_emission_factor[key] == pytest.approx(
            expected_ef
        )
        if expected_coeff is not None:
            assert algo.shore_power_regulation_coefficient[key] == pytest.approx(
                expected_coeff
            )


class TestShoreTransferExpected:
    """Test shore power transfer for expected scope."""

    def test_expected_scope_transfers_energy_and_cost(self):
        """Expected scope transfers shore power energy/cost to vessel expectation."""
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
        """Existing scope transfers shore power to vessel profile (not expectation)."""
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

        vessel_profile.add_shore_power_energy.assert_called_once_with(50.0, 3)
        vessel_profile.add_shore_power_expenses.assert_called_once_with(1000.0, 3)
        vessel_profile.add_shore_power_emission.assert_called_once_with("co2", 2.5, 3)

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
