# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""LevyProfile, the output storage the Levy node reports its results from."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.initial_values import EMPTY_FLOAT
from navigate.core.profiles._base_profile import _BaseProfile

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray


class LevyProfile(_BaseProfile):
    """Revenue one levy collected over the timeline."""

    def __init__(self) -> None:
        super().__init__()

        self._collected: FloatArray = EMPTY_FLOAT

    def initialize(self, timeline: FloatArray) -> None:
        self._initialize_base(timeline)

        self._collected = self._default_array()

    def add_collected(self, collected: float, idx: int | slice = np.s_[:]) -> None:
        self._collected[idx] += collected

    def set_collected(self, idx: int, collected: float) -> None:
        self._collected[idx] = collected

    def get_collected(self) -> FloatArray:
        return self._collected
