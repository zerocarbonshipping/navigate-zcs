# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Mathematical coherence tests for the Technology → Package → Residual Energy pipeline.

Tests verify the correctness of:
  - Compound savings formula: 1 - prod(1 - s_i)
  - Compound external power: additive across technologies
  - Residual energy: max(raw * (1 - saving) - external, 0)
  - Power ↔ energy round-trip conversions
  - Transfer curve filtering and summation
  - Shore power capacity aggregation
  - Combined savings + external power + transfer through the full pipeline
"""
from unittest.mock import MagicMock

import numpy as np
import pytest

from navigate.calculator.curve import Curve
from navigate.core import Scalar
from navigate.core.enum_ import EnergyDemandTypeID
from navigate.core.unit import MWD_TO_GJ
from navigate.vessel import Technology
from navigate.vessel.package import Package
from navigate.vessel.saving import (
    _calculate_power_transfer,
    _energy_to_power,
    _iterate_legs_or_ports,
    _power_to_energy,
    _raw_to_residual_energy,
)

PROPULSION = EnergyDemandTypeID.PROPULSION
ELECTRICAL = EnergyDemandTypeID.ELECTRICAL
HEAT = EnergyDemandTypeID.HEAT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_technology(name: str, **kwargs) -> Technology:
    """Build and initialize a Technology with optional savings/powers.

    Parameters
    ----------
    name : str
    kwargs :
        energy_saving : dict[EnergyDemandTypeID, float]
        external_power : dict[EnergyDemandTypeID, float]
        shore_power_capacity : float
        power_transfer : dict[tuple[EnergyDemandTypeID, EnergyDemandTypeID], float | Curve]
        capex : float
        opex : float
        lifetime : float
    """
    tech = Technology(name)

    for energy_id, val in kwargs.get('energy_saving', {}).items():
        tech.set_energy_saving(energy_id.name, val)

    for energy_id, val in kwargs.get('external_power', {}).items():
        tech.set_external_power(energy_id.name, val)

    if 'shore_power_capacity' in kwargs:
        tech.set_shore_power_capacity(kwargs['shore_power_capacity'])

    for (src, dst), val in kwargs.get('power_transfer', {}).items():
        tech.set_power_transfer(src.name, dst.name, val)

    if 'capex' in kwargs:
        tech.set_CAPEX(kwargs['capex'])
    if 'opex' in kwargs:
        tech.set_OPEX(kwargs['opex'])
    if 'lifetime' in kwargs:
        tech.set_lifetime(kwargs['lifetime'])

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

    def test_single_technology(self):
        tech = _make_technology('vfd', energy_saving={ELECTRICAL: 0.08})
        pkg = _make_package(tech)
        assert pkg.compound_savings[ELECTRICAL] == pytest.approx(0.08)

    def test_two_technologies_multiplicative(self):
        """4% + 7.5% propulsion savings → 1 - 0.96 * 0.925 = 0.112."""
        t1 = _make_technology('t1', energy_saving={PROPULSION: 0.04})
        t2 = _make_technology('t2', energy_saving={PROPULSION: 0.075})
        pkg = _make_package(t1, t2)
        expected = 1. - (1. - 0.04) * (1. - 0.075)
        assert pkg.compound_savings[PROPULSION] == pytest.approx(expected)

    def test_not_additive(self):
        """Compound savings must be strictly less than the sum of individual savings."""
        t1 = _make_technology('t1', energy_saving={PROPULSION: 0.10})
        t2 = _make_technology('t2', energy_saving={PROPULSION: 0.20})
        pkg = _make_package(t1, t2)
        assert pkg.compound_savings[PROPULSION] < 0.10 + 0.20

    @pytest.mark.parametrize('n', [2, 5, 10, 20])
    def test_n_identical_technologies_converge(self, n):
        """N identical 10% savings → 1 - 0.9^n, approaching 1 as n grows."""
        techs = [_make_technology(f't{i}', energy_saving={PROPULSION: 0.10}) for i in range(n)]
        pkg = _make_package(*techs)
        expected = 1. - 0.9 ** n
        assert pkg.compound_savings[PROPULSION] == pytest.approx(expected)
        assert 0. < pkg.compound_savings[PROPULSION] < 1.

    def test_zero_savings_identity(self):
        """All-zero savings → compound = 0."""
        t1 = _make_technology('t1', energy_saving={PROPULSION: 0.0})
        t2 = _make_technology('t2', energy_saving={PROPULSION: 0.0})
        pkg = _make_package(t1, t2)
        assert pkg.compound_savings[PROPULSION] == pytest.approx(0.0)

    def test_full_saving_absorbing(self):
        """One technology with saving = 1 → compound = 1 regardless of others."""
        t1 = _make_technology('t1', energy_saving={PROPULSION: 0.5})
        t2 = _make_technology('t2', energy_saving={PROPULSION: 1.0})
        pkg = _make_package(t1, t2)
        assert pkg.compound_savings[PROPULSION] == pytest.approx(1.0)

    def test_per_energy_type_independence(self):
        """Propulsion savings don't leak into electrical or heat."""
        tech = _make_technology('t1', energy_saving={PROPULSION: 0.15})
        pkg = _make_package(tech)
        assert pkg.compound_savings[PROPULSION] == pytest.approx(0.15)
        assert pkg.compound_savings[ELECTRICAL] == pytest.approx(0.0)
        assert pkg.compound_savings[HEAT] == pytest.approx(0.0)

    def test_diminishing_marginal_return(self):
        """Second identical technology contributes less marginal saving than the first."""
        s = 0.10
        t1 = _make_technology('t1', energy_saving={PROPULSION: s})
        t2 = _make_technology('t2', energy_saving={PROPULSION: s})

        pkg_one = _make_package(t1)
        pkg_two = _make_package(t1, t2)

        marginal_first = pkg_one.compound_savings[PROPULSION]
        marginal_second = pkg_two.compound_savings[PROPULSION] - pkg_one.compound_savings[PROPULSION]
        assert marginal_second < marginal_first


