# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Regulation node, read by the bunkering LP and policy layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.expectations._policy_expectation import _PolicyExpectation
from navigate.core.initial_values import EMPTY_FLOAT

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray, FloatLike


class RegulationExpectation(_PolicyExpectation):
    """Compliance costs of a regulation and the capacity each vessel is measured on."""

    def __init__(self) -> None:
        super().__init__()

        self._flexibility_cost: FloatArray = EMPTY_FLOAT
        self._belief_flexibility_cost: FloatArray = EMPTY_FLOAT
        self._vessel_net_flexibility_units: dict[str, FloatArray] = {}
        self._remedial_cost: FloatArray = EMPTY_FLOAT

        self._vessel_capacity: dict[str, FloatArray] = {}

    def initialize(
        self, length: int, emission_names: Iterable[str], vessels: dict[str, Vessel]
    ) -> None:
        self._initialize_expectation(length)
        self._initialize_policy_expectation(emission_names)

        self._flexibility_cost = self._default_array()
        self._belief_flexibility_cost = self._default_array()
        self._vessel_net_flexibility_units = self._default_dict_array(vessels)
        self._remedial_cost = self._default_array()

        self._vessel_capacity = self._default_dict_array(vessels)

    def reset_expected_bunkering(self) -> None:
        self._flexibility_cost[:] = 0.0

        for units in self._vessel_net_flexibility_units.values():
            units[:] = 0.0

    def set_flexibility_cost(self, idx: int, cost: float) -> None:
        self._flexibility_cost[idx] = cost

    def set_vessel_net_flexibility_units(
        self, idx: int, vessel_name: str, units: float
    ) -> None:
        self._vessel_net_flexibility_units[vessel_name][idx] = units

    def set_remedial_cost(self, idx: int, cost: FloatLike) -> None:
        self._remedial_cost[idx:] = cost

    def set_vessel_capacity(
        self, idx: int, vessel_name: str, capacity: FloatLike
    ) -> None:
        self._vessel_capacity[vessel_name][idx:] = capacity

    def get_flexibility_cost(self) -> FloatArray:
        return self._flexibility_cost

    def get_belief_flexibility_cost(self) -> FloatArray:
        return self._belief_flexibility_cost

    def get_vessel_net_flexibility_units(self, vessel_name: str) -> FloatArray:
        return self._vessel_net_flexibility_units[vessel_name]

    def get_remedial_cost(self, idx: int) -> float:
        cost: float = self._remedial_cost[idx]
        return cost

    def get_vessel_capacity(self, vessel_name: str, idx: int) -> float:
        capacity: float = self._vessel_capacity[vessel_name][idx]
        return capacity
