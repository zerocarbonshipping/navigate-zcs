# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""GlobalProfile, the model-wide output storage the simulation fills."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from navigate.core.profiles._base_profile import result
from navigate.core.profiles._fuel_infrastructure_profile import (
    _FuelInfrastructureProfile,
)
from navigate.core.profiles._plant_aggregate_profile import _PlantAggregateProfile
from navigate.core.profiles._vessel_aggregate_profile import _VesselAggregateProfile

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.process import Process
    from navigate.core.profiles.profile_context import ProfileContext
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class GlobalProfile(
    _VesselAggregateProfile, _PlantAggregateProfile, _FuelInfrastructureProfile
):
    """Totals over every vessel, plant and port, plus the timings of the run."""

    # computational time in seconds; every entry below the total is part of it
    total_time: FloatArray = result("s")
    expected_build_time: FloatArray = result("s")
    expected_solve_time: FloatArray = result("s")
    expected_transfer_time: FloatArray = result("s")
    speed_time: FloatArray = result("s")
    retrofit_time: FloatArray = result("s")
    fleet_evolution_time: FloatArray = result("s")
    producer_evolution_time: FloatArray = result("s")
    existing_build_time: FloatArray = result("s")
    existing_solve_time: FloatArray = result("s")
    existing_transfer_time: FloatArray = result("s")
    temporal_time: FloatArray = result("s")
    vessel_time: FloatArray = result("s")
    fuel_supply_time: FloatArray = result("s")
    policy_time: FloatArray = result("s")
    fleet_state_time: FloatArray = result("s")
    profile_agg_time: FloatArray = result("s")
    overhead_time: FloatArray = result("s")

    def initialize(
        self,
        context: ProfileContext,
        feedstocks: dict[str, Feedstock],
        processes: dict[str, Process],
        regulation_names: Sequence[str] = (),
        levy_names: Sequence[str] = (),
    ) -> None:
        """
        Initialize the global profile's storage arrays and lookups.

        Parameters
        ----------
        context
            Timeline, fuels and emissions of the run.
        feedstocks
            All feedstocks in the simulation.
        processes
            All processes in the simulation.
        regulation_names
            Names of all regulations in the simulation.
        levy_names
            Names of all levies in the simulation.
        """
        self._initialize_base(context)
        self._initialize_fuel_consumer(regulation_names, levy_names)
        self._initialize_fuel_producer(feedstocks, processes)
        self._initialize_fuel_infrastructure()
        self._initialize_vessel_aggregate()
        self._initialize_plant_aggregate()

        # computational time
        self.total_time = self._default_array()
        self.expected_build_time = self._default_array()
        self.expected_solve_time = self._default_array()
        self.expected_transfer_time = self._default_array()
        self.speed_time = self._default_array()
        self.retrofit_time = self._default_array()
        self.fleet_evolution_time = self._default_array()
        self.producer_evolution_time = self._default_array()
        self.existing_build_time = self._default_array()
        self.existing_solve_time = self._default_array()
        self.existing_transfer_time = self._default_array()
        self.temporal_time = self._default_array()
        self.vessel_time = self._default_array()
        self.fuel_supply_time = self._default_array()
        self.policy_time = self._default_array()
        self.fleet_state_time = self._default_array()
        self.profile_agg_time = self._default_array()
        self.overhead_time = self._default_array()
