# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Levy node, read by the bunkering LP and the policy layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

from navigate.core.expectations._policy_expectation import _PolicyExpectation

if TYPE_CHECKING:
    from collections.abc import Collection

    from navigate.util.types_ import FloatArray, FloatLike, Index


class LevyExpectation(_PolicyExpectation[tuple[str, str, str]]):
    """The level a levy charges and its cost per ton of each fuel a vessel bunkers."""

    def __init__(self) -> None:
        super().__init__()

        self._level: FloatArray

        # keyed by (vessel_name, port_name, fuel_name)
        self._cost: dict[tuple[str, str, str], FloatArray] = {}

    def initialize(self, length: int, emission_names: Collection[str]) -> None:
        self._initialize_expectation(length)
        self._initialize_policy_expectation(emission_names)

        self._level = self._default_array()

    def set_level(self, idx: int, level: FloatArray) -> None:
        self._level[idx:] = level

    def set_cost(self, key: tuple[str, str, str], idx: int, cost: FloatLike) -> None:
        self._cost.setdefault(key, self._default_array())
        self._cost[key][idx:] = cost

    @overload
    def get_level(self, idx: int) -> float: ...

    @overload
    def get_level(self, idx: slice) -> FloatArray: ...

    def get_level(self, idx: Index) -> FloatLike:
        return self._level[idx]

    def get_cost(self, key: tuple[str, str, str], idx: int) -> float:
        if key not in self._cost:
            return 0.0

        cost: float = self._cost[key][idx]
        return cost
