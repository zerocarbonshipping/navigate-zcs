# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests for the carried levelized technology charge (Increment.technology_charter_rate).

Verifies:
  - Levelization identity: discounting the constant charge over its window reproduces
    the NPV of the event's cost flow, for full-lifetime and fractional windows.
  - Retrofit-step annual costs mirror the incremental package cost flows.
  - apply_uptake_transition accumulates the moved-share-weighted annuity.
  - clean_up_multipliers merges the carried rate multiplier-weighted.
  - Fuel conversion carries the rate onto the target vessel type.
  - The cargo charter metrics shift by exactly the technology charge.
"""
from unittest.mock import MagicMock

import numpy as np

from navigate.core import Scalar
from navigate.core.increment import Increment
from navigate.core.node import Node
from navigate.core.nodes.fleet import Fleet
from navigate.core.unit import YEAR_TO_DAYS
from navigate.economics.flows import correct_flow_residual, get_age_flow
from navigate.economics.metric import calculate_net_present_value
from navigate.fleet.charter import (
    _calculate_cargo_unit_properties,
    _calculate_fuel_cost,
    _initialize_vessel_component,
)
from navigate.fleet.conversion import apply_fuel_conversions
from navigate.fleet.evolution import add_newbuilds, clean_up_multipliers
from navigate.fleet.package import (
    Package,
    _trim_flow_to_life,
    annual_costs_for_retrofit_steps,
    levelize_package_cost,
)
from navigate.fleet.technology_adoption import (
    apply_uptake_transition,
    calculate_package_charter_rates,
    define_initial_technology,
    transfer_technology_charter_rate,
)
from navigate.util import YEAR

DISCOUNT = 0.08


def _charge_window_flow(window: float) -> np.ndarray:
    """Operating-year flow the constant charge is recovered over: ones with a prorated final year."""
    flow = get_age_flow(lead_time=0., lifetime=window)
    correct_flow_residual(window, flow)
    return flow


def _make_package(cost_flow: np.ndarray) -> MagicMock:
    package = MagicMock()
    package.cost_flow = cost_flow
    return package


def _example_cost_flow(n: int = 10, capex: float = 100., opex: float = 5.) -> np.ndarray:
    flow = np.full(n, opex)
    flow[0] += capex
    return flow


class TestLevelizePackageCost:
    """The levelized charge conserves NPV over its amortization window."""

    def test_identity_full_window(self):
        flow = _example_cost_flow(n=10)
        rate = levelize_package_cost(flow, window=10., discount_rate=DISCOUNT)

        charge_flow = rate * _charge_window_flow(10.)
        np.testing.assert_almost_equal(calculate_net_present_value(charge_flow, DISCOUNT),
                                       calculate_net_present_value(flow, DISCOUNT))

    def test_identity_fractional_window(self):
        # retrofit with 4.5 years of remaining life: full CAPEX recovered over
        # 4.5 years of charging (the final year prorated), not over 5 whole years
        flow = _example_cost_flow(n=10)
        rate = levelize_package_cost(flow, window=4.5, discount_rate=DISCOUNT)

        charge_flow = rate * _charge_window_flow(4.5)
        trimmed = _trim_flow_to_life(flow, 4.5)
        np.testing.assert_almost_equal(calculate_net_present_value(charge_flow, DISCOUNT),
                                       calculate_net_present_value(trimmed, DISCOUNT))
        np.testing.assert_array_almost_equal(_charge_window_flow(4.5), [1., 1., 1., 1., .5])

    def test_short_window_raises_yearly_charge(self):
        flow = _example_cost_flow(n=10)
        full = levelize_package_cost(flow, window=10., discount_rate=DISCOUNT)
        short = levelize_package_cost(flow, window=5., discount_rate=DISCOUNT)
        assert short > full

    def test_zero_window(self):
        assert levelize_package_cost(_example_cost_flow(), 0., DISCOUNT) == 0.


class TestAnnualCostsForRetrofitSteps:

    def test_stay_option_is_free(self):
        packages = [_make_package(np.zeros(10)), _make_package(_example_cost_flow())]
        annual = annual_costs_for_retrofit_steps(0, packages, remaining=5., discount_rate=DISCOUNT)
        assert annual[0] == 0.

    def test_step_matches_incremental_flow(self):
        flow_a = _example_cost_flow(capex=100.)
        flow_ab = _example_cost_flow(capex=250., opex=12.)
        packages = [_make_package(np.zeros(10)), _make_package(flow_a), _make_package(flow_ab)]

        annual = annual_costs_for_retrofit_steps(1, packages, remaining=5., discount_rate=DISCOUNT)
        expected = levelize_package_cost(flow_ab - flow_a, 5., DISCOUNT)
        np.testing.assert_almost_equal(annual[1], expected)


class TestCalculatePackageCharterRates:

    def test_rates_levelized_over_vessel_lifetime(self):
        vessel = MagicMock()
        vessel.lifetime = Scalar(10.)
        vessel.cost_of_capital = Scalar(DISCOUNT)

        flow = _example_cost_flow(n=10)
        packages = [_make_package(np.zeros(10)), _make_package(flow)]

        rates = calculate_package_charter_rates(packages, vessel)
        np.testing.assert_almost_equal(rates[0], 0.)
        np.testing.assert_almost_equal(rates[1], levelize_package_cost(flow, 10., DISCOUNT))


class TestApplyUptakeTransition:

    def test_moved_share_accumulates_annuity(self):
        fleet = Fleet.__new__(Fleet)
        increment = Increment(multiplier=10., age=5., dt=1.,
                              package_uptake=np.array([1., 0., 0.]))
        fleet.increments = [[increment]]

        choices = np.array([0.5, 0.3, 0.2])
        annual_costs = np.array([0., 10., 25.])
        apply_uptake_transition(fleet, 0, 0, 0, choices, annual_costs)

        np.testing.assert_array_almost_equal(increment.package_uptake, [0.5, 0.3, 0.2])
        np.testing.assert_almost_equal(increment.technology_charter_rate, 0.3 * 10. + 0.2 * 25.)

    def test_partial_current_scales_charge(self):
        fleet = Fleet.__new__(Fleet)
        increment = Increment(multiplier=10., age=5., dt=1.,
                              package_uptake=np.array([0.4, 0.6]),
                              technology_charter_rate=3.)
        fleet.increments = [[increment]]

        apply_uptake_transition(fleet, 0, 0, 0, np.array([0.5, 0.5]), np.array([0., 20.]))

        # only the 0.4 eligible share moves; the carried rate rises by 0.4 * 0.5 * 20
        np.testing.assert_almost_equal(increment.technology_charter_rate, 3. + 0.4 * 0.5 * 20.)


class TestCleanUpMultipliersCharterRate:

    def test_merge_preserves_multiplier_weighted_rate(self):
        fleet = Fleet.__new__(Fleet)
        fleet.assets = [MagicMock()]
        fleet.newbuild_package_uptake = [np.zeros(2)]
        fleet.increments = [[
            Increment(2., 5., 1., package_uptake=np.array([1., 0.]), technology_charter_rate=10.),
            Increment(6., 5., 1., package_uptake=np.array([0., 1.]), technology_charter_rate=30.),
        ]]

        clean_up_multipliers(fleet)

        assert len(fleet.increments[0]) == 1
        merged = fleet.increments[0][0]
        np.testing.assert_almost_equal(merged.multiplier, 8.)
        np.testing.assert_almost_equal(merged.technology_charter_rate, (2. * 10. + 6. * 30.) / 8.)


class TestConversionCarriesCharterRate:

    def test_rate_rides_along(self):
        vessel_a, vessel_b = MagicMock(), MagicMock()
        vessel_a.name = "a"
        vessel_b.name = "b"

        fleet = Fleet.__new__(Fleet)
        fleet.assets = [vessel_a, vessel_b]
        fleet.profile = MagicMock()
        fleet.increments = [[Increment(10., 5., 1., package_uptake=np.array([1., 0.]),
                                       technology_charter_rate=7.)],
                            []]

        timeline = np.arange(3.) * YEAR_TO_DAYS
        fleet.fuel_conversion_expenses = np.zeros_like(timeline)

        proposals = {("a", 0): {"age": 5., "dt": 1.,
                                "costs_per_vessel": {"b": np.array([1.])},
                                "conversions": {"b": 2.}}}
        apply_fuel_conversions(fleet, proposals, idx=0, timeline=timeline)

        converted = fleet.increments[1][0]
        np.testing.assert_almost_equal(converted.multiplier, 2.)
        np.testing.assert_almost_equal(converted.technology_charter_rate, 7.)


class _ShareCurve(Node):
    """Constant age-share curve stub for define_initial_technology."""

    def __init__(self, value: float):
        super().__init__("share")
        self._value = value

    def get(self, age: float) -> float:
        return self._value


def _make_cost_package(technologies: list, cost_flow: np.ndarray) -> Package:
    package = Package(technologies)
    package.cost_flow = cost_flow
    return package


def _make_priced_vessel(name: str) -> MagicMock:
    vessel = MagicMock()
    vessel.name = name
    vessel.lifetime = Scalar(10.)
    vessel.cost_of_capital = Scalar(DISCOUNT)
    return vessel


class TestTransferTechnologyCharterRate:

    def test_multiplier_weighted_average(self):
        vessel = _make_priced_vessel("v0")
        fleet = Fleet.__new__(Fleet)
        fleet.assets = [vessel]
        fleet.increments = [[
            Increment(2., 5., 1., technology_charter_rate=10.),
            Increment(6., 8., 1., technology_charter_rate=30.),
        ]]

        transfer_technology_charter_rate(fleet, idx=4)

        expected = (2. * 10. + 6. * 30.) / 8.
        vessel.expectation.set_technology_charter_rate.assert_called_once_with(4, expected)
        vessel.profile.set_technology_cost.assert_called_once_with(4, expected)

    def test_empty_fleet_is_zero(self):
        vessel = _make_priced_vessel("v0")
        fleet = Fleet.__new__(Fleet)
        fleet.assets = [vessel]
        fleet.increments = [[]]

        transfer_technology_charter_rate(fleet, idx=0)

        vessel.expectation.set_technology_charter_rate.assert_called_once_with(0, 0.)


class TestAddNewbuildsCharterRate:

    def test_newbuild_carries_uptake_weighted_rate(self):
        tech = MagicMock()
        flow = _example_cost_flow(n=10)

        fleet = Fleet.__new__(Fleet)
        fleet.assets = [_make_priced_vessel("v0")]
        fleet.technology_packages = [_make_cost_package([], np.zeros(10)),
                                     _make_cost_package([tech], flow)]
        fleet.newbuild_package_uptake = [np.array([0.75, 0.25])]
        fleet.increments = [[]]

        add_newbuilds(fleet, [3.], time_step=YEAR)

        increment = fleet.increments[0][0]
        expected = 0.25 * levelize_package_cost(flow, 10., DISCOUNT)
        np.testing.assert_almost_equal(increment.technology_charter_rate, expected)
        np.testing.assert_array_almost_equal(increment.package_uptake, [0.75, 0.25])


class TestDefineInitialTechnologySeeding:

    def test_seeded_uptake_charged_as_if_newbuild(self):
        tech = MagicMock()
        tech.name = "t0"
        flow = _example_cost_flow(n=10)

        fleet = Fleet.__new__(Fleet)
        fleet.assets = [_make_priced_vessel("v0")]
        fleet.technologies = [tech]
        fleet.technology_packages = [_make_cost_package([], np.zeros(10)),
                                     _make_cost_package([tech], flow)]
        fleet.increments = [[Increment(5., 3., 1.)]]
        fleet.initial_technology_share = {("v0", "t0"): _ShareCurve(0.4)}

        define_initial_technology(fleet)

        increment = fleet.increments[0][0]
        expected = 0.4 * levelize_package_cost(flow, 10., DISCOUNT)
        np.testing.assert_array_almost_equal(increment.package_uptake, [0.6, 0.4])
        np.testing.assert_almost_equal(increment.technology_charter_rate, expected)


class TestFleetProfileTechnologyExpenses:

    def test_carried_rate_accumulates_multiplier_weighted(self):
        from navigate.fleet.aggregation import calculate_fleet_profile

        vessel = _make_priced_vessel("v0")
        vessel.expectation.get_asset_charter_rate.return_value = 0.5
        vessel.expectation.get_tied_capital.return_value = np.zeros(3)
        vessel.power_system.get_converters.return_value = []

        for getter in ("get_reference_speed", "get_minimum_speed", "get_maximum_speed",
                       "get_actual_speed", "get_optimal_speed", "get_lowest_speed",
                       "get_highest_speed"):
            getattr(vessel.profile, getter).return_value = np.nan

        fleet = Fleet.__new__(Fleet)
        fleet.assets = [vessel]
        fleet.increments = [[Increment(4., 2., 1., technology_charter_rate=12.)]]
        fleet.profile = MagicMock()
        fleet.profile.get_fuel_conversions.return_value = {}
        fleet.fuel_conversion_expenses = np.zeros(4)

        timeline = np.arange(4.) * YEAR
        calculate_fleet_profile(fleet, fuels={}, timeline=timeline, idx=1)

        fleet.profile.add_technology_expenses.assert_called_once_with(12. * 4., 1)


class TestPostProcessTechnologyExpenses:

    def test_technology_series_enters_operating_cost_flow(self):
        from navigate.fleet.post_process import _calculate_total_vessel_operating_expenses

        rate = 2e6
        n = 8
        timeline = np.arange(float(n)) * YEAR_TO_DAYS

        vessel = MagicMock()
        profile = vessel.profile
        profile.get_lifetime.return_value = 3.
        profile.get_lead_time.return_value = 0.
        profile.is_in_fleet.return_value = np.ones(n, dtype=bool)
        profile.get_total_fuel_expenses.return_value = np.zeros(n)
        profile.get_total_levy_expenses.return_value = np.zeros(n)
        profile.get_regulation_expenses.return_value = np.zeros(n)
        profile.get_technology_cost.return_value = np.full(n, rate)

        flow, _year_flow, overlap = _calculate_total_vessel_operating_expenses(vessel, 0, timeline)

        np.testing.assert_array_almost_equal(flow, rate * overlap)


class TestCargoUnitPropertiesTechnologyCharge:

    @staticmethod
    def _freight_rate(technology_rate: float) -> tuple[float, object]:
        timeline = np.arange(0., 15.) * YEAR_TO_DAYS

        vessel = MagicMock()
        vessel.lead_time = Scalar(0.)
        vessel.lifetime = Scalar(10.)
        vessel.cost_of_capital = Scalar(DISCOUNT)

        expectation = vessel.expectation
        expectation.get_asset_charter_npv.return_value = 1e8
        expectation.get_technology_charter_rate.return_value = technology_rate
        expectation.get_total_fuel_expenses.return_value = np.full(timeline.size, 1e6)
        expectation.get_cargo_miles.return_value = np.full(timeline.size, 5e6)

        component = _initialize_vessel_component(vessel, None, time_initial=0.)
        _calculate_fuel_cost(vessel, component, timeline, 0)
        _calculate_cargo_unit_properties(vessel, component, timeline, 0)

        return expectation.set_freight_rate.call_args.args[1], component

    def test_charge_shifts_freight_rate_exactly(self):
        rate = 2e6
        baseline, component = self._freight_rate(0.)
        charged, _ = self._freight_rate(rate)

        from navigate.economics.flows import build_cargo_flow

        age_npv = calculate_net_present_value(component.constant_overlap, DISCOUNT)
        cargo = np.full(int(component.get_length()) + 5, 5e6)
        timeline = np.arange(0., 15.) * YEAR_TO_DAYS
        cargo_flow = build_cargo_flow(component=component, cargo=cargo[:timeline.size], timeline=timeline)
        cargo_npv = calculate_net_present_value(cargo_flow, DISCOUNT)

        np.testing.assert_almost_equal(charged - baseline, rate * age_npv / cargo_npv)

    def test_zero_charge_is_neutral(self):
        baseline, _ = self._freight_rate(0.)
        assert baseline > 0.
