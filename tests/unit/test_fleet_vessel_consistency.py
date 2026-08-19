# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import MagicMock

import numpy as np
import pytest

from navigate.core.enum_ import FuelTypeID
from navigate.core.profiles.fleet_profile import FleetProfile
from navigate.core.profiles.vessel_profile import VesselProfile


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _fuel(lhv: float = 41.2, rho: float = 0.9, fuel_type: FuelTypeID = FuelTypeID.OIL):
    f = MagicMock()
    f.fuel_type = fuel_type
    f.lower_heating_value.get.return_value = lhv
    f.mass_density.get.return_value = rho
    return f


def _emission(gwp: float = 1.0):
    e = MagicMock()
    e.global_warming_potential.get.return_value = gwp
    return e


def _make_vessel_profile(timeline, fuels, emissions):
    p = VesselProfile()
    p.initialize(timeline=timeline, emissions=emissions, fuels=fuels,
                 emissions_lifetime=100.)
    return p


def _make_fleet_profile(timeline, fuels, emissions, vessel_names, technology_names=()):
    p = FleetProfile()
    p.initialize(timeline=timeline, vessel_names=vessel_names,
                 technology_names=list(technology_names), fuels=fuels,
                 emissions=emissions, emissions_lifetime=100.)
    return p


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def timeline():
    return np.array([0.0, 1.0])


@pytest.fixture
def fuels():
    return {"lsfo": _fuel(lhv=41.2, rho=0.9)}


@pytest.fixture
def emissions():
    return {"co2": _emission(gwp=1.0)}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFleetAggregationConsistency:
    """Fleet-level totals == sum_v(vessel_total * multiplier_v)."""

    def test_total_equivalent_wtw(self, timeline, fuels, emissions):
        v1 = _make_vessel_profile(timeline, fuels, emissions)
        v1._WTT[("lsfo", "co2")][0] = 2.0
        v1._TTW[("lsfo", "co2")][0] = 5.0

        v2 = _make_vessel_profile(timeline, fuels, emissions)
        v2._WTT[("lsfo", "co2")][0] = 3.0
        v2._TTW[("lsfo", "co2")][0] = 4.0

        fleet = _make_fleet_profile(timeline, fuels, emissions, vessel_names=["v1", "v2"])
        fleet.add_fuel_consumer_profile(v1, multiplier=50.0, idx=0)
        fleet.add_fuel_consumer_profile(v2, multiplier=30.0, idx=0)

        expected = (50.0 * v1.get_total_equivalent_WTW(0)
                    + 30.0 * v2.get_total_equivalent_WTW(0))
        assert fleet.get_total_equivalent_WTW(0) == pytest.approx(expected)
        # closed-form: 50*(2+5) + 30*(3+4) = 560
        assert fleet.get_total_equivalent_WTW(0) == pytest.approx(560.0)

    def test_consumed_energy(self, timeline, fuels, emissions):
        v1 = _make_vessel_profile(timeline, fuels, emissions)
        v1._consumed_mass["lsfo"][0] = 100.0

        v2 = _make_vessel_profile(timeline, fuels, emissions)
        v2._consumed_mass["lsfo"][0] = 250.0

        fleet = _make_fleet_profile(timeline, fuels, emissions, vessel_names=["v1", "v2"])
        fleet.add_fuel_consumer_profile(v1, multiplier=50.0, idx=0)
        fleet.add_fuel_consumer_profile(v2, multiplier=30.0, idx=0)

        expected = (50.0 * v1.get_consumed_energy("lsfo", 0)
                    + 30.0 * v2.get_consumed_energy("lsfo", 0))
        assert fleet.get_consumed_energy("lsfo", 0) == pytest.approx(expected)
        # closed-form: (50*100 + 30*250) * lhv(41.2) = 12500 * 41.2
        assert fleet.get_consumed_energy("lsfo", 0) == pytest.approx(515_000.0)

    def test_multiplier_is_applied(self, timeline, fuels, emissions):
        # Guards against the specific failure mode where aggregation ignores
        # the multiplier: the historical 31 % gap would have been masked if
        # either side of the comparison dropped `multiplier` to 1.
        v = _make_vessel_profile(timeline, fuels, emissions)
        v._WTT[("lsfo", "co2")][0] = 10.0
        v._TTW[("lsfo", "co2")][0] = 20.0

        fleet = _make_fleet_profile(timeline, fuels, emissions, vessel_names=["v"])
        fleet.add_fuel_consumer_profile(v, multiplier=100.0, idx=0)

        assert fleet.get_total_equivalent_WTW(0) == pytest.approx(3000.0)

    def test_idx_is_applied(self, timeline, fuels, emissions):
        # Aggregation must only touch the requested idx; other steps stay zero.
        v = _make_vessel_profile(timeline, fuels, emissions)
        v._WTT[("lsfo", "co2")][0] = 1.0
        v._WTT[("lsfo", "co2")][1] = 7.0

        fleet = _make_fleet_profile(timeline, fuels, emissions, vessel_names=["v"])
        fleet.add_fuel_consumer_profile(v, multiplier=10.0, idx=0)

        wtw = fleet.get_total_equivalent_WTW()
        assert wtw[0] == pytest.approx(10.0)
        assert wtw[1] == pytest.approx(0.0)


