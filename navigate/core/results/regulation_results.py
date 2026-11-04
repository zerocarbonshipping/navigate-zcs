# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""RegulationResults, the output storage of the Regulation node."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.results.base_results import BaseResults, Unit, result

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.results.results_context import ResultsContext
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class RegulationResults(BaseResults):
    """Thresholds, compliance and the units traded under one regulation."""

    # cost of one compliance unit
    remedial_cost: FloatArray = result(Unit.USD_PER_TCO2E)
    flexibility_cost: FloatArray = result(Unit.USD_PER_TCO2E)

    # thresholds, in the measure unit of the regulation
    vessel_threshold: dict[str, FloatArray] = result(Unit.MEASURE)
    shared_threshold: FloatArray = result(Unit.MEASURE)

    # thresholds after adjustment for non-compliance, in the measure unit
    adjusted_vessel_threshold: dict[str, FloatArray] = result(Unit.MEASURE)
    adjusted_shared_threshold: FloatArray = result(Unit.MEASURE)

    # allowances, CO2-equivalent under the regulation's global warming potential
    vessel_allowance: dict[str, FloatArray] = result(Unit.TCO2E_PER_YEAR)
    shared_allowance: FloatArray = result(Unit.TCO2E_PER_YEAR)

    # compliance, in the measure unit of the regulation
    vessel_compliance: dict[str, FloatArray] = result(Unit.MEASURE)
    shared_compliance: FloatArray = result(Unit.MEASURE)

    # compliance in absolute emissions, whatever the measure
    vessel_units: dict[str, FloatArray] = result(Unit.TCO2E_PER_YEAR)
    shared_units: FloatArray = result(Unit.TCO2E_PER_YEAR)

    # traded units
    surplus_units: FloatArray = result(Unit.TCO2E_PER_YEAR)
    flexibility_units: FloatArray = result(Unit.TCO2E_PER_YEAR)
    remedial_units: FloatArray = result(Unit.TCO2E_PER_YEAR)
    non_compliance_units: FloatArray = result(Unit.TCO2E_PER_YEAR)

    # compliance expenses
    surplus_revenue: FloatArray = result(Unit.USD_PER_YEAR)
    flexibility_expenses: FloatArray = result(Unit.USD_PER_YEAR)
    remedial_expenses: FloatArray = result(Unit.USD_PER_YEAR)

    def initialize(self, context: ResultsContext, vessel_names: Sequence[str]) -> None:
        """
        Allocate the regulation results' storage.

        Parameters
        ----------
        context
            Timeline, fuels and emissions of the run.
        vessel_names
            Names of all vessels in the simulation.
        """
        self.context = context

        self.remedial_cost = self._default_array(default=np.nan)
        self.flexibility_cost = self._default_array(default=np.nan)

        self.vessel_threshold = self._default_dict(vessel_names, default=np.nan)
        self.shared_threshold = self._default_array(default=np.nan)

        self.adjusted_vessel_threshold = self._default_dict(
            vessel_names, default=np.nan
        )
        self.adjusted_shared_threshold = self._default_array(default=np.nan)

        self.vessel_allowance = self._default_dict(vessel_names, default=np.nan)
        self.shared_allowance = self._default_array(default=np.nan)

        self.vessel_compliance = self._default_dict(vessel_names, default=np.nan)
        self.shared_compliance = self._default_array(default=np.nan)

        self.vessel_units = self._default_dict(vessel_names, default=np.nan)
        self.shared_units = self._default_array(default=np.nan)

        self.surplus_units = self._default_array()
        self.flexibility_units = self._default_array()
        self.remedial_units = self._default_array()

        self.surplus_revenue = self._default_array()
        self.flexibility_expenses = self._default_array()
        self.remedial_expenses = self._default_array()
