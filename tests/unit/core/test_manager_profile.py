# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""A constructed manager profile carries the state of every branch it aggregates."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from navigate.core.enum_ import FuelTypeID
from navigate.core.profiles._fuel_infrastructure_profile import (
    _FuelInfrastructureProfile,
)
from navigate.core.profiles._plant_aggregate_profile import _PlantAggregateProfile
from navigate.core.profiles._vessel_aggregate_profile import _VesselAggregateProfile
from navigate.core.profiles.manager_profile import ManagerProfile
from navigate.core.profiles.port_profile import PortProfile


def _fuel():
    fuel = MagicMock()
    fuel.fuel_type = FuelTypeID.OIL
    fuel.liquid_market = False
    fuel.lower_heating_value.get.return_value = 1.0
    return fuel


# the wall-clock breakdown of one simulation, read back through the manager's
# get_*_time readers; no branch it aggregates declares any of it
TIMING_ATTRIBUTES = frozenset(
    {
        "_total_time",
        "_expected_build_time",
        "_expected_solve_time",
        "_expected_transfer_time",
        "_speed_time",
        "_retrofit_time",
        "_fleet_evolution_time",
        "_producer_evolution_time",
        "_existing_build_time",
        "_existing_solve_time",
        "_existing_transfer_time",
        "_temporal_time",
        "_vessel_time",
        "_fuel_supply_time",
        "_policy_time",
        "_fleet_state_time",
        "_profile_agg_time",
        "_overhead_time",
    }
)


def test_manager_state_is_the_three_branches_plus_its_own_timings():
    # a manager aggregates vessels, plants and infrastructure, so constructing
    # one has to run all three branches' constructors and nothing else
    branches = (
        set(vars(_VesselAggregateProfile()))
        | set(vars(_PlantAggregateProfile()))
        | set(vars(_FuelInfrastructureProfile()))
    )

    assert set(vars(ManagerProfile())) == branches | TIMING_ATTRIBUTES


class TestBunkerSupplyMassAggregation:
    """
    Port and manager report an unconstrained bunker supply differently.

    A port with no reported supply that step (an unconstrained supply, never
    written as np.inf) carries NaN; the manager's own array starts at the
    additive identity 0 so it can sum several ports, but a NaN port entry
    still propagates into that sum instead of being skipped, since a finite
    total would understate a true supply that is actually unbounded.
    """

    @staticmethod
    def _port(fuels, timeline):
        port = PortProfile()
        port.initialize(
            timeline=timeline, emissions={}, fuels=fuels, emissions_lifetime=100.0
        )
        return port

    def test_a_fresh_port_reports_nan_until_written(self):
        fuels = {"fuel_a": _fuel()}
        port = self._port(fuels, np.array([0.0]))

        assert np.isnan(port.get_bunker_supply_mass()["fuel_a"][0])

    def test_a_fresh_manager_reports_zero_until_aggregated(self):
        fuels = {"fuel_a": _fuel()}
        manager = ManagerProfile()
        manager.initialize(
            timeline=np.array([0.0]),
            emissions={},
            feedstocks={},
            fuels=fuels,
            processes={},
            emissions_lifetime=100.0,
        )

        assert manager.get_bunker_supply_mass()["fuel_a"][0] == 0.0

    def test_one_unreported_port_makes_the_global_total_nan(self):
        # fuel_a: both ports report a finite supply, so the global total is
        # their ordinary sum. fuel_b: one port is unconstrained that step and
        # reports nothing (NaN); the global total propagates that NaN rather
        # than silently summing only the port that did report, which would
        # understate an actually-unbounded total as a false precise number
        fuels = {"fuel_a": _fuel(), "fuel_b": _fuel()}
        timeline = np.array([0.0])

        port_a = self._port(fuels, timeline)
        port_a.set_bunker_supply_mass(0, "fuel_a", 100.0)
        port_a.set_bunker_supply_mass(0, "fuel_b", 200.0)

        port_b = self._port(fuels, timeline)
        port_b.set_bunker_supply_mass(0, "fuel_a", 50.0)
        # fuel_b left unwritten on port_b: unconstrained that step

        manager = ManagerProfile()
        manager.initialize(
            timeline=timeline,
            emissions={},
            feedstocks={},
            fuels=fuels,
            processes={},
            emissions_lifetime=100.0,
        )
        manager.add_fuel_infrastructure_profile(port_a)
        manager.add_fuel_infrastructure_profile(port_b)

        total = manager.get_bunker_supply_mass()
        assert total["fuel_a"][0] == 150.0
        assert np.isnan(total["fuel_b"][0])
