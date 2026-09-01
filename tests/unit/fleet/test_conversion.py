# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests for the fuel-conversion business case (navigate/fleet/conversion.py)."""
from unittest.mock import MagicMock, patch

import numpy as np

from navigate.core import Scalar
from navigate.core.enum_ import FuelTypeID, UtilityID
from navigate.core.increment import Increment
from navigate.core.nodes.fleet import Fleet
from navigate.economics.metric import calculate_net_present_value
from navigate.fleet.conversion import apply_fuel_conversions, propose_fuel_conversions
from navigate.util import YEAR, dates_to_days


def _vessel(name: str,
            fuel_type: FuelTypeID,
            fuel_cost_flow: np.ndarray,
            lifetime: float = 25.,
            cost_of_capital: float = 0.1,
            total_energy: float = 10.,
            capex_npv: float = 500.) -> MagicMock:
    vessel = MagicMock()
    vessel.name = name
    vessel.fuel_type = fuel_type
    vessel.lifetime = Scalar(lifetime)
    vessel.cost_of_capital = Scalar(cost_of_capital)
    vessel.expectation.get_fuel_cost_flow.return_value = fuel_cost_flow
    vessel.expectation.get_total_energy.return_value = total_energy
    vessel.expectation.get_capex_npv.return_value = capex_npv
    return vessel


def _fleet(vessels: list, conversion_cost: dict, supply: dict) -> Fleet:
    fleet = Fleet.__new__(Fleet)
    fleet.assets = vessels
    fleet.increments = [[] for _ in vessels]
    fleet.retrofit_frequency = Scalar(5.)
    fleet.fuel_conversion_minimum_age = Scalar(0.)
    fleet.fuel_conversion_sensitivity = Scalar(2.)
    fleet.fuel_conversion_cost = {pair: Scalar(cost) for pair, cost in conversion_cost.items()}
    fleet.allow_vessel = {vessel.name: True for vessel in vessels}
    fleet.conversion_available = {vessel.name: True for vessel in vessels}
    fleet.profile = MagicMock()
    fleet.profile.get_fuel_type_supply.side_effect = lambda fuel_type, idx: supply.get(fuel_type, 0.)
    fleet.profile.get_fuel_type_demand.return_value = 0.
    return fleet


def _oil_to_ammonia_fleet(supply: float = 1000., multiplier: float = 4., age: float = 10.) -> Fleet:
    """One oil vessel with one increment, one ammonia destination, conversion cost 100."""
    vessel_from = _vessel("oil", FuelTypeID.OIL, np.full(30, 8.))
    vessel_to = _vessel("ammonia", FuelTypeID.AMMONIA, np.full(30, 3.))
    fleet = _fleet([vessel_from, vessel_to],
                   {("oil", "ammonia"): 100.},
                   {FuelTypeID.AMMONIA: supply})
    fleet.increments[0] = [Increment(multiplier, age, 1., package_uptake=np.array([1.]))]
    return fleet


_DCM = 'navigate.fleet.conversion.calculate_asset_shares'
_SHARES = (np.array([0.25, 0.75]), "")


def _assert_no_proposals(fleet: Fleet) -> None:
    with patch(_DCM) as dcm:
        assert propose_fuel_conversions(fleet, idx=3, time_step=YEAR) == {}

    dcm.assert_not_called()


