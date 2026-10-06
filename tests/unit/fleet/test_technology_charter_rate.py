# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the levelized technology charge (VesselIncrement.technology_charter_rate).

Verifies:
  - Levelization identity: discounting the constant charge over its window reproduces
    the NPV of the event's cost flow, for full-lifetime and fractional windows.
  - Retrofit-step annual costs mirror the incremental package cost flows.
  - _apply_retrofits accumulates the moved-share-weighted annuity.
  - clean_up_multipliers merges the carried rate multiplier-weighted.
  - Newbuilds and the seeded initial technology carry the uptake-weighted rate.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from navigate.core import Scalar
from navigate.core.increment import VesselIncrement
from navigate.core.node import Node
from navigate.core.node_type import CURVE
from navigate.core.nodes.fleet import Fleet
from navigate.economics.flows import (
    correct_flow_residual,
    get_age_flow,
    trim_flow_to_lifetime,
)
from navigate.economics.metric import calculate_net_present_value
from navigate.fleet.evolution import clean_up_multipliers
from navigate.fleet.package import (
    Package,
    annual_costs_for_retrofit_steps,
    levelize_package_cost,
)
from navigate.fleet.planning import add_newbuilds
from navigate.fleet.technology_adoption import (
    _apply_retrofits,
    _RetrofitProposal,
    define_initial_technology,
)
from navigate.util import YEAR

DISCOUNT = 0.08


def _charge_window_flow(window: float) -> np.ndarray:
    """Operating-year flow the charge recovers over: ones with a prorated final year."""
    flow = get_age_flow(lead_time=0.0, lifetime=window)
    correct_flow_residual(window, flow)
    return flow


def _make_package(cost_flow: np.ndarray) -> MagicMock:
    package = MagicMock()
    package.cost_flow = cost_flow
    return package


def _example_cost_flow(
    n: int = 10, capex: float = 100.0, opex: float = 5.0
) -> np.ndarray:
    flow = np.full(n, opex)
    flow[0] += capex
    return flow


class TestLevelizePackageCost:
    """The levelized charge conserves NPV over its amortization window."""

    @pytest.mark.parametrize(
        "window",
        [
            10.0,
            # retrofit with 4.5 years of remaining life: full CAPEX recovered over
            # 4.5 years of charging (the final year prorated), not over 5 whole years
            4.5,
        ],
    )
    def test_identity(self, window):
        flow = _example_cost_flow(n=10)
        rate = levelize_package_cost(flow, window=window, discount_rate=DISCOUNT)

        charge_flow = rate * _charge_window_flow(window)
        np.testing.assert_almost_equal(
            calculate_net_present_value(charge_flow, DISCOUNT),
            calculate_net_present_value(trim_flow_to_lifetime(flow, window), DISCOUNT),
        )


class TestAnnualCostsForRetrofitSteps:
    def test_step_matches_incremental_flow(self):
        flow_a = _example_cost_flow(capex=100.0)
        flow_ab = _example_cost_flow(capex=250.0, opex=12.0)
        packages = [
            _make_package(np.zeros(10)),
            _make_package(flow_a),
            _make_package(flow_ab),
        ]

        annual = annual_costs_for_retrofit_steps(
            1, packages, remaining=5.0, discount_rate=DISCOUNT
        )
        expected = levelize_package_cost(flow_ab - flow_a, 5.0, DISCOUNT)
        np.testing.assert_almost_equal(annual[1], expected)
        # staying at the current package costs nothing
        assert annual[0] == 0.0


