# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""PortResults, the output storage the Port node reports its results from."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from navigate.core.results._fuel_infrastructure_results import (
    _FuelInfrastructureResults,
)
from navigate.core.results.base_results import result

if TYPE_CHECKING:
    from navigate.core.results.results_context import ResultsContext
    from navigate.util.types_ import BoolArray, FloatArray


@dataclass(eq=False, repr=False)
class PortResults(_FuelInfrastructureResults):
    """Bunkering permissions, prices and well-to-tank emissions at one port."""

    bunkering_allowed: dict[str, BoolArray] = result("-")
    bunker_price: dict[str, FloatArray] = result("USD/t")

    # well-to-tank emissions per ton of the fuel bunkered, keyed by
    # (fuel, emission): the emission is written, its CO2-equivalent computed
    bunker_wtt: dict[tuple[str, str], FloatArray] = result("t/t")
    equivalent_bunker_wtt: dict[tuple[str, str], FloatArray] = result("tCO2e/t")

    def initialize(self, context: ResultsContext) -> None:
        """
        Initialize the port results' storage arrays.

        Parameters
        ----------
        context
            Timeline, fuels and emissions of the run.
        """
        self.context = context

        self._initialize_fuel_infrastructure()

        self.bunkering_allowed = self._default_bool_dict(context.fuels)
        self.bunker_price = self._default_dict(context.fuels)

        self.bunker_wtt = self._default_tuple_dict(context.fuels, context.emissions)
