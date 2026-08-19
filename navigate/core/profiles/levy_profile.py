# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import numpy as np

from navigate.core.misc import EMPTY_FLOAT
from navigate.core.profiles._policy_profile import _PolicyProfile


class LevyProfile(_PolicyProfile):
    def __init__(self):
        super().__init__()

        self._collected: np.ndarray = EMPTY_FLOAT

    def initialize(self, timeline: np.ndarray) -> None:
        self._initialize_base(timeline)
        self._initialize_policy_profile()

        self._collected = self._default_array()

    def add_collected(self, idx: int, collected: float) -> None:
        self._collected[idx] += collected

    def set_collected(self, idx: int, collected: float) -> None:
        self._collected[idx] = collected

    def get_collected(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._collected[idx]
