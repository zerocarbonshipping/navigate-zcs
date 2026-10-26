# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""LevyResults, the output storage of the Levy node."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from navigate.core.results.base_results import BaseResults, result

if TYPE_CHECKING:
    from navigate.core.results.results_context import ResultsContext
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class LevyResults(BaseResults):
    """Revenue one levy collected over the timeline."""

    # negative where the levy pays out a subsidy
    collected: FloatArray = result("USD/year")

    def initialize(self, context: ResultsContext) -> None:
        """
        Allocate the levy results' storage.

        Parameters
        ----------
        context
            Timeline, fuels and emissions of the run.
        """
        self.context = context
        self.collected = self._default_array()