# ---------------------------------------------------------------------------
# 2. Compound external power
# ---------------------------------------------------------------------------

class TestCompoundPower:
    """Verify: compound_power = sum(power_i), per energy type."""

    def test_single_technology(self):
        tech = _make_technology('kite', external_power={PROPULSION: 1.25})
        pkg = _make_package(tech)
        assert pkg.compound_powers[PROPULSION] == pytest.approx(1.25)

    def test_additive(self):
        t1 = _make_technology('kite', external_power={PROPULSION: 1.25})
        t2 = _make_technology('rotor', external_power={PROPULSION: 2.0})
        pkg = _make_package(t1, t2)
        assert pkg.compound_powers[PROPULSION] == pytest.approx(3.25)

    def test_defaults_to_zero(self):
        tech = _make_technology('vfd', energy_saving={ELECTRICAL: 0.08})
        pkg = _make_package(tech)
        assert pkg.compound_powers[PROPULSION] == pytest.approx(0.0)
        assert pkg.compound_powers[ELECTRICAL] == pytest.approx(0.0)

    def test_per_energy_type_independence(self):
        tech = _make_technology('t1', external_power={PROPULSION: 2.0, ELECTRICAL: 0.5})
        pkg = _make_package(tech)
        assert pkg.compound_powers[PROPULSION] == pytest.approx(2.0)
        assert pkg.compound_powers[ELECTRICAL] == pytest.approx(0.5)
        assert pkg.compound_powers[HEAT] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 3. Residual energy formula
# ---------------------------------------------------------------------------

class TestResidualEnergy:
    """Verify: residual = max(raw * (1 - saving) - external, 0)."""

    def test_passthrough_no_savings_no_external(self):
        raw = np.array([100., 200., 300.])
        result = _raw_to_residual_energy(raw, 0.0, np.array([0., 0., 0.]))
        np.testing.assert_array_almost_equal(result, raw)

    def test_saving_only(self):
        raw = np.array([100., 200.])
        result = _raw_to_residual_energy(raw, 0.20, np.zeros(2))
        np.testing.assert_array_almost_equal(result, [80., 160.])

    def test_external_only(self):
        raw = np.array([100.])
        external = np.array([30.])
        result = _raw_to_residual_energy(raw, 0.0, external)
        np.testing.assert_array_almost_equal(result, [70.])

    def test_combined_saving_then_external(self):
        """Saving is applied first (multiplicative), then external is subtracted."""
        raw = np.array([100.])
        result = _raw_to_residual_energy(raw, 0.20, np.array([10.]))
        # 100 * 0.8 - 10 = 70
        np.testing.assert_array_almost_equal(result, [70.])

    def test_non_negativity_clamp(self):
        """External power exceeding post-saving demand → 0, not negative."""
        raw = np.array([10.])
        result = _raw_to_residual_energy(raw, 0.0, np.array([999.]))
        np.testing.assert_array_almost_equal(result, [0.])

    def test_full_saving(self):
        raw = np.array([1000.])
        result = _raw_to_residual_energy(raw, 1.0, np.zeros(1))
        np.testing.assert_array_almost_equal(result, [0.])

    def test_vectorized(self):
        """Works element-wise on arrays."""
        raw = np.array([100., 200., 300.])
        external = np.array([10., 20., 30.])
        result = _raw_to_residual_energy(raw, 0.10, external)
        expected = np.maximum(raw * 0.9 - external, 0.)
        np.testing.assert_array_almost_equal(result, expected)