class TestProposeFuelConversions:

    def test_dcm_receives_business_case(self):
        fleet = _oil_to_ammonia_fleet()

        with patch(_DCM, return_value=_SHARES) as dcm:
            proposals = propose_fuel_conversions(fleet, idx=3, time_step=YEAR)

        # age 10 with dt 1 gives avg_age 10.5 and 14.5 remaining years: 14 full
        # years of fuel saving plus a prorated half year, less the lump-sum cost
        expected_cash = np.full(15, 8. - 3.)
        expected_cash[-1] *= 0.5
        expected_cash[0] -= 100.

        (metrics_list, utility, sensitivity), kwargs = dcm.call_args
        np.testing.assert_almost_equal(metrics_list[0],
                                       calculate_net_present_value(expected_cash, 0.1))
        assert metrics_list[1] == 0.
        assert utility is UtilityID.SIGNED_REFERENCE
        assert sensitivity == 2.
        assert kwargs['reference'] == 500.
        assert kwargs['limits'] == [1., 1.]

        proposal = proposals[("oil", 0)]
        assert proposal['age'] == 10.
        assert proposal['dt'] == 1.
        np.testing.assert_almost_equal(proposal['conversions']['ammonia'], 0.25 * 4.)

    def test_costs_per_vessel_annualizes_conversion_cost(self):
        fleet = _oil_to_ammonia_fleet()

        with patch(_DCM, return_value=_SHARES):
            proposals = propose_fuel_conversions(fleet, idx=3, time_step=YEAR)

        yearly = 100. * (1. / 14.5 + 0.1)
        expected = np.full(15, yearly)
        expected[-1] *= 0.5
        np.testing.assert_array_almost_equal(proposals[("oil", 0)]['costs_per_vessel']['ammonia'],
                                             expected)

    def test_expectation_flows_not_mutated(self):
        fleet = _oil_to_ammonia_fleet()

        with patch(_DCM, return_value=_SHARES):
            propose_fuel_conversions(fleet, idx=3, time_step=YEAR)

        np.testing.assert_array_equal(fleet.assets[0].expectation.get_fuel_cost_flow(),
                                      np.full(30, 8.))
        np.testing.assert_array_equal(fleet.assets[1].expectation.get_fuel_cost_flow(),
                                      np.full(30, 3.))

    def test_supply_cap_limits_and_debit(self):
        # walked youngest (age 10) first: limit (30 / 10) / 4; its 2 proposed
        # conversions encumber 20 units, leaving the older increment (10 / 10) / 4
        fleet = _oil_to_ammonia_fleet(supply=30.)
        fleet.increments[0] = [Increment(4., 15., 1., package_uptake=np.array([1.])),
                               Increment(4., 10., 1., package_uptake=np.array([1.]))]

        with patch(_DCM, return_value=(np.array([0.5, 0.5]), "")) as dcm:
            propose_fuel_conversions(fleet, idx=3, time_step=YEAR)

        limits = [call.kwargs['limits'][0] for call in dcm.call_args_list]
        np.testing.assert_almost_equal(limits, [0.75, 0.25])

    def test_skips_increment_off_retrofit_cycle(self):
        _assert_no_proposals(_oil_to_ammonia_fleet(age=7.))

    def test_skips_increment_below_minimum_age(self):
        fleet = _oil_to_ammonia_fleet()
        fleet.fuel_conversion_minimum_age = Scalar(15.)
        _assert_no_proposals(fleet)

    def test_skips_increment_beyond_lifetime(self):
        _assert_no_proposals(_oil_to_ammonia_fleet(age=25.))

    def test_skips_unavailable_destination(self):
        fleet = _oil_to_ammonia_fleet()
        fleet.conversion_available["ammonia"] = False
        _assert_no_proposals(fleet)

    def test_skips_destination_without_supply(self):
        _assert_no_proposals(_oil_to_ammonia_fleet(supply=0.))


class TestApplyFuelConversionExpenses:
    """Conversion expenses anchor to elapsed years, not time-step indices."""

    def test_installments_land_on_calendar_timeline(self):
        vessel_a, vessel_b = MagicMock(), MagicMock()
        vessel_a.name = "a"
        vessel_b.name = "b"

        fleet = Fleet.__new__(Fleet)
        fleet.assets = [vessel_a, vessel_b]
        fleet.profile = MagicMock()
        fleet.increments = [[Increment(10., 5., 1., package_uptake=np.array([1., 0.]))], []]

        # calendar years are 365 or 366 days, so years = timeline / YEAR drifts
        # off the step indices; at idx=1 (365 days elapsed) years[1] < 1
        dates = np.array([np.datetime64(f"{year}-01-01") for year in range(2025, 2030)])
        timeline = dates_to_days(dates)
        fleet.fuel_conversion_expenses = np.zeros_like(timeline)

        idx = 1
        costs = np.array([30., 30., 30.])
        proposals = {("a", 0): {"age": 5., "dt": 1.,
                                "costs_per_vessel": {"b": costs},
                                "conversions": {"b": 2.}}}
        apply_fuel_conversions(fleet, proposals, idx=idx, timeline=timeline)

        expected = np.zeros_like(timeline)
        expected[idx:idx + costs.size] = 2. * costs[0]
        np.testing.assert_array_almost_equal(fleet.fuel_conversion_expenses, expected)