class TestFleetTechnologyUptake:
    """get_fleet_technology_uptake == existing-vessel-weighted average."""

    @pytest.fixture
    def fleet(self, timeline, fuels, emissions):
        p = _make_fleet_profile(timeline, fuels, emissions,
                                vessel_names=["v1", "v2"], technology_names=["tech"])
        p._technology_uptake[("v1", "tech")][:] = [0.8, 0.5]
        p._technology_uptake[("v2", "tech")][:] = [0.4, 0.1]
        p._existing_vessels["v1"][:] = [3.0, 0.0]
        p._existing_vessels["v2"][:] = [1.0, 0.0]
        return p

    def test_weighted_average(self, fleet):
        # closed-form: (0.8*3 + 0.4*1) / (3 + 1) = 0.7
        assert fleet.get_fleet_technology_uptake("tech")[0] == pytest.approx(0.7)

    def test_empty_fleet_step_is_zero(self, fleet):
        assert fleet.get_fleet_technology_uptake("tech")[1] == 0.0

    def test_dict_form_and_idx(self, fleet):
        uptake = fleet.get_fleet_technology_uptake()
        assert list(uptake) == ["tech"]
        np.testing.assert_allclose(uptake["tech"], [0.7, 0.0])
        assert fleet.get_fleet_technology_uptake("tech", 0) == pytest.approx(0.7)

    def test_no_technologies(self, timeline, fuels, emissions):
        fleet = _make_fleet_profile(timeline, fuels, emissions, vessel_names=["v"])
        assert fleet.get_fleet_technology_uptake() == {}

    def test_no_vessels_is_timeline_shaped_zero(self, timeline, fuels, emissions):
        fleet = _make_fleet_profile(timeline, fuels, emissions, vessel_names=[],
                                    technology_names=["tech"])
        np.testing.assert_array_equal(fleet.get_fleet_technology_uptake("tech"),
                                      np.zeros_like(timeline))


class TestScrapNewbuildAccumulation:

    def test_writers_accumulate_per_vessel(self, timeline, fuels, emissions):
        fleet = _make_fleet_profile(timeline, fuels, emissions, vessel_names=["a", "b"])

        fleet.add_scrap("a", 0, 1.5)
        fleet.add_scrap("a", 0, 0.5)
        fleet.add_newbuilds("a", 1, 2.0)
        fleet.add_newbuilds("a", 1, 3.0)

        assert fleet.get_scrap("a", 0) == pytest.approx(2.0)
        assert fleet.get_newbuilds("a", 1) == pytest.approx(5.0)
        np.testing.assert_array_equal(fleet.get_scrap("b"), np.zeros_like(timeline))
        np.testing.assert_array_equal(fleet.get_newbuilds("b"), np.zeros_like(timeline))


