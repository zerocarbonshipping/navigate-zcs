# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Iterable

import numpy as np

from navigate.core.expectations._policy_expectation import _PolicyExpectation
from navigate.core.misc import EMPTY_FLOAT


class LevyExpectation(_PolicyExpectation):
    def __init__(self):
        super().__init__()

        self._level: np.ndarray = EMPTY_FLOAT

    def initialize(self, length: int, emission_names: Iterable[str]) -> None:
        self._initialize_expectation(length)
        self._initialize_policy_expectation(emission_names)

        self._level = self._default_array()

    def set_level(self, idx: int, level: np.ndarray) -> None:
        self._level[idx:] = level

    def get_level(self, idx: int) -> np.ndarray:
        return self._level[idx]
