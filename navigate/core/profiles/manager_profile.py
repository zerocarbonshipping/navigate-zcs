# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""ManagerProfile, the model-wide output storage the simulation manager fills."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.initial_values import EMPTY_FLOAT
from navigate.core.profiles._fuel_infrastructure_profile import (
    _FuelInfrastructureProfile,
)
from navigate.core.profiles._plant_aggregate_profile import _PlantAggregateProfile
from navigate.core.profiles._vessel_aggregate_profile import _VesselAggregateProfile

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.process import Process
    from navigate.util.types_ import FloatArray


class ManagerProfile(
    _VesselAggregateProfile, _PlantAggregateProfile, _FuelInfrastructureProfile
):
    """Totals over every vessel, plant and port, plus the timings of the run."""

    def __init__(self) -> None:
        super().__init__()

        # computational time in seconds; every entry below the total is part of it
        self._total_time: FloatArray = EMPTY_FLOAT  # the whole simulation
        self._expected_build_time: FloatArray = EMPTY_FLOAT  # expected LP build
        self._expected_solve_time: FloatArray = EMPTY_FLOAT  # expected LP solve
        self._expected_transfer_time: FloatArray = EMPTY_FLOAT  # expected LP transfer
        self._speed_time: FloatArray = EMPTY_FLOAT  # speed management
        self._retrofit_time: FloatArray = EMPTY_FLOAT  # technology retrofit
        self._fleet_evolution_time: FloatArray = EMPTY_FLOAT  # fleet evolution
        self._producer_evolution_time: FloatArray = EMPTY_FLOAT  # producer evolution
        self._existing_build_time: FloatArray = EMPTY_FLOAT  # existing LP build
        self._existing_solve_time: FloatArray = EMPTY_FLOAT  # existing LP solve
        self._existing_transfer_time: FloatArray = EMPTY_FLOAT  # existing LP transfer
        self._temporal_time: FloatArray = EMPTY_FLOAT  # temporal and expectations
        self._vessel_time: FloatArray = EMPTY_FLOAT  # vessel operations and charter
        self._fuel_supply_time: FloatArray = EMPTY_FLOAT  # fuel supply chain
        self._policy_time: FloatArray = EMPTY_FLOAT  # policy and regulation
        self._fleet_state_time: FloatArray = EMPTY_FLOAT  # age, evolution, technology
        self._profile_agg_time: FloatArray = EMPTY_FLOAT  # profile aggregation
        self._overhead_time: FloatArray = EMPTY_FLOAT  # initialization overhead

    def initialize(
        self,
        timeline: FloatArray,
        emissions: dict[str, Emission],
        feedstocks: dict[str, Feedstock],
        fuels: dict[str, Fuel],
        processes: dict[str, Process],
        emissions_lifetime: float,
        regulation_names: Sequence[str] = (),
        levy_names: Sequence[str] = (),
    ) -> None:
        self._initialize_base(timeline)
        self._initialize_fuel_base(fuels)
        self._initialize_fuel_type(fuels)
        self._initialize_fuel_emission(emissions, emissions_lifetime)
        self._initialize_fuel_consumer(fuels, emissions, regulation_names, levy_names)
        self._initialize_fuel_producer(feedstocks, fuels, processes)
        self._initialize_fuel_infrastructure(fuels)
        self._initialize_vessel_aggregate()
        self._initialize_plant_aggregate()

        # computational time
        self._total_time = self._default_array()
        self._expected_build_time = self._default_array()
        self._expected_solve_time = self._default_array()
        self._expected_transfer_time = self._default_array()
        self._speed_time = self._default_array()
        self._retrofit_time = self._default_array()
        self._fleet_evolution_time = self._default_array()
        self._producer_evolution_time = self._default_array()
        self._existing_build_time = self._default_array()
        self._existing_solve_time = self._default_array()
        self._existing_transfer_time = self._default_array()
        self._temporal_time = self._default_array()
        self._vessel_time = self._default_array()
        self._fuel_supply_time = self._default_array()
        self._policy_time = self._default_array()
        self._fleet_state_time = self._default_array()
        self._profile_agg_time = self._default_array()
        self._overhead_time = self._default_array()

    def set_total_time(self, idx: int, time: float) -> None:
        self._total_time[idx] = time

    def add_expected_build_time(self, time: float, idx: int | slice = np.s_[:]) -> None:
        self._expected_build_time[idx] += time

    def add_expected_solve_time(self, time: float, idx: int | slice = np.s_[:]) -> None:
        self._expected_solve_time[idx] += time

    def add_expected_transfer_time(
        self, time: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._expected_transfer_time[idx] += time

    def set_speed_time(self, idx: int, time: float) -> None:
        self._speed_time[idx] = time

    def set_retrofit_time(self, idx: int, time: float) -> None:
        self._retrofit_time[idx] = time

    def add_fleet_evolution_time(
        self, time: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._fleet_evolution_time[idx] += time

    def add_producer_evolution_time(
        self, time: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._producer_evolution_time[idx] += time

    def set_existing_build_time(self, idx: int, time: float) -> None:
        self._existing_build_time[idx] = time

    def set_existing_solve_time(self, idx: int, time: float) -> None:
        self._existing_solve_time[idx] = time

    def set_existing_transfer_time(self, idx: int, time: float) -> None:
        self._existing_transfer_time[idx] = time

    def add_temporal_time(self, time: float, idx: int | slice = np.s_[:]) -> None:
        self._temporal_time[idx] += time

    def add_vessel_time(self, time: float, idx: int | slice = np.s_[:]) -> None:
        self._vessel_time[idx] += time

    def add_fuel_supply_time(self, time: float, idx: int | slice = np.s_[:]) -> None:
        self._fuel_supply_time[idx] += time

    def add_policy_time(self, time: float, idx: int | slice = np.s_[:]) -> None:
        self._policy_time[idx] += time

    def add_fleet_state_time(self, time: float, idx: int | slice = np.s_[:]) -> None:
        self._fleet_state_time[idx] += time

    def add_profile_agg_time(self, time: float, idx: int | slice = np.s_[:]) -> None:
        self._profile_agg_time[idx] += time

    def add_overhead_time(self, time: float, idx: int | slice = np.s_[:]) -> None:
        self._overhead_time[idx] += time

    def get_total_time(self) -> FloatArray:
        return self._total_time

    def get_expected_build_time(self) -> FloatArray:
        return self._expected_build_time

    def get_expected_solve_time(self) -> FloatArray:
        return self._expected_solve_time

    def get_expected_transfer_time(self) -> FloatArray:
        return self._expected_transfer_time

    def get_speed_time(self) -> FloatArray:
        return self._speed_time

    def get_retrofit_time(self) -> FloatArray:
        return self._retrofit_time

    def get_fleet_evolution_time(self) -> FloatArray:
        return self._fleet_evolution_time

    def get_producer_evolution_time(self) -> FloatArray:
        return self._producer_evolution_time

    def get_existing_build_time(self) -> FloatArray:
        return self._existing_build_time

    def get_existing_solve_time(self) -> FloatArray:
        return self._existing_solve_time

    def get_existing_transfer_time(self) -> FloatArray:
        return self._existing_transfer_time

    def get_temporal_time(self) -> FloatArray:
        return self._temporal_time

    def get_vessel_time(self) -> FloatArray:
        return self._vessel_time

    def get_fuel_supply_time(self) -> FloatArray:
        return self._fuel_supply_time

    def get_policy_time(self) -> FloatArray:
        return self._policy_time

    def get_fleet_state_time(self) -> FloatArray:
        return self._fleet_state_time

    def get_profile_agg_time(self) -> FloatArray:
        return self._profile_agg_time

    def get_overhead_time(self) -> FloatArray:
        return self._overhead_time
