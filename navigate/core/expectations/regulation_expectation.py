# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

import numpy as np

from navigate.core.expectations._policy_expectation import _PolicyExpectation
from navigate.core.misc import EMPTY_FLOAT

if TYPE_CHECKING:
    from navigate.vessel import Vessel


class RegulationExpectation(_PolicyExpectation):
    def __init__(self):
        super().__init__()

        self._flexibility_cost: np.ndarray = EMPTY_FLOAT
        self._belief_flexibility_cost: np.ndarray = EMPTY_FLOAT
        self._vessel_net_flexibility_units: dict[str, np.ndarray] = {}
        self._remedial_cost: np.ndarray = EMPTY_FLOAT

        self._vessel_capacity: dict[str, np.ndarray] = {}

    def initialize(self, length: int, emission_names: Iterable[str], vessels: dict[str, Vessel]) -> None:
        self._initialize_expectation(length)
        self._initialize_policy_expectation(emission_names)

        self._flexibility_cost = self._default_array()
        self._belief_flexibility_cost = self._default_array()
        self._vessel_net_flexibility_units = self._default_dict_array(vessels)
        self._remedial_cost = self._default_array()

        self._vessel_capacity = self._default_dict_array(vessels)

    def reset_expected_bunkering(self) -> None:
        self._flexibility_cost[:] = 0.

        for units in self._vessel_net_flexibility_units.values():
            units[:] = 0.

    def set_flexibility_cost(self, idx: int, cost: float) -> None:
        self._flexibility_cost[idx] = cost

    def set_vessel_net_flexibility_units(self, idx: int, vessel_name: str, units: float) -> None:
        self._vessel_net_flexibility_units[vessel_name][idx] = units

    def set_remedial_cost(self, idx: int, cost: np.ndarray) -> None:
        self._remedial_cost[idx:] = cost

    def set_vessel_capacity(self, idx: int, vessel_name: str, capacity: np.ndarray) -> None:
        self._vessel_capacity[vessel_name][idx:] = capacity

    def get_flexibility_cost(self, idx: int | slice = np.s_[:]) -> float | np.ndarray:
        return self._flexibility_cost[idx]

    def get_belief_flexibility_cost(self) -> np.ndarray:
        return self._belief_flexibility_cost

    def get_vessel_net_flexibility_units(self, vessel_name: str) -> np.ndarray:
        return self._vessel_net_flexibility_units[vessel_name]

    def get_remedial_cost(self, idx: int) -> np.ndarray:
        return self._remedial_cost[idx]

    def get_vessel_capacity(self, vessel_name: str, idx: int) -> np.ndarray:
        return self._vessel_capacity[vessel_name][idx]
