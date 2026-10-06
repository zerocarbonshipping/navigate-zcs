# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the Technology → Package → Residual Energy pipeline.

Tests verify:
  - Compound savings formula: 1 - prod(1 - s_i)
  - Residual energy: max(raw * (1 - saving) - external, 0)
  - Transfer curve filtering and summation
  - Combined savings + external power + transfer through the full pipeline
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from navigate.core import Scalar
from navigate.core.enum_ import EnergyDemandTypeID
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.technology import Technology
from navigate.core.nodes.variable import Variable
from navigate.core.table_data import TableData
from navigate.core.unit import MWD_TO_GJ
from navigate.fleet.package import Package
from navigate.fleet.residual_energy import (
    _calculate_power_transfer,
    _iterate_legs_or_ports,
    _raw_to_residual_energy,
)

PROPULSION = EnergyDemandTypeID.PROPULSION
ELECTRICAL = EnergyDemandTypeID.ELECTRICAL
HEAT = EnergyDemandTypeID.HEAT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_technology(name: str, **kwargs) -> Technology:
    """
    Build and initialize a Technology with optional savings/powers.

    Parameters
    ----------
    name : str
        Name of the technology node.
    kwargs :
        energy_saving : dict[EnergyDemandTypeID, float]
        external_power : dict[EnergyDemandTypeID, float]
        shore_power_capacity : float
        power_transfer :
            dict[tuple[EnergyDemandTypeID, EnergyDemandTypeID], float | Curve]
        capex : float
        opex : float
        lifetime : float
    """
    tech = Technology(name)

    for energy_id, val in kwargs.get("energy_saving", {}).items():
        tech.set_energy_saving(energy_id.name, val)

    for energy_id, val in kwargs.get("external_power", {}).items():
        tech.set_external_power(energy_id.name, val)

    if "shore_power_capacity" in kwargs:
        tech.set_shore_power_capacity(kwargs["shore_power_capacity"])

    for (src, dst), val in kwargs.get("power_transfer", {}).items():
        tech.set_power_transfer(src.name, dst.name, val)

    if "capex" in kwargs:
        tech.set_capex(kwargs["capex"])
    if "opex" in kwargs:
        tech.set_opex(kwargs["opex"])
    if "lifetime" in kwargs:
        tech.set_lifetime(kwargs["lifetime"])

    tech.initialize()
    return tech


def _make_package(*technologies: Technology) -> Package:
    """Build a Package and precompute compound state."""
    pkg = Package(list(technologies))
    pkg.precompute()
    return pkg


# ---------------------------------------------------------------------------
# 1. Compound savings formula
# ---------------------------------------------------------------------------


class TestCompoundSavings:
    """Verify: compound_saving = 1 - prod(1 - s_i), per energy type."""

    @pytest.mark.parametrize(
        ("savings", "expected"),
        [
            # 4% + 7.5% → 1 - 0.96 * 0.925 = 0.112, not the additive 0.115
            ([0.04, 0.075], 1.0 - (1.0 - 0.04) * (1.0 - 0.075)),
            # one technology with saving = 1 absorbs: compound = 1 regardless of others
            ([0.5, 1.0], 1.0),
        ],
    )
    def test_compound_value(self, savings, expected):
        techs = [
            _make_technology(f"t{i}", energy_saving={PROPULSION: s})
            for i, s in enumerate(savings)
        ]
        pkg = _make_package(*techs)
        assert pkg.compound_savings[PROPULSION] == pytest.approx(expected)


# ---------------------------------------------------------------------------
# 2. Residual energy formula
# ---------------------------------------------------------------------------


class TestResidualEnergy:
    """Verify: residual = max(raw * (1 - saving) - external, 0)."""

    @pytest.mark.parametrize(
        ("raw", "saving", "external", "expected"),
        [
            # saving is applied first (multiplicative), then external is subtracted:
            # 100 * 0.8 - 10 = 70
            ([100.0], 0.20, [10.0], [70.0]),
            # external power exceeding post-saving demand → 0, not negative
            ([10.0], 0.0, [999.0], [0.0]),
        ],
    )
    def test_residual(self, raw, saving, external, expected):
        result = _raw_to_residual_energy(np.array(raw), saving, np.array(external))
        np.testing.assert_array_almost_equal(result, expected)


# ---------------------------------------------------------------------------
# 3. Transfer curves
# ---------------------------------------------------------------------------


