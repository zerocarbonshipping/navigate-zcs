# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.expectations._expectation import _Expectation
from navigate.core.misc import EMPTY_FLOAT
from navigate.util import slice_dict

if TYPE_CHECKING:
    from navigate.fuel import Fuel


class FleetExpectation(_Expectation):
    def __init__(self):
        super().__init__()

        self._existing_multipliers: dict[str, np.ndarray] = {}     # dict[vessel_name: np.ndarray], number of existing vessels
        self._newbuild_multipliers: dict[str, np.ndarray] = {}     # dict[vessel_name: np.ndarray], number of newbuild vessels

        self._fuel_demand: dict[str, np.ndarray] = {}              # dict[fuel_name: np.ndarray], expected future fuel demand

        self._uptakes: np.ndarray = EMPTY_FLOAT

    def initialize(self, length: int, vessel_names: list[str], fuels: dict[str, Fuel]) -> None:
        self._initialize_expectation(length)

        self._existing_multipliers = self._default_dict_array(vessel_names)
        self._newbuild_multipliers = self._default_dict_array(vessel_names)

        self._fuel_demand = self._default_dict_array(fuels)

        self._uptakes = self._default_2D_array(len(vessel_names))

    def set_existing_multipliers(self, idx: int, vessel_name: str, multipliers: np.ndarray) -> None:
        self._existing_multipliers[vessel_name][idx:] = multipliers

    def set_newbuild_multipliers(self, idx: int, vessel_name: str, multipliers: np.ndarray) -> None:
        self._newbuild_multipliers[vessel_name][idx:] = multipliers

    def set_fuel_demand(self, idx: int, fuel_name: str, demand: float) -> None:
        self._fuel_demand[fuel_name][idx] = demand

    def set_uptakes(self, idx: int, uptakes: np.ndarray) -> None:
        self._uptakes[:, idx] = uptakes

    def get_existing_multipliers(self, vessel_name: str, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._existing_multipliers[vessel_name][idx]

    def get_newbuild_multipliers(self, vessel_name: str, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._newbuild_multipliers[vessel_name][idx]

    def get_expected_multipliers(self, vessel_name: str, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._existing_multipliers[vessel_name][idx] + self._newbuild_multipliers[vessel_name][idx]

    def get_total_existing_multipliers(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return np.add.reduce(list(self._existing_multipliers.values()))[idx]

    def get_total_expected_multipliers(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return (np.add.reduce(list(self._existing_multipliers.values()))
                + np.add.reduce(list(self._newbuild_multipliers.values())))[idx]

    def get_fuel_demand(self, idx: int | slice = np.s_[:]) -> dict[str, np.ndarray]:
        return slice_dict(self._fuel_demand, idx)

    def get_uptakes(self, idx: int) -> np.ndarray:
        return self._uptakes[:, :(idx + 1)]
