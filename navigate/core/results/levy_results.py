# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""LevyResults, the output storage the Levy node reports its results from."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from navigate.core.results._base_results import _BaseResults, result

if TYPE_CHECKING:
    from navigate.core.results.results_context import ResultsContext
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class LevyResults(_BaseResults):
    """Revenue one levy collected over the timeline."""

    # negative where the levy pays out a subsidy
    collected: FloatArray = result("USD/year")

    def initialize(self, context: ResultsContext) -> None:
        """
        Initialize the levy results' storage arrays.

        Parameters
        ----------
        context
            Timeline, fuels and emissions of the run.
        """
        self._initialize_base(context)
        self.collected = self._default_array()
