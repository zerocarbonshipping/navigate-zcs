# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""VesselResults, the output storage of the Vessel node."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.results._fuel_consumer_results import _FuelConsumerResults
from navigate.core.results._transport_results import _TransportResults
from navigate.core.results.base_results import Unit, result

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.results.results_context import ResultsContext
    from navigate.util.types_ import BoolArray, FloatArray


@dataclass(eq=False, repr=False)
class VesselResults(_FuelConsumerResults, _TransportResults):
    """Energy, emissions, speeds, expenses and charter rates of one vessel type."""

    lifetime: FloatArray = result(Unit.YEARS)
    lead_time: FloatArray = result(Unit.YEARS)

    # investment signals: energy-weighted mean of the smoothed energy-conservation duals
    investment_signal_technology: FloatArray = result(Unit.USD_PER_GJ)
    investment_signal_speed: FloatArray = result(Unit.USD_PER_GJ)

    technology_cost: FloatArray = result(Unit.USD_PER_YEAR)

    # freight and charter rates
    asset_charter_rate: FloatArray = result(Unit.USD_PER_YEAR)
    cargo_charter_rate: FloatArray = result(Unit.USD_PER_YEAR)
    investment_freight_rate: FloatArray = result(Unit.USD_PER_CARGO_MILE)

    # savings against the year-0 raw energy
    speed_energy_saving: FloatArray = result(Unit.DIMENSIONLESS)
    operational_energy_saving: FloatArray = result(Unit.DIMENSIONLESS)
    technology_energy_saving: FloatArray = result(Unit.DIMENSIONLESS)
    energy_saving: FloatArray = result(Unit.DIMENSIONLESS)

    # fleet membership and cost state
    in_fleet: BoolArray = result(Unit.DIMENSIONLESS)
    cost_is_calculated: BoolArray = field(init=False)

    def initialize(
        self,
        context: ResultsContext,
        regulation_names: Sequence[str],
        levy_names: Sequence[str],
    ) -> None:
        """
        Allocate the vessel results' storage.

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