class TestApplyRetrofits:
    def test_moved_share_accumulates_annuity(self):
        increment = VesselIncrement(
            multiplier=10.0,
            age=5.0,
            age_span=1.0,
            package_uptake=np.array([1.0, 0.0, 0.0]),
        )

        choices = np.array([0.5, 0.3, 0.2])
        annual_costs = np.array([0.0, 10.0, 25.0])
        _apply_retrofits(
            [_RetrofitProposal(0, increment, 0, choices, 1.0, annual_costs)]
        )

        np.testing.assert_array_almost_equal(increment.package_uptake, [0.5, 0.3, 0.2])
        np.testing.assert_almost_equal(
            increment.technology_charter_rate, 0.3 * 10.0 + 0.2 * 25.0
        )

    def test_partial_current_scales_charge(self):
        increment = VesselIncrement(
            multiplier=10.0,
            age=5.0,
            age_span=1.0,
            package_uptake=np.array([0.4, 0.6]),
            technology_charter_rate=3.0,
        )

        _apply_retrofits(
            [
                _RetrofitProposal(
                    0, increment, 0, np.array([0.5, 0.5]), 0.4, np.array([0.0, 20.0])
                )
            ]
        )

        # only the 0.4 eligible share moves; the carried rate rises by 0.4 * 0.5 * 20
        np.testing.assert_almost_equal(
            increment.technology_charter_rate, 3.0 + 0.4 * 0.5 * 20.0
        )


class TestCleanUpMultipliersCharterRate:
    def test_merge_preserves_multiplier_weighted_rate(self):
        fleet = Fleet.__new__(Fleet)
        fleet.assets = [MagicMock()]
        fleet.newbuild_package_uptake = [np.zeros(2)]
        fleet.increments = [
            [
                VesselIncrement(
                    2.0,
                    5.0,
                    1.0,
                    package_uptake=np.array([1.0, 0.0]),
                    technology_charter_rate=10.0,
                ),
                VesselIncrement(
                    6.0,
                    5.0,
                    1.0,
                    package_uptake=np.array([0.0, 1.0]),
                    technology_charter_rate=30.0,
                ),
            ]
        ]

        clean_up_multipliers(fleet)

        assert len(fleet.increments[0]) == 1
        merged = fleet.increments[0][0]
        np.testing.assert_almost_equal(merged.multiplier, 8.0)
        np.testing.assert_almost_equal(
            merged.technology_charter_rate, (2.0 * 10.0 + 6.0 * 30.0) / 8.0
        )


class _ShareCurve(Node):
    """Constant age-share curve stub for define_initial_technology."""

    def __init__(self, value: float):
        super().__init__("share", CURVE)
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
    vessel.lifetime = Scalar(10.0)
    vessel.cost_of_capital = Scalar(DISCOUNT)
    return vessel


class TestAddNewbuildsCharterRate:
    def test_newbuild_carries_uptake_weighted_rate(self):
        tech = MagicMock()
        flow = _example_cost_flow(n=10)

        fleet = Fleet.__new__(Fleet)
        fleet.assets = [_make_priced_vessel("v0")]
        fleet.technology_packages = [
            _make_cost_package([], np.zeros(10)),
            _make_cost_package([tech], flow),
        ]
        fleet.newbuild_package_uptake = [np.array([0.75, 0.25])]
        fleet.increments = [[]]

        add_newbuilds(fleet, np.array([3.0]), time_step=YEAR)

        increment = fleet.increments[0][0]
        expected = 0.25 * levelize_package_cost(flow, 10.0, DISCOUNT)
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
        fleet.technology_packages = [
            _make_cost_package([], np.zeros(10)),
            _make_cost_package([tech], flow),
        ]
        fleet.increments = [
            [VesselIncrement(5.0, 3.0, 1.0, package_uptake=np.zeros(2))]
        ]
        fleet.initial_technology_share = {("v0", "t0"): _ShareCurve(0.4)}

        define_initial_technology(fleet)

        increment = fleet.increments[0][0]
        expected = 0.4 * levelize_package_cost(flow, 10.0, DISCOUNT)
        np.testing.assert_array_almost_equal(increment.package_uptake, [0.6, 0.4])
        np.testing.assert_almost_equal(increment.technology_charter_rate, expected)
