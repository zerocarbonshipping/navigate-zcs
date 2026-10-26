# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""GlobalResults, the model-wide output storage the simulation fills."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from navigate.core.enum_ import TimingID
from navigate.core.results._base_results import result
from navigate.core.results._fuel_infrastructure_results import (
    _FuelInfrastructureResults,
)
from navigate.core.results._plant_aggregate_results import _PlantAggregateResults
from navigate.core.results._vessel_aggregate_results import _VesselAggregateResults

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.results.results_context import ResultsContext
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class GlobalResults(
    _VesselAggregateResults, _PlantAggregateResults, _FuelInfrastructureResults
):
    """Totals over every vessel, plant and port, plus the run's computational time."""

    computational_time: dict[TimingID, FloatArray] = result("s/year", per_step=True)

    def initialize(
        self,
        context: ResultsContext,
        feedstock_names: Sequence[str],
        process_names: Sequence[str],
        regulation_names: Sequence[str],
        levy_names: Sequence[str],
    ) -> None:
        """
        Initialize the global results' storage arrays and lookups.

        Parameters
        ----------
        context
            Timeline, fuels and emissions of the run.
        feedstock_names
            Names of all feedstocks in the simulation.
        process_names
            Names of all processes in the simulation.
        regulation_names
            Names of all regulations in the simulation.
        levy_names
            Names of all levies in the simulation.
        """
        self._initialize_base(context)
        self._initialize_fuel_consumer(regulation_names, levy_names)
        self._initialize_fuel_producer(feedstock_names, process_names)
        self._initialize_fuel_infrastructure()
        self._initialize_vessel_aggregate()
        self._initialize_plant_aggregate()

        self.computational_time = self._default_dict(TimingID)
