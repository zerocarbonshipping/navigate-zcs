# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""RegulationProfile, the output storage the Regulation node reports from."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.profiles._base_profile import _BaseProfile, result

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.profiles.profile_context import ProfileContext
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class RegulationProfile(_BaseProfile):
    """Thresholds, compliance and the units traded under one regulation."""

    # cost of one compliance unit
    remedial_cost: FloatArray = result("USD/tCO2e")
    flexibility_cost: FloatArray = result("USD/tCO2e")

    # thresholds, in the measure unit of the regulation
    vessel_threshold: dict[str, FloatArray] = result("measure")
    shared_threshold: FloatArray = result("measure")

    # thresholds after adjustment for non-compliance, in the measure unit
    adjusted_vessel_threshold: dict[str, FloatArray] = result("measure")
    adjusted_shared_threshold: FloatArray = result("measure")

    # allowances, CO2-equivalent under the regulation's global warming potential
    vessel_allowance: dict[str, FloatArray] = result("tCO2e/year")
    shared_allowance: FloatArray = result("tCO2e/year")

    # compliance, in the measure unit of the regulation
    vessel_compliance: dict[str, FloatArray] = result("measure")
    shared_compliance: FloatArray = result("measure")

    # compliance in absolute emissions, whatever the measure
    vessel_units: dict[str, FloatArray] = result("tCO2e/year")
    shared_units: FloatArray = result("tCO2e/year")

    # traded units
    surplus_units: FloatArray = result("tCO2e/year")
    flexibility_units: FloatArray = result("tCO2e/year")
    remedial_units: FloatArray = result("tCO2e/year")
    non_compliance_units: FloatArray = result("tCO2e/year")

    # compliance expenses
    surplus_revenue: FloatArray = result("USD/year")
    flexibility_expenses: FloatArray = result("USD/year")
    remedial_expenses: FloatArray = result("USD/year")

    def initialize(self, context: ProfileContext, vessels: dict[str, Vessel]) -> None:
        """
        Initialize the regulation profile's storage arrays.

        Parameters
        ----------
        context
            Timeline, fuels and emissions of the run.
        vessels
            All vessels in the simulation.
        """
        self._initialize_base(context)

        self.flexibility_cost = self._default_array(default=np.nan)
        self.remedial_cost = self._default_array(default=np.nan)

        self.vessel_threshold = self._default_dict(vessels, default=np.nan)
        self.shared_threshold = self._default_array(default=np.nan)

        self.adjusted_vessel_threshold = self._default_dict(vessels, default=np.nan)
        self.adjusted_shared_threshold = self._default_array(default=np.nan)

        self.vessel_allowance = self._default_dict(vessels, default=np.nan)
        self.shared_allowance = self._default_array(default=np.nan)

        self.vessel_compliance = self._default_dict(vessels, default=np.nan)
        self.shared_compliance = self._default_array(default=np.nan)
        self.vessel_units = self._default_dict(vessels, default=np.nan)
        self.shared_units = self._default_array(default=np.nan)

        self.surplus_units = self._default_array()
        self.flexibility_units = self._default_array()
        self.remedial_units = self._default_array()

        self.surplus_revenue = self._default_array()
        self.flexibility_expenses = self._default_array()
        self.remedial_expenses = self._default_array()
