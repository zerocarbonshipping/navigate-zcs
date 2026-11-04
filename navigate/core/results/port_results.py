# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""PortResults, the output storage of the Port node."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from navigate.core.results._fuel_infrastructure_results import (
    _FuelInfrastructureResults,
)
from navigate.core.results.base_results import Unit, result

if TYPE_CHECKING:
    from navigate.core.results.results_context import ResultsContext
    from navigate.util.types_ import BoolArray, FloatArray


@dataclass(eq=False, repr=False)
class PortResults(_FuelInfrastructureResults):
    """Bunkering permissions, prices and well-to-tank emissions at one port."""

    bunkering_allowed: dict[str, BoolArray] = result(Unit.DIMENSIONLESS)
    bunker_price: dict[str, FloatArray] = result(Unit.USD_PER_TON)

    # well-to-tank emissions per ton of the fuel bunkered, keyed by
    # (fuel, emission): the emission is written, its CO2-equivalent computed
    bunker_wtt: dict[tuple[str, str], FloatArray] = result(Unit.TON_PER_TON)
    equivalent_bunker_wtt: dict[tuple[str, str], FloatArray] = result(
        Unit.TCO2E_PER_TON
    )

    def initialize(self, context: ResultsContext) -> None:
        """
        Allocate the port results' storage.

        Parameters
        ----------
        context
            Timeline, fuels and emissions of the run.
        """
        self.context = context
        fuels = context.fuels

        self._initialize_fuel_infrastructure()

        self.bunkering_allowed = self._default_bool_dict(fuels)
        self.bunker_price = self._default_dict(fuels)

        self.bunker_wtt = self._default_tuple_dict(fuels, context.emissions)
