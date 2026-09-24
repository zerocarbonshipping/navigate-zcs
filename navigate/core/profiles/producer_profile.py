# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""ProducerProfile, the output storage the Producer node reports results from."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.initial_values import EMPTY_FLOAT, EMPTY_NAN
from navigate.core.profiles._plant_aggregate_profile import _PlantAggregateProfile

if TYPE_CHECKING:
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.process import Process
    from navigate.util.types_ import FloatArray


class ProducerProfile(_PlantAggregateProfile):
    """Production, feedstock use and plant development of one fuel producer."""

    def __init__(self) -> None:
        super().__init__()

        # plants added to the development pipeline, plants/year
        self._maximum_development: FloatArray = EMPTY_NAN
        self._development: FloatArray = EMPTY_FLOAT

        self._fair_share_fuel_fraction: dict[str, FloatArray] = {}

    def initialize(
        self,
        timeline: FloatArray,
        feedstocks: dict[str, Feedstock],
        fuels: dict[str, Fuel],
        processes: dict[str, Process],
    ) -> None:
        """
        Initialize the producer profile's storage arrays and lookups.

        Parameters
        ----------
        timeline
            Simulation timeline, in years.
        feedstocks
            All feedstocks in the simulation.
        fuels
            All fuels in the simulation.
        processes
            All processes in the simulation.
        """
        self._initialize_base(timeline)
        self._initialize_fuel_base(fuels)
        self._initialize_fuel_type(fuels)
        self._initialize_fuel_producer(feedstocks, fuels, processes)
        self._initialize_plant_aggregate()

        self._maximum_development = self._default_array(default=np.nan)
        self._development = self._default_array()

        self._fair_share_fuel_fraction = self._default_dict(fuels)

    def set_maximum_development(self, idx: int, development_constraint: float) -> None:
        self._maximum_development[idx] = development_constraint

    def set_development(self, idx: int, development: float) -> None:
        self._development[idx] = development

    def set_fair_share_fuel_fraction(
        self, idx: int, fuel_name: str, fair_share: float
    ) -> None:
        self._fair_share_fuel_fraction[fuel_name][idx] = fair_share

    def get_maximum_development(self) -> FloatArray:
        return self._maximum_development

    def get_development(self) -> FloatArray:
        return self._development

    def get_cumulative_maximum_development(self) -> FloatArray:
        return self._to_cumulative(self._maximum_development)

    def get_cumulative_development(self) -> FloatArray:
        return self._to_cumulative(self._development)

    def get_fair_share_fuel_fraction(self) -> dict[str, FloatArray]:
        return dict(self._fair_share_fuel_fraction)
