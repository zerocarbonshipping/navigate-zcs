# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The results layer that sums plant capital over a producer or the model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from navigate.core.results._fuel_producer_results import _FuelProducerResults
from navigate.core.results.base_results import accumulate, result

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class _PlantAggregateResults(_FuelProducerResults):
    """Tied-up capital of the plants in a producer's results or the global results."""

    plant_tied_capital: FloatArray = result("USD")

    def _initialize_plant_aggregate(self) -> None:
        self.plant_tied_capital = self._default_array()

    def add_plant_aggregate_results(self, results: _PlantAggregateResults) -> None:
        """
        Add another plant aggregate's results, its fuel producer results included.

        Parameters
        ----------
        results
            Plant aggregate results from another node.
        """
        self.add_fuel_producer_results(results)

        accumulate(self.plant_tied_capital, results.plant_tied_capital)
