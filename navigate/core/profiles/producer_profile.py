# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.misc import EMPTY_FLOAT, EMPTY_NAN
from navigate.core.profiles._plant_aggregate_profile import _PlantAggregateProfile
from navigate.util import extract_from_dict

if TYPE_CHECKING:
    from navigate.fuel import Fuel
    from navigate.fuel.feedstock import Feedstock
    from navigate.fuel.process import Process


class ProducerProfile(_PlantAggregateProfile):
    def __init__(self):
        super().__init__()

        self._maximum_development: np.ndarray = EMPTY_NAN
        self._development: np.ndarray = EMPTY_FLOAT

        self._fair_share_fuel_fraction: dict[str, np.ndarray] = {}  # fraction of fair-share going to the specific producer

    def initialize(self, timeline: np.ndarray,
                   feedstocks: dict[str, Feedstock], fuels: dict[str, Fuel],
                   processes: dict[str, Process]) -> None:
        """

        Parameters
        ----------
        timeline : np.ndarray
            Simulation timeline in years.
        feedstocks : dict[Feedstock]
            All feedstocks in the simulation.
        fuels : dict[Fuel]
            All fuels in the simulation.
        processes : dict[Process]
            All processes in the simulation.
        """

        self._initialize_base(timeline)
        self._initialize_fuel_base(fuels)
        self._initialize_fuel_producer(feedstocks, fuels, processes)
        self._initialize_plant_aggregate(fuels)

        self._maximum_development = self._default_array(default=np.nan)
        self._development = self._default_array()

        self._fair_share_fuel_fraction = self._default_dict(fuels)

    def set_maximum_development(self, idx: int, development_constraint: float) -> None:
        self._maximum_development[idx] = development_constraint

    def set_development(self, idx: int, development: float) -> None:
        self._development[idx] = development

    def set_fair_share_fuel_fraction(self, idx: int, fuel_name: str, fair_share: float) -> None:
        self._fair_share_fuel_fraction[fuel_name][idx] = fair_share

    def get_maximum_development(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._maximum_development[idx]

    def get_development(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._development[idx]

    def get_cumulative_maximum_development(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._to_cumulative(self._maximum_development[idx])

    def get_cumulative_development(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._to_cumulative(self._development[idx])

    def get_fair_share_fuel_fraction(
            self, fuel_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._fair_share_fuel_fraction, fuel_name, idx)