# ---------------------------------------------------------------------------
# 4. Power ↔ energy round-trip
# ---------------------------------------------------------------------------

class TestPowerEnergyConversion:
    """Verify inverse relationship and correct unit factor."""

    def test_round_trip(self):
        power = np.array([5.0, 10.0])
        duration = np.array([1.0, 2.0])
        energy = _power_to_energy(power, duration)
        recovered = _energy_to_power(energy, duration)
        np.testing.assert_array_almost_equal(recovered, power)

    def test_unit_factor(self):
        """1 MW for 1 day = MWD_TO_GJ GJ."""
        power = np.array([1.0])
        duration = np.array([1.0])  # 1 day
        energy = _power_to_energy(power, duration)
        np.testing.assert_array_almost_equal(energy, [MWD_TO_GJ])

    def test_mwd_to_gj_value(self):
        """MWD_TO_GJ = 24h * 3600 MJ/MWh * 1e-3 GJ/MJ = 86.4."""
        assert MWD_TO_GJ == pytest.approx(86.4)

    def test_zero_duration(self):
        """Zero duration → zero energy."""
        power = np.array([100.])
        duration = np.array([0.])
        energy = _power_to_energy(power, duration)
        np.testing.assert_array_almost_equal(energy, [0.])


# ---------------------------------------------------------------------------
# 5. Transfer curves
# ---------------------------------------------------------------------------

class TestTransferCurves:
    """Verify Package filters zero-transfer curves and _calculate_power_transfer sums."""

    def test_zero_transfer_filtered_out(self):
        """Technologies with no power transfer produce no transfer_curves entries."""
        tech = _make_technology('vfd', energy_saving={ELECTRICAL: 0.08})
        pkg = _make_package(tech)
        assert pkg.transfer_curves == {}

    def test_non_zero_transfer_collected(self):
        tech = _make_technology('whrs', power_transfer={(PROPULSION, HEAT): 0.3})
        pkg = _make_package(tech)
        assert (PROPULSION, HEAT) in pkg.transfer_curves
        assert len(pkg.transfer_curves[(PROPULSION, HEAT)]) == 1

    def test_multiple_curves_summed(self):
        """Two transfer scalars at the same (src, dst) are summed."""
        load = np.array([0.5, 0.8])
        curves = [Scalar(0.2), Scalar(0.3)]
        result = _calculate_power_transfer(curves, load)
        np.testing.assert_array_almost_equal(result, [0.5, 0.5])

    def test_includes_transfer_flag(self):
        tech_no_transfer = _make_technology('vfd', energy_saving={ELECTRICAL: 0.08})
        tech_transfer = _make_technology('whrs', power_transfer={(PROPULSION, HEAT): 0.3})

        pkg_no = _make_package(tech_no_transfer)
        pkg_yes = _make_package(tech_transfer)

        assert pkg_no.includes_transfer is False
        assert pkg_yes.includes_transfer is True


# ---------------------------------------------------------------------------
# 6. Shore power capacity
# ---------------------------------------------------------------------------

class TestShorePowerCapacity:
    """Verify shore power capacity is additive across technologies."""

    def test_single_technology(self):
        tech = _make_technology('sp', shore_power_capacity=4.0)
        pkg = _make_package(tech)
        assert pkg.shore_power_capacity == pytest.approx(4.0)

    def test_additive(self):
        t1 = _make_technology('sp1', shore_power_capacity=4.0)
        t2 = _make_technology('sp2', shore_power_capacity=2.5)
        pkg = _make_package(t1, t2)
        assert pkg.shore_power_capacity == pytest.approx(6.5)

    def test_defaults_to_zero(self):
        tech = _make_technology('vfd', energy_saving={ELECTRICAL: 0.08})
        pkg = _make_package(tech)
        assert pkg.shore_power_capacity == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 7. Combined pipeline: savings + external power + power transfer
# ---------------------------------------------------------------------------

