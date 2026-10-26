# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""ProducerResults, the output storage of the Producer node."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.results._plant_aggregate_results import _PlantAggregateResults
from navigate.core.results.base_results import result

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.results.results_context import ResultsContext
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class ProducerResults(_PlantAggregateResults):
    """Production, feedstock use and plant development of one fuel producer."""

    # plants added to the development pipeline
    maximum_development: FloatArray = result("plants/year")
    development: FloatArray = result("plants/year", per_step=True)

    fair_share_fuel_fraction: dict[str, FloatArray] = result("-")

    def initialize(
        self,
        context: ResultsContext,
        feedstock_names: Sequence[str],
        process_names: Sequence[str],
    ) -> None:
        """
        Allocate the producer results' storage.

        Parameters
        ----------
        context
            Timeline, fuels and emissions of the run.
        feedstock_names
            Names of all feedstocks in the simulation.
        process_names
            Names of all processes in the simulation.
        """
        self.context = context

        self._initialize_fuel_producer(feedstock_names, process_names)
        self._initialize_plant_aggregate()

        self.maximum_development = self._default_array(default=np.nan)
        self.development = self._default_array()

        self.fair_share_fuel_fraction = self._default_dict(context.fuels)
