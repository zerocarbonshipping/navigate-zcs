# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""FleetResults, the output storage the Fleet node reports its results from."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from navigate.core.results._transport_results import _TransportResults
from navigate.core.results._vessel_aggregate_results import _VesselAggregateResults
from navigate.core.results.base_results import result

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.results.results_context import ResultsContext
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class FleetResults(_VesselAggregateResults, _TransportResults):
    """Trade, transport work, fleet composition and speeds of one fleet."""

    trade: FloatArray = result("cargo-miles/year")

    existing_vessels: dict[str, FloatArray] = result("vessels")
    scrap: dict[str, FloatArray] = result("vessels/year", per_step=True)
    newbuilds: dict[str, FloatArray] = result("vessels/year", per_step=True)
    fuel_conversions: dict[tuple[str, str], FloatArray] = result(
        "vessels/year", per_step=True
    )

    # fraction of the vessels carrying a technology, per vessel and technology,
    # across the fleet, among the newbuilds and among the retrofits
    technology_uptake: dict[tuple[str, str], FloatArray] = result("-")
    newbuild_technology_uptake: dict[tuple[str, str], FloatArray] = result("-")
    retrofit_technology_uptake: dict[tuple[str, str], FloatArray] = result("-")
    # fraction of the fleet carrying a technology, weighted by vessel count
    fleet_technology_uptake: dict[str, FloatArray] = result("-")

    def initialize(
        self,
        context: ResultsContext,
        vessel_names: Sequence[str],
        technology_names: Sequence[str],
        regulation_names: Sequence[str],
        levy_names: Sequence[str],
    ) -> None:
        """
        Initialize the fleet results' storage arrays and lookups.

        Parameters
        ----------
        context
            Timeline, fuels and emissions of the run.
        vessel_names
            Names of all vessels in the fleet.
        technology_names
            Names of all technologies in the simulation.
        regulation_names
            Names of all regulations in the simulation.
        levy_names
            Names of all levies in the simulation.
        """
        self.context = context

        self._initialize_fuel_consumer(regulation_names, levy_names)
        self._initialize_vessel_aggregate()
        self._initialize_transport()

        self.trade = self._default_array()

        self.existing_vessels = self._default_dict(vessel_names)
        self.scrap = self._default_dict(vessel_names)
        self.newbuilds = self._default_dict(vessel_names)
        self.fuel_conversions = self._default_tuple_dict(vessel_names, vessel_names)

        self.technology_uptake = self._default_tuple_dict(
            vessel_names, technology_names
        )
        self.newbuild_technology_uptake = self._default_tuple_dict(
            vessel_names, technology_names
        )
        self.retrofit_technology_uptake = self._default_tuple_dict(
            vessel_names, technology_names
        )
