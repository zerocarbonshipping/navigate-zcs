# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the fleet-level totals published by calculate_fleet_profile.

Verifies:
  - Fuel-type capacity accumulates multiplier-weighted on the fleet expectation,
    split between main and pilot fuel for dual-fuel converters, and the step
    total transfers to the fleet profile.
  - Fuel-type supply accumulates the vessels' allocations of the port bunker
    supply on the fleet expectation, its only store, counting each port once
    however often the route calls it.
  - The fuel-type totals reset between time-steps instead of accumulating
    across them.
  - The carried technology charter rate accumulates multiplier-weighted into
    the profile technology expenses.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from navigate.core import Scalar
from navigate.core.enum_ import FuelTypeID
from navigate.core.expectations import FleetExpectation
from navigate.core.increment import VesselIncrement
from navigate.core.nodes.fleet import Fleet
from navigate.simulation.fleet.aggregation import calculate_fleet_profile
from navigate.util import YEAR


def _vessel() -> MagicMock:
    vessel = MagicMock()
    vessel.name = "v0"
    vessel.expectation.get_asset_charter_rate.return_value = 0.5
    vessel.expectation.get_tied_capital.return_value = np.zeros(3)
    return vessel


def _converter(name: str, main_fuel_type: FuelTypeID) -> MagicMock:
    converter = MagicMock()
    converter.name = name
    converter.power_capacity = Scalar(10.0)
    converter.is_dual_fuel.return_value = False
    converter.main_fuel_types = [main_fuel_type]
    converter.pilot_fuel_types = []
    return converter


def _fleet(vessel: MagicMock, increment: VesselIncrement | None = None) -> Fleet:
    fleet = Fleet.__new__(Fleet)
    fleet.assets = [vessel]
    fleet.increments = [
        [
            increment
            if increment is not None
            else VesselIncrement(4.0, 2.0, 1.0, package_uptake=np.array([1.0]))
        ]
    ]
    fleet.profile = MagicMock()
    fleet.expectation = FleetExpectation()
    fleet.expectation.initialize(4, ["v0"], {})
    return fleet


class TestFuelTypeTotals:
    def test_capacity_accumulates_and_transfers_to_profile(self):
        vessel = _vessel()
        vessel.expectation.get_spend_energy.return_value = 2.0

        main = _converter("c0", FuelTypeID.OIL)

        dual = _converter("c1", FuelTypeID.OIL)
        dual.is_dual_fuel.return_value = True
        dual.minimum_pilot_fuel = Scalar(0.25)
        dual.pilot_fuel_types = [FuelTypeID.METHANOL]

        vessel.power_system.get_converters.return_value = [main, dual]

        fleet = _fleet(vessel)
        calculate_fleet_profile(fleet, fuels={}, timeline=np.arange(4.0) * YEAR, idx=1)

        # per converter 2. spend energy x 4 vessels: c0 adds 8 oil, c1 splits its 8 as 6
        # oil + 2 pilot
        expectation = fleet.expectation
        add_capacity = fleet.profile.add_fuel_type_capacity

        assert expectation.get_fuel_type_capacity(FuelTypeID.OIL) == 14.0
        assert expectation.get_fuel_type_capacity(FuelTypeID.METHANOL) == 2.0
        add_capacity.assert_any_call(FuelTypeID.OIL, 14.0, 1)
        add_capacity.assert_any_call(FuelTypeID.METHANOL, 2.0, 1)

    def test_supply_accumulates_allocation(self):
        vessel = _vessel()
        vessel.power_system.get_converters.return_value = []
        allocations = {("p0", "lng"): 1.5, ("p1", "lng"): 0.75}
        vessel.expectation.get_allocation_fuel_existing.side_effect = (
            lambda port_name, fuel_name: allocations[(port_name, fuel_name)]
        )

        ports = []
        for name in ("p0", "p1"):
            port = MagicMock()
            port.name = name
            port.is_bunkering_allowed.return_value = True
            # a finite supply, so the allocation counts rather than the supply
            port.expectation.get_bunker_supply.return_value = 3.0
            ports.append(port)

        p0, p1 = ports
        vessel.route.ports = [p0, p1, p0]

        fuel = MagicMock()
        fuel.fuel_type = FuelTypeID.METHANE
        fuel.lower_heating_value = Scalar(2.0)

        fleet = _fleet(vessel)
        calculate_fleet_profile(
            fleet, fuels={"lng": fuel}, timeline=np.arange(4.0) * YEAR, idx=1
        )

        # allocated mass x 2. LHV x 4 vessels: p0 contributes 12 once, p1 contributes 6
        assert fleet.expectation.get_fuel_type_supply(FuelTypeID.METHANE) == 18.0
        assert fleet.expectation.get_fuel_type_supply(FuelTypeID.OIL) == 0.0

    def test_totals_reset_between_steps(self):
        vessel = _vessel()
        vessel.expectation.get_spend_energy.return_value = 2.0
        vessel.power_system.get_converters.return_value = [
            _converter("c0", FuelTypeID.OIL)
        ]

        fleet = _fleet(vessel)
        calculate_fleet_profile(fleet, fuels={}, timeline=np.arange(4.0) * YEAR, idx=1)
        calculate_fleet_profile(fleet, fuels={}, timeline=np.arange(4.0) * YEAR, idx=2)

        assert fleet.expectation.get_fuel_type_capacity(FuelTypeID.OIL) == 8.0


class TestFleetProfileTechnologyExpenses:
    def test_carried_rate_accumulates_multiplier_weighted(self):
        vessel = _vessel()
        vessel.power_system.get_converters.return_value = []

        fleet = _fleet(
            vessel,
            VesselIncrement(
                4.0,
                2.0,
                1.0,
                package_uptake=np.array([1.0]),
                technology_charter_rate=12.0,
            ),
        )
        calculate_fleet_profile(fleet, fuels={}, timeline=np.arange(4.0) * YEAR, idx=1)

        fleet.profile.add_technology_expenses.assert_called_once_with(12.0 * 4.0, 1)
