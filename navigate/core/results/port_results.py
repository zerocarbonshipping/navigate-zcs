# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""PortResults, the output storage of the Port node."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.results._fuel_infrastructure_results import (
    _FuelInfrastructureResults,
)
from navigate.core.results.base_results import Unit, result

if TYPE_CHECKING:
    from navigate.core.results.results_context import ResultsContext
    from navigate.util.types_ import BoolArray, FloatArray


@dataclass(eq=False, repr=False)
class PortResults(_FuelInfrastructureResults):
    """Bunkering permissions, limits, prices and well-to-tank emissions at one port."""

    bunkering_allowed: dict[str, BoolArray] = result(Unit.DIMENSIONLESS)
    bunker_price: dict[str, FloatArray] = result(Unit.USD_PER_TON)

    # the bunkering limit's mass is written, its energy computed from it
    bunkering_limit_mass: dict[str, FloatArray] = result(Unit.TON_PER_YEAR)
    bunkering_limit_energy: dict[str, FloatArray] = result(Unit.GJ_PER_YEAR)

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

        # a liquid-market supply stays NaN where the fuel is allowed without a finite
        # bunkering limit, as nothing bounds it
        for fuel_name in context.liquid_market_fuels:
            self.bunker_supply_mass[fuel_name] = self._default_array(default=np.nan)

        self.bunkering_allowed = self._default_bool_dict(fuels)
        self.bunker_price = self._default_dict(fuels)
        self.bunkering_limit_mass = self._default_dict(fuels, default=np.nan)

        self.bunker_wtt = self._default_tuple_dict(fuels, context.emissions)
