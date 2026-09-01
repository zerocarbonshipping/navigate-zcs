# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests for the fleet-level totals published by calculate_fleet_profile.

Verifies:
  - Fuel-type demand accumulates multiplier-weighted on the fleet expectation,
    split between main and pilot fuel for dual-fuel converters, and the step
    total transfers to the fleet profile.
  - Fuel-type supply accumulates the fair-share port bunker supply across
    ports on the fleet expectation, its only store.
  - The fuel-type totals reset between time-steps instead of accumulating
    across them.
  - The carried technology charter rate accumulates multiplier-weighted into
    the profile technology expenses.
"""
from unittest.mock import MagicMock

import numpy as np

from navigate.core import Scalar
from navigate.core.enum_ import FuelTypeID
from navigate.core.expectations import FleetExpectation
from navigate.core.increment import Increment
from navigate.core.nodes.fleet import Fleet
from navigate.fleet.aggregation import calculate_fleet_profile
from navigate.util import YEAR


def _vessel() -> MagicMock:
    vessel = MagicMock()
    vessel.name = "v0"
    vessel.expectation.get_asset_charter_rate.return_value = 0.5
    vessel.expectation.get_tied_capital.return_value = np.zeros(3)

    for getter in ("get_reference_speed", "get_minimum_speed", "get_maximum_speed",
                   "get_actual_speed", "get_optimal_speed", "get_lowest_speed",
                   "get_highest_speed"):
        getattr(vessel.profile, getter).return_value = np.nan

    return vessel


def _converter(name: str, main_fuel_type: FuelTypeID) -> MagicMock:
    converter = MagicMock()
    converter.name = name
    converter.power_capacity = Scalar(10.)
    converter.is_dual_fuel.return_value = False
    converter.main_fuel_types = [main_fuel_type]
    converter.pilot_fuel_types = []
    return converter


def _fleet(vessel: MagicMock, increment: Increment | None = None) -> Fleet:
    fleet = Fleet.__new__(Fleet)
    fleet.assets = [vessel]
    fleet.increments = [[increment if increment is not None else Increment(4., 2., 1.)]]
    fleet.profile = MagicMock()
    fleet.profile.get_fuel_conversions.return_value = {}
    fleet.expectation = FleetExpectation()
    fleet.expectation.initialize(4, ["v0"], {})
    fleet.fuel_conversion_expenses = np.zeros(4)
    return fleet


class TestFuelTypeTotals:

    def test_demand_accumulates_and_transfers_to_profile(self):
        vessel = _vessel()
        vessel.expectation.get_spend_energy.return_value = 2.

        main = _converter("c0", FuelTypeID.OIL)

        dual = _converter("c1", FuelTypeID.OIL)
        dual.is_dual_fuel.return_value = True
        dual.minimum_pilot_fuel = Scalar(0.25)
        dual.pilot_fuel_types = [FuelTypeID.METHANOL]

        vessel.power_system.get_converters.return_value = [main, dual]

        fleet = _fleet(vessel)
        calculate_fleet_profile(fleet, fuels={}, timeline=np.arange(4.) * YEAR, idx=1)

        # per converter 2. spend energy x 4 vessels: c0 adds 8 oil, c1 splits its 8 as 6 oil + 2 pilot
        assert fleet.expectation.get_fuel_type_demand(FuelTypeID.OIL) == 14.
        assert fleet.expectation.get_fuel_type_demand(FuelTypeID.METHANOL) == 2.
        fleet.profile.add_fuel_type_demand.assert_any_call(FuelTypeID.OIL, 14., 1)
        fleet.profile.add_fuel_type_demand.assert_any_call(FuelTypeID.METHANOL, 2., 1)

    def test_supply_accumulates_fair_share(self):
        vessel = _vessel()
        vessel.power_system.get_converters.return_value = []
        vessel.expectation.get_fair_share_fuel_existing.return_value = {("p0", "lng"): 0.5,
                                                                        ("p1", "lng"): 0.25}

        ports = []
        for name in ("p0", "p1"):
            port = MagicMock()
            port.name = name
            port.is_bunkering_allowed.return_value = True
            port.expectation.get_bunker_supply.return_value = 3.
            ports.append(port)
        vessel.route.ports = ports

        fuel = MagicMock()
        fuel.fuel_type = FuelTypeID.METHANE
        fuel.lower_heating_value = Scalar(2.)

        fleet = _fleet(vessel)
        calculate_fleet_profile(fleet, fuels={"lng": fuel}, timeline=np.arange(4.) * YEAR, idx=1)

        # 3. mass x 2. LHV x fair share x 4 vessels: p0 contributes 12, p1 contributes 6
        assert fleet.expectation.get_fuel_type_supply(FuelTypeID.METHANE) == 18.
        assert fleet.expectation.get_fuel_type_supply(FuelTypeID.OIL) == 0.

    def test_totals_reset_between_steps(self):
        vessel = _vessel()
        vessel.expectation.get_spend_energy.return_value = 2.
        vessel.power_system.get_converters.return_value = [_converter("c0", FuelTypeID.OIL)]

        fleet = _fleet(vessel)
        calculate_fleet_profile(fleet, fuels={}, timeline=np.arange(4.) * YEAR, idx=1)
        calculate_fleet_profile(fleet, fuels={}, timeline=np.arange(4.) * YEAR, idx=2)

        assert fleet.expectation.get_fuel_type_demand(FuelTypeID.OIL) == 8.


class TestFleetProfileTechnologyExpenses:

    def test_carried_rate_accumulates_multiplier_weighted(self):
        vessel = _vessel()
        vessel.power_system.get_converters.return_value = []

        fleet = _fleet(vessel, Increment(4., 2., 1., technology_charter_rate=12.))
        calculate_fleet_profile(fleet, fuels={}, timeline=np.arange(4.) * YEAR, idx=1)

        fleet.profile.add_technology_expenses.assert_called_once_with(12. * 4., 1)
