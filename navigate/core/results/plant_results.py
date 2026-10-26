# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""PlantResults, the output storage of the Plant node."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.results.base_results import BaseResults, result

if TYPE_CHECKING:
    from navigate.core.results.results_context import ResultsContext
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class PlantResults(BaseResults):
    """Production cost and well-to-tank emissions of the fuel one plant makes."""

    # cost of the fuel produced
    investment_cost: FloatArray = result("USD/t")
    instantaneous_cost: FloatArray = result("USD/t")

    # well-to-tank emissions per ton of fuel: the emissions are written, their
    # CO2-equivalents computed from them
    investment_wtt: dict[str, FloatArray] = field(init=False)
    instantaneous_wtt: dict[str, FloatArray] = field(init=False)

    equivalent_investment_wtt: dict[str, FloatArray] = result("tCO2e/t")
    equivalent_instantaneous_wtt: dict[str, FloatArray] = result("tCO2e/t")

    def initialize(self, context: ResultsContext) -> None:
        """
        Allocate the plant results' storage.

        Parameters
        ----------
        context
            Timeline, fuels and emissions of the run.
        """
        self.context = context

        self.investment_cost = self._default_array(default=np.nan)
        self.instantaneous_cost = self._default_array(default=np.nan)

        self.investment_wtt = self._default_dict(context.emissions, default=np.nan)
        self.instantaneous_wtt = self._default_dict(context.emissions, default=np.nan)
