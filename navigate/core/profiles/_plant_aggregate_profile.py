# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.misc import EMPTY_FLOAT
from navigate.core.profiles._fuel_producer_profile import _FuelProducerProfile

if TYPE_CHECKING:
    from navigate.fuel import Fuel


class _PlantAggregateProfile(_FuelProducerProfile):
    def __init__(self):
        super().__init__()

        self._plant_tied_capital: np.ndarray = EMPTY_FLOAT

        self._supply_expectation: dict[str, list[np.ndarray]] = {}  # supply expectation by producers

    def _initialize_plant_aggregate(self, fuels: dict[str, Fuel]) -> None:

        self._plant_tied_capital = self._default_array()

        for fuel_name, fuel in fuels.items():

            if fuel.belongs_to_liquid_market():
                self._supply_expectation[fuel_name] = self._default_list(self.get_length(), default=np.inf)
            else:
                self._supply_expectation[fuel_name] = self._default_list(self.get_length(), default=0.)

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

        for key in self._supply_expectation:
            for i, value in enumerate(profile._supply_expectation[key]):
                self._supply_expectation[key][i] += value

    def add_plant_tied_capital(self, tied_capital: float, idx: int) -> None:
        self._plant_tied_capital[idx] += tied_capital

    def add_supply_expectation(self, fuel_name: str, idx: int, supply_expectation: np.ndarray) -> None:
        self._supply_expectation[fuel_name][idx][idx:] += supply_expectation

    def get_plant_tied_capital(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._plant_tied_capital[idx]

    def get_supply_expectation(self) -> dict[str, list[np.ndarray]]:
        return self._supply_expectation