class TestTransferCurves:
    """Verify Package filters zero-transfer curves; _calculate_power_transfer sums."""

    def test_package_collects_only_non_zero_transfers(self):
        """A technology without power transfer adds no transfer_curves entry."""
        pkg_no = _make_package(
            _make_technology("vfd", energy_saving={ELECTRICAL: 0.08})
        )
        pkg_yes = _make_package(
            _make_technology("whrs", power_transfer={(PROPULSION, HEAT): 0.3})
        )

        assert pkg_no.transfer_curves == {}
        assert pkg_no.includes_transfer is False
        assert list(pkg_yes.transfer_curves) == [(PROPULSION, HEAT)]
        assert len(pkg_yes.transfer_curves[(PROPULSION, HEAT)]) == 1
        assert pkg_yes.includes_transfer is True

    def test_curve_and_variable_transfer_summed(self):
        """
        A Curve and a Variable transferring the same pair sum without a shape crash.

        Through the real path (Technology.set_power_transfer -> Package.precompute ->
        _calculate_power_transfer): a Variable's getter used to ignore the array load
        and answer a bare float, while the Curve's answered one value per load point.
        Stacking the two into one array to sum them then raised
        "setting an array element with a sequence" for any pair more than one
        technology contributes to.
        """
        curve = Curve("whrs_curve")
        curve.set_table(TableData(rows=[[0.0, 0.0], [1.0, 1.0]]))  # identity: y = x
        curve.build_table()

        variable = Variable("whrs_variable")
        variable.set_value(0.3)

        t_curve = _make_technology(
            "t_curve", power_transfer={(PROPULSION, HEAT): curve}
        )
        t_variable = _make_technology(
            "t_variable", power_transfer={(PROPULSION, HEAT): variable}
        )
        pkg = _make_package(t_curve, t_variable)

        load = np.array([0.5, 0.8])
        result = _calculate_power_transfer(
            pkg.transfer_curves[(PROPULSION, HEAT)], load
        )
        # curve(load) = load itself (identity table): [0.5, 0.8]; the variable is
        # a constant 0.3, broadcast to load's shape: [0.3, 0.3]
        np.testing.assert_array_almost_equal(result, [0.8, 1.1])


# ---------------------------------------------------------------------------
# 4. Combined pipeline: savings + external power + power transfer
# ---------------------------------------------------------------------------


def _make_mock_vessel(converter_capacities: dict[EnergyDemandTypeID, float]):
    """
    Build a mock vessel whose only role is to provide converter capacities.

    Parameters
    ----------
    converter_capacities
        Mapping from energy demand type to converter power capacity in MW.
    """
    vessel = MagicMock()
    power_system = MagicMock()

    def get_converter(energy_id):
        converter = MagicMock()
        capacity = Scalar(converter_capacities[energy_id])
        converter.power_capacity = capacity
        return converter

    power_system.get_converter_by_energy_type.side_effect = get_converter
    vessel.power_system = power_system
    return vessel


class TestCombinedResidualEnergy:
    """
    End-to-end test through _iterate_legs_or_ports with all three saving types.

    Scenario: a vessel with 20 MW propulsion and 5 MW heat converters.
    One leg of 1 day duration.

    Technologies installed:
      - VFD: 10% propulsion energy saving
      - Kite: 0.5 MW external propulsion power
      - WHRS: transfers 0.2 MW from propulsion system to heat system

    Raw demand: 1000 GJ propulsion, 500 GJ heat.

    Expected pipeline per energy type:

    PROPULSION:
      1. External energy = 0.5 MW * 1 day * 86.4 GJ/MWd = 43.2 GJ
      2. Residual = max(1000 * 0.9 - 43.2, 0) = 856.8 GJ

    HEAT:
      1. External energy = 0 (no external heat power)
      2. Residual before transfer = max(500 * 1.0 - 0, 0) = 500 GJ
      3. Propulsion residual power = 856.8 / 86.4 = 9.9167 MW
      4. Converter load = 9.9167 / 20.0 = 0.4958
      5. Transfer power = 0.2 MW (scalar, load-independent)
      6. Transfer energy = 0.2 * 1.0 * 86.4 = 17.28 GJ
      7. Residual after transfer = max(500 - 17.28, 0) = 482.72 GJ
    """

    @pytest.fixture
    def setup(self):
        vfd = _make_technology("vfd", energy_saving={PROPULSION: 0.10})
        kite = _make_technology("kite", external_power={PROPULSION: 0.5})
        whrs = _make_technology("whrs", power_transfer={(PROPULSION, HEAT): 0.2})

        pkg = _make_package(vfd, kite, whrs)

        vessel = _make_mock_vessel(
            {
                PROPULSION: 20.0,
                HEAT: 5.0,
            }
        )

        durations = [np.array([1.0])]  # 1 day
        raw_demands = {
            PROPULSION: [np.array([1000.0])],
            HEAT: [np.array([500.0])],
        }

        return vessel, pkg, durations, raw_demands

    def test_propulsion_residual(self, setup):
        """Propulsion: 10% saving + 0.5 MW external → 856.8 GJ."""
        vessel, pkg, durations, raw_demands = setup
        result = _iterate_legs_or_ports(vessel, pkg, durations, raw_demands)

        external_energy = 0.5 * 1.0 * MWD_TO_GJ  # 43.2
        expected = 1000.0 * 0.9 - external_energy  # 856.8
        assert result[PROPULSION][0] == pytest.approx(expected)

    def test_heat_residual_with_transfer(self, setup):
        """Heat: no saving/external, 0.2 MW transferred from propulsion → 482.72 GJ."""
        vessel, pkg, durations, raw_demands = setup
        result = _iterate_legs_or_ports(vessel, pkg, durations, raw_demands)

        transfer_energy = 0.2 * 1.0 * MWD_TO_GJ  # 17.28
        expected = 500.0 - transfer_energy  # 482.72
        assert result[HEAT][0] == pytest.approx(expected)
