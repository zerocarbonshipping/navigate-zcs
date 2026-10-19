# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The profile layer that sums plant capital over a producer or the model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from navigate.core.profiles._base_profile import accumulate, result
from navigate.core.profiles._fuel_producer_profile import _FuelProducerProfile

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class _PlantAggregateProfile(_FuelProducerProfile):
    """Tied-up capital of the plants in a producer's profile or the global profile."""

    plant_tied_capital: FloatArray = result("USD")

    def _initialize_plant_aggregate(self) -> None:
        self.plant_tied_capital = self._default_array()

    def add_plant_aggregate_profile(self, profile: _PlantAggregateProfile) -> None:
        """
        Add another plant aggregate profile's values into this one.

        Parameters
        ----------
        profile
            Plant aggregate profile from another node.
        """
        accumulate(self.plant_tied_capital, profile.plant_tied_capital)