def _make_mock_vessel(converter_capacities: dict[EnergyDemandTypeID, float]):
    """Build a mock vessel whose only role is to provide converter capacities.

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
    """End-to-end test through _iterate_legs_or_ports with all three saving types.

    Scenario: a vessel with 20 MW propulsion and 5 MW heat converters.
    One leg of 1 day duration.

    Technologies installed:
      - VFD: 10% propulsion energy saving
      - Kite: 0.5 MW external propulsion power
      - WHRS: transfers 0.2 MW from propulsion system to heat system

    Raw demand: 1000 GJ propulsion, 500 GJ heat.

    Expected pipeline per energy type:

    PROPULSION:
      1. External energy = 0.5 MW × 1 day × 86.4 GJ/MWd = 43.2 GJ
      2. Residual = max(1000 × 0.9 - 43.2, 0) = 856.8 GJ

    HEAT:
      1. External energy = 0 (no external heat power)
      2. Residual before transfer = max(500 × 1.0 - 0, 0) = 500 GJ
      3. Propulsion residual power = 856.8 / 86.4 = 9.9167 MW
      4. Converter load = 9.9167 / 20.0 = 0.4958
      5. Transfer power = 0.2 MW (scalar, load-independent)
      6. Transfer energy = 0.2 × 1.0 × 86.4 = 17.28 GJ
      7. Residual after transfer = max(500 - 17.28, 0) = 482.72 GJ
    """

    @pytest.fixture
    def setup(self):
        vfd = _make_technology('vfd', energy_saving={PROPULSION: 0.10})
        kite = _make_technology('kite', external_power={PROPULSION: 0.5})
        whrs = _make_technology('whrs', power_transfer={(PROPULSION, HEAT): 0.2})

        pkg = _make_package(vfd, kite, whrs)

        vessel = _make_mock_vessel({
            PROPULSION: 20.0,
            HEAT: 5.0,
        })

        durations = [np.array([1.0])]  # 1 day
        raw_demands = {
            PROPULSION: [np.array([1000.])],
            HEAT: [np.array([500.])],
        }

        return vessel, pkg, durations, raw_demands

    def test_propulsion_residual(self, setup):
        """Propulsion: 10% saving + 0.5 MW external → 856.8 GJ."""
        vessel, pkg, durations, raw_demands = setup
        result = _iterate_legs_or_ports(vessel, pkg, durations, raw_demands)

        external_energy = 0.5 * 1.0 * MWD_TO_GJ  # 43.2
        expected = 1000. * 0.9 - external_energy   # 856.8
        assert result[PROPULSION][0] == pytest.approx(expected)

    def test_heat_residual_with_transfer(self, setup):
        """Heat: no saving, no external, but 0.2 MW transferred from propulsion → 482.72 GJ."""
        vessel, pkg, durations, raw_demands = setup
        result = _iterate_legs_or_ports(vessel, pkg, durations, raw_demands)

        transfer_energy = 0.2 * 1.0 * MWD_TO_GJ  # 17.28
        expected = 500. - transfer_energy           # 482.72
        assert result[HEAT][0] == pytest.approx(expected)

    def test_all_residuals_non_negative(self, setup):
        """No residual energy should ever go negative."""
        vessel, pkg, durations, raw_demands = setup
        result = _iterate_legs_or_ports(vessel, pkg, durations, raw_demands)
        for energy_id in result:
            for step in result[energy_id]:
                assert np.all(step >= 0.)

    def test_total_energy_reduced(self, setup):
        """Total residual must be strictly less than total raw demand."""
        vessel, pkg, durations, raw_demands = setup
        result = _iterate_legs_or_ports(vessel, pkg, durations, raw_demands)

        total_raw = 1000. + 500.
        total_residual = np.sum(result[PROPULSION][0]) + np.sum(result[HEAT][0])
        assert total_residual < total_raw

    def test_without_transfer_heat_unchanged(self):
        """Without WHRS, heat residual equals raw demand."""
        vfd = _make_technology('vfd', energy_saving={PROPULSION: 0.10})
        kite = _make_technology('kite', external_power={PROPULSION: 0.5})
        pkg = _make_package(vfd, kite)

        vessel = _make_mock_vessel({PROPULSION: 20.0, HEAT: 5.0})
        durations = [np.array([1.0])]
        raw_demands = {
            PROPULSION: [np.array([1000.])],
            HEAT: [np.array([500.])],
        }

        result = _iterate_legs_or_ports(vessel, pkg, durations, raw_demands)
        assert result[HEAT][0] == pytest.approx(500.)

    def test_monotonicity_adding_technology_reduces_energy(self):
        """Adding any technology to a package should never increase residual energy."""
        vfd = _make_technology('vfd', energy_saving={PROPULSION: 0.10})
        kite = _make_technology('kite', external_power={PROPULSION: 0.5})

        pkg_one = _make_package(vfd)
        pkg_two = _make_package(vfd, kite)

        vessel = _make_mock_vessel({PROPULSION: 20.0})
        durations = [np.array([1.0])]
        raw_demands = {PROPULSION: [np.array([1000.])]}

        r1 = _iterate_legs_or_ports(vessel, pkg_one, durations, raw_demands)
        r2 = _iterate_legs_or_ports(vessel, pkg_two, durations, raw_demands)

        assert np.all(r2[PROPULSION][0] <= r1[PROPULSION][0])
