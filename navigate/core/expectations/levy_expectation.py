# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Levy node, read by the bunkering LP and the policy layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

from navigate.core.expectations._policy_expectation import _PolicyExpectation
from navigate.core.initial_values import EMPTY_FLOAT

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.util.types_ import FloatArray, FloatLike


class LevyExpectation(_PolicyExpectation):
    """The level a levy charges and its cost per ton of each fuel a vessel bunkers."""

    def __init__(self) -> None:
        super().__init__()

        self._level: FloatArray = EMPTY_FLOAT

        # keyed by (vessel_name, port_name, fuel_name)
        self._cost: dict[tuple[str, str, str], FloatArray] = {}

    def initialize(self, length: int, emission_names: Iterable[str]) -> None:
        self._initialize_expectation(length)
        self._initialize_policy_expectation(emission_names)

        self._level = self._default_array()

    def set_level(self, idx: int, level: FloatLike) -> None:
        self._level[idx:] = level

    def set_cost(self, idx: int, key: tuple[str, str, str], cost: FloatLike) -> None:
        self._cost.setdefault(key, self._default_array())
        self._cost[key][idx:] = cost

    @overload
    def get_level(self, idx: int) -> float: ...

    @overload
    def get_level(self, idx: slice) -> FloatArray: ...

    def get_level(self, idx: int | slice) -> FloatLike:
        return self._level[idx]

    def get_cost(self, key: tuple[str, str, str], idx: int) -> float:

        if key not in self._cost:
            return 0.0

        cost: float = self._cost[key][idx]
        return cost
