# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""ProducerResults, the output storage the Producer node reports results from."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.results._base_results import result
from navigate.core.results._plant_aggregate_results import _PlantAggregateResults

if TYPE_CHECKING:
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.process import Process
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
        feedstocks: dict[str, Feedstock],
        processes: dict[str, Process],
    ) -> None:
        """
        Initialize the producer results' storage arrays and lookups.

        Parameters
        ----------
        context
            Timeline, fuels and emissions of the run.
        feedstocks
            All feedstocks in the simulation.
        processes
            All processes in the simulation.
        """
        self._initialize_base(context)
        self._initialize_fuel_producer(feedstocks, processes)
        self._initialize_plant_aggregate()

        self.maximum_development = self._default_array(default=np.nan)
        self.development = self._default_array()

        self.fair_share_fuel_fraction = self._default_dict(context.fuels)
