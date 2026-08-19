# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import numpy as np

from navigate.core.misc import EMPTY_FLOAT
from navigate.core.profiles._fuel_producer_profile import _FuelProducerProfile


class _PlantAggregateProfile(_FuelProducerProfile):
    def __init__(self):
        super().__init__()

        self._plant_tied_capital: np.ndarray = EMPTY_FLOAT

    def _initialize_plant_aggregate(self) -> None:

        self._plant_tied_capital = self._default_array()

    def add_plant_aggregate_profile(self, profile: _PlantAggregateProfile, idx: int | slice = np.s_[:]) -> None:
        """

        Parameters
        ----------
        profile : _PlantAggregateProfile | ProducerProfile
            Aggregate profile from other node.
        idx : int
            Time-step index.
        """

        self._plant_tied_capital[idx] += profile._plant_tied_capital[idx]

    def add_plant_tied_capital(self, tied_capital: float, idx: int) -> None:
        self._plant_tied_capital[idx] += tied_capital

    def get_plant_tied_capital(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._plant_tied_capital[idx]
