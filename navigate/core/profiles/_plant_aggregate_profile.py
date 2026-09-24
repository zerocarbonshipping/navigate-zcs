# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The profile layer that sums plant capital over a producer or the model."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.initial_values import EMPTY_FLOAT
from navigate.core.profiles._fuel_producer_profile import _FuelProducerProfile

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray


class _PlantAggregateProfile(_FuelProducerProfile):
    """Capital tied up in the plants aggregated into a producer or the manager."""

    def __init__(self) -> None:
        super().__init__()

        self._plant_tied_capital: FloatArray = EMPTY_FLOAT

    def _initialize_plant_aggregate(self) -> None:
        self._plant_tied_capital = self._default_array()

    def add_plant_aggregate_profile(
        self, profile: _PlantAggregateProfile, idx: int | slice = np.s_[:]
    ) -> None:
        """
        Add another plant aggregate profile's values into this one.

        Parameters
        ----------
        profile
            Plant aggregate profile from another node.
        idx
            Time-step index or slice.
        """
        self._plant_tied_capital[idx] += profile._plant_tied_capital[idx]

    def add_plant_tied_capital(
        self, tied_capital: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._plant_tied_capital[idx] += tied_capital

    def get_plant_tied_capital(self) -> FloatArray:
        return self._plant_tied_capital
