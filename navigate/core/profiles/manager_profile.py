# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.misc import EMPTY_FLOAT
from navigate.core.profiles._infrastructure_aggregate_profile import _InfrastructureAggregateProfile
from navigate.core.profiles._plant_aggregate_profile import _PlantAggregateProfile
from navigate.core.profiles._vessel_aggregate_profile import _VesselAggregateProfile

if TYPE_CHECKING:
    from navigate.fuel import Emission, Fuel
    from navigate.fuel.feedstock import Feedstock
    from navigate.fuel.process import Process
    from navigate.fuel.source import Source


class ManagerProfile(_VesselAggregateProfile, _PlantAggregateProfile, _InfrastructureAggregateProfile):
    def __init__(self):
        _VesselAggregateProfile.__init__(self)
        _PlantAggregateProfile.__init__(self)
        _InfrastructureAggregateProfile.__init__(self)

        # computational time
        self._total_time: np.ndarray = EMPTY_FLOAT                 # complete FT simulation time
        self._expected_build_time: np.ndarray = EMPTY_FLOAT        # LP build time (part of FT)
        self._expected_solve_time: np.ndarray = EMPTY_FLOAT        # LP solve time (part of FT)
        self._expected_transfer_time: np.ndarray = EMPTY_FLOAT     # LP transfer time (part of FT)
        self._speed_time: np.ndarray = EMPTY_FLOAT                 # speed management time (part of FT)
        self._retrofit_time: np.ndarray = EMPTY_FLOAT              # EE retrofit time (part of FT)
        self._fleet_evolution_time: np.ndarray = EMPTY_FLOAT       # fleet evolution time (part of FT)
        self._producer_evolution_time: np.ndarray = EMPTY_FLOAT    # producer evolution time (part of FT)
        self._existing_build_time: np.ndarray = EMPTY_FLOAT        # LP model build time (part of FT)
        self._existing_solve_time: np.ndarray = EMPTY_FLOAT        # LP model solve time (part of FT)
        self._existing_transfer_time: np.ndarray = EMPTY_FLOAT     # LP transfer time (part of FT)
        self._temporal_time: np.ndarray = EMPTY_FLOAT              # temporal + expectations
        self._vessel_time: np.ndarray = EMPTY_FLOAT                # vessel ops + charter
        self._fuel_supply_time: np.ndarray = EMPTY_FLOAT           # fuel supply chain
        self._policy_time: np.ndarray = EMPTY_FLOAT                # policy + regulation
        self._fleet_state_time: np.ndarray = EMPTY_FLOAT           # age + evolution + tech
        self._profile_agg_time: np.ndarray = EMPTY_FLOAT           # profile aggregation
        self._overhead_time: np.ndarray = EMPTY_FLOAT              # init overhead

    def initialize(self, timeline: np.ndarray, emissions: dict[str, Emission],
                   feedstocks: dict[str, Feedstock], fuels: dict[str, Fuel],
                   processes: dict[str, Process], sources: dict[str, Source],
                   emissions_lifetime: float,
                   regulation_names: list[str] = (), levy_names: list[str] = ()) -> None:

        self._initialize_base(timeline)
        self._initialize_fuel_base(fuels)
        self._initialize_fuel_consumer(fuels, emissions, emissions_lifetime, regulation_names, levy_names)
        self._initialize_fuel_producer(feedstocks, fuels, processes, sources)
        self._initialize_fuel_infrastructure(fuels)
        self._initialize_vessel_aggregate(fuels)
        self._initialize_plant_aggregate(fuels)
        self._initialize_infrastructure_aggregate()

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

    def add_expected_build_time(self, idx: int, time: float) -> None:
        self._expected_build_time[idx] += time

    def add_expected_solve_time(self, idx: int, time: float) -> None:
        self._expected_solve_time[idx] += time

    def add_expected_transfer_time(self, idx: int, time: float) -> None:
        self._expected_transfer_time[idx] += time

    def set_speed_time(self, idx: int, time: float) -> None:
        self._speed_time[idx] = time

    def set_retrofit_time(self, idx: int, time: float) -> None:
        self._retrofit_time[idx] = time

    def add_fleet_evolution_time(self, idx: int, time: float) -> None:
        self._fleet_evolution_time[idx] += time

    def add_producer_evolution_time(self, idx: int, time: float) -> None:
        self._producer_evolution_time[idx] += time

    def set_existing_build_time(self, idx: int, time: float) -> None:
        self._existing_build_time[idx] = time

    def set_existing_solve_time(self, idx: int, time: float) -> None:
        self._existing_solve_time[idx] = time

    def set_existing_transfer_time(self, idx: int, time: float) -> None:
        self._existing_transfer_time[idx] = time

    def add_temporal_time(self, idx: int, time: float) -> None:
        self._temporal_time[idx] += time

    def add_vessel_time(self, idx: int, time: float) -> None:
        self._vessel_time[idx] += time

    def add_fuel_supply_time(self, idx: int, time: float) -> None:
        self._fuel_supply_time[idx] += time

    def add_policy_time(self, idx: int, time: float) -> None:
        self._policy_time[idx] += time

    def add_fleet_state_time(self, idx: int, time: float) -> None:
        self._fleet_state_time[idx] += time

    def add_profile_agg_time(self, idx: int, time: float) -> None:
        self._profile_agg_time[idx] += time

    def add_overhead_time(self, idx: int, time: float) -> None:
        self._overhead_time[idx] += time

    def get_total_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._total_time[idx]

    def get_expected_build_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._expected_build_time[idx]

    def get_expected_solve_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._expected_solve_time[idx]

    def get_expected_transfer_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._expected_transfer_time[idx]

    def get_speed_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._speed_time[idx]

    def get_retrofit_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._retrofit_time[idx]

    def get_fleet_evolution_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._fleet_evolution_time[idx]

    def get_producer_evolution_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._producer_evolution_time[idx]

    def get_existing_build_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._existing_build_time[idx]

    def get_existing_solve_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._existing_solve_time[idx]

    def get_existing_transfer_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._existing_transfer_time[idx]

    def get_temporal_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._temporal_time[idx]

    def get_vessel_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._vessel_time[idx]

    def get_fuel_supply_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._fuel_supply_time[idx]

    def get_policy_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._policy_time[idx]

    def get_fleet_state_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._fleet_state_time[idx]

    def get_profile_agg_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._profile_agg_time[idx]

    def get_overhead_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._overhead_time[idx]
