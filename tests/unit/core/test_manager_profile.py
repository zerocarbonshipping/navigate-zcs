# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""A constructed manager profile carries the state of every branch it aggregates."""

from __future__ import annotations

from navigate.core.profiles._fuel_infrastructure_profile import (
    _FuelInfrastructureProfile,
)
from navigate.core.profiles._plant_aggregate_profile import _PlantAggregateProfile
from navigate.core.profiles._vessel_aggregate_profile import _VesselAggregateProfile
from navigate.core.profiles.manager_profile import ManagerProfile

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
