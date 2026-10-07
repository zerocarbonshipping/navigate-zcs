# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""A constructed global profile carries the state of every branch it aggregates."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from navigate.core.enum_ import FuelTypeID
from navigate.core.profiles._fuel_infrastructure_profile import (
    _FuelInfrastructureProfile,
)
from navigate.core.profiles._plant_aggregate_profile import _PlantAggregateProfile
from navigate.core.profiles._vessel_aggregate_profile import _VesselAggregateProfile
from navigate.core.profiles.global_profile import GlobalProfile
from navigate.core.profiles.port_profile import PortProfile


def _fuel():
    fuel = MagicMock()
    fuel.fuel_type = FuelTypeID.OIL
    fuel.liquid_market = False
    fuel.lower_heating_value.get.return_value = 1.0
    return fuel


# the wall-clock breakdown of one simulation, read back through the global profile's
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


def test_global_profile_state_is_the_three_branches_plus_its_own_timings():
    # a global profile aggregates vessels, plants and infrastructure, so constructing
    # one has to run all three branches' constructors and nothing else
    branches = (
        set(vars(_VesselAggregateProfile()))
        | set(vars(_PlantAggregateProfile()))
        | set(vars(_FuelInfrastructureProfile()))
    )

    assert set(vars(GlobalProfile())) == branches | TIMING_ATTRIBUTES


class TestBunkerSupplyMassAggregation:
    """The global bunker supply is the sum of every port's own supply."""

    @staticmethod
    def _port(fuels, timeline):
        port = PortProfile()
        port.initialize(
            timeline=timeline, emissions={}, fuels=fuels, emissions_lifetime=100.0
        )
        return port

    @staticmethod
    def _global_profile(fuels, timeline):
        profile = GlobalProfile()
        profile.initialize(
            timeline=timeline,
            emissions={},
            feedstocks={},
            fuels=fuels,
            processes={},
            emissions_lifetime=100.0,
        )
        return profile

    def test_finite_ports_aggregate_to_their_finite_sum(self):
        fuels = {"fuel_a": _fuel()}
        timeline = np.array([0.0])

        port_a = self._port(fuels, timeline)
        port_a.set_bunker_supply_mass(0, "fuel_a", 100.0)

        port_b = self._port(fuels, timeline)
        port_b.set_bunker_supply_mass(0, "fuel_a", 50.0)

        profile = self._global_profile(fuels, timeline)
        profile.add_fuel_infrastructure_profile(port_a)
        profile.add_fuel_infrastructure_profile(port_b)

        assert profile.get_bunker_supply_mass()["fuel_a"][0] == 150.0
