# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""VesselResults, the output storage the Vessel node reports its results from."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.results._fuel_consumer_results import _FuelConsumerResults
from navigate.core.results._transport_results import _TransportResults
from navigate.core.results.base_results import result

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.results.results_context import ResultsContext
    from navigate.util.types_ import BoolArray, FloatArray


@dataclass(eq=False, repr=False)
class VesselResults(_FuelConsumerResults, _TransportResults):
    """Energy, emissions, speeds, expenses and charter rates of one vessel type."""

    lifetime: FloatArray = result("years")
    lead_time: FloatArray = result("years")

    # investment signals: energy-weighted mean of the smoothed energy-conservation duals
    investment_signal_technology: FloatArray = result("USD/GJ")
    investment_signal_speed: FloatArray = result("USD/GJ")

    technology_cost: FloatArray = result("USD/year")

    # freight and charter rates
    asset_charter_rate: FloatArray = result("USD/year")
    cargo_charter_rate: FloatArray = result("USD/year")
    investment_freight_rate: FloatArray = result("USD/cargo-mile")

    # savings against the year-0 raw energy
    speed_energy_saving: FloatArray = result("-")
    operational_energy_saving: FloatArray = result("-")
    technology_energy_saving: FloatArray = result("-")
    energy_saving: FloatArray = result("-")

    # fleet membership and cost state
    in_fleet: BoolArray = result("-")
    cost_is_calculated: BoolArray = field(init=False)

    def initialize(
        self,
        context: ResultsContext,
        regulation_names: Sequence[str],
        levy_names: Sequence[str],
    ) -> None:
        """
        Initialize the vessel results' storage arrays and lookups.

        Parameters
        ----------
        context
            Timeline, fuels and emissions of the run.
        regulation_names
            Names of all regulations in the simulation.
        levy_names
            Names of all levies in the simulation.
        """
        self.context = context

        self._initialize_fuel_consumer(regulation_names, levy_names)
        self._initialize_transport()

        self.lifetime = self._default_array()
        self.lead_time = self._default_array()

        self.investment_signal_technology = self._default_array(default=np.nan)
        self.investment_signal_speed = self._default_array(default=np.nan)

        self.technology_cost = self._default_array()

        self.asset_charter_rate = self._default_array(default=np.nan)
        self.cargo_charter_rate = self._default_array(default=np.nan)
        self.investment_freight_rate = self._default_array(default=np.nan)

        self.in_fleet = self._default_bool_array()
        self.cost_is_calculated = self._default_bool_array()