class TestShorePowerAccounting:

    def _make_profile(self, timeline, fuels, emissions, shore=False):
        p = _make_vessel_profile(timeline, fuels, emissions)
        p.add_consumed_mass("lsfo", 10.0, 0)
        p.add_fuel_expenses("lsfo", 100.0, 0)
        p.add_WTT("lsfo", "co2", 2.0, 0)
        p.add_TTW("lsfo", "co2", 3.0, 0)
        if shore:
            p.add_shore_power_energy(0, 50.0)
            p.add_shore_power_expenses(0, 25.0)
            p.add_shore_power_emission("co2", 0, 4.0)
        return p

    @pytest.fixture
    def base(self, timeline, fuels, emissions):
        return self._make_profile(timeline, fuels, emissions)

    @pytest.fixture
    def vessel(self, timeline, fuels, emissions):
        return self._make_profile(timeline, fuels, emissions, shore=True)

    def test_totals_include_shore_power(self, base, vessel):
        assert vessel.get_total_consumed_energy(0) == pytest.approx(base.get_total_consumed_energy(0) + 50.0)
        assert vessel.get_total_fuel_expenses(0) == pytest.approx(base.get_total_fuel_expenses(0) + 25.0)
        assert vessel.get_total_fuel_related_expenses(0) == pytest.approx(
            base.get_total_fuel_related_expenses(0) + 25.0)

    def test_per_fuel_dicts_stay_fuel_only(self, vessel):
        assert set(vessel.get_consumed_energy()) == {"lsfo"}
        assert set(vessel.get_fuel_expenses()) == {"lsfo"}
        assert vessel.get_fuel_expenses("lsfo", 0) == pytest.approx(100.0)

    def test_equivalent_WTW_family_includes_shore_power(self, vessel):
        # gwp = 1: fuel WTW = 2 + 3, shore = 4
        assert vessel.get_total_equivalent_WTW(0) == pytest.approx(9.0)
        assert vessel.get_total_equivalent_WTT(0) == pytest.approx(2.0)
        assert vessel.get_total_equivalent_TTW(0) == pytest.approx(3.0)

    def test_cumulative_and_intensity_variants_track_widened_total(self, vessel):
        np.testing.assert_allclose(vessel.get_cumulative_total_equivalent_WTW(),
                                   vessel._to_cumulative(vessel.get_total_equivalent_WTW()))
        np.testing.assert_allclose(vessel.get_cumulative_total_fuel_expenses(),
                                   vessel._to_cumulative(vessel.get_total_fuel_expenses()))
        np.testing.assert_allclose(vessel.get_cumulative_total_fuel_related_expenses(),
                                   vessel._to_cumulative(vessel.get_total_fuel_related_expenses()))
        # 9 ton -> g over (462 GJ -> MJ): 9e6 / 462e3
        assert vessel.get_intensity_total_equivalent_WTW()[0] == pytest.approx(9.0e6 / 462.0e3)
        # WTT/TTW numerators stay fuel-only over the shore-inclusive denominator
        assert vessel.get_intensity_total_equivalent_WTT()[0] == pytest.approx(2.0e6 / 462.0e3)
        assert vessel.get_intensity_total_equivalent_TTW()[0] == pytest.approx(3.0e6 / 462.0e3)
        np.testing.assert_allclose(
            vessel.get_cumulative_intensity_total_equivalent_WTW(),
            vessel._convert_to_intensity(vessel.get_total_equivalent_WTW(),
                                         vessel.get_total_consumed_energy(), cumulative=True))

    def test_propagates_via_fuel_consumer_merge(self, timeline, fuels, emissions, vessel):
        fleet = _make_fleet_profile(timeline, fuels, emissions, vessel_names=["v"])
        fleet.add_fuel_consumer_profile(vessel, 3.0, 0)

        assert fleet.get_shore_power_energy(0) == pytest.approx(150.0)
        assert fleet.get_shore_power_expenses(0) == pytest.approx(75.0)
        assert fleet.get_shore_power_emission("co2", 0) == pytest.approx(12.0)

        # the widened totals include the propagated shore power at fleet level
        assert fleet.get_total_equivalent_WTW(0) == pytest.approx(3.0 * 9.0)
        assert fleet.get_total_consumed_energy(0) == pytest.approx(3.0 * 462.0)
        assert fleet.get_total_fuel_expenses(0) == pytest.approx(3.0 * 125.0)

    def test_manager_merge_counts_shore_power_once(self, timeline, fuels, emissions, vessel):
        fleet = _make_fleet_profile(timeline, fuels, emissions, vessel_names=["v"])
        fleet.add_fuel_consumer_profile(vessel, 1.0, 0)

        # stand-in for the manager: mirrors manager.py calling both merge methods
        manager = _make_fleet_profile(timeline, fuels, emissions, vessel_names=["v"])
        manager.add_fuel_consumer_profile(fleet)
        manager.add_vessel_aggregate_profile(fleet)

        assert manager.get_shore_power_energy(0) == pytest.approx(50.0)
        assert manager.get_shore_power_expenses(0) == pytest.approx(25.0)
        assert manager.get_shore_power_emission("co2", 0) == pytest.approx(4.0)
