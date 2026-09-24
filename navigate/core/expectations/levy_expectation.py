# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Levy node, read by the bunkering LP and the policy layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.expectations._policy_expectation import _PolicyExpectation
from navigate.core.initial_values import EMPTY_FLOAT

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.util.types_ import FloatArray, FloatLike


class LevyExpectation(_PolicyExpectation):
    """The level a levy charges, alongside the emission coefficients it charges on."""

    def __init__(self) -> None:
        super().__init__()

        self._level: FloatArray = EMPTY_FLOAT  # levy level, USD/ton emission

    def initialize(self, length: int, emission_names: Iterable[str]) -> None:
        self._initialize_expectation(length)
        self._initialize_policy_expectation(emission_names)

        self._level = self._default_array()

    def set_level(self, idx: int, level: FloatLike) -> None:
        self._level[idx:] = level

    def get_level(self, idx: int) -> float:
        level: float = self._level[idx]
        return level
