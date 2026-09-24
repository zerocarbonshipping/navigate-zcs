# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""RegulationProfile, the output storage the Regulation node reports from."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.initial_values import EMPTY_FLOAT, EMPTY_NAN
from navigate.core.profiles._base_profile import _BaseProfile

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray


class RegulationProfile(_BaseProfile):
    """Thresholds, compliance and the units traded under one regulation."""

    def __init__(self) -> None:
        super().__init__()

        # cost of one compliance unit, USD/ton
        self._remedial_cost: FloatArray = EMPTY_NAN  # remedial unit
        self._flexibility_cost: FloatArray = EMPTY_NAN  # flexible or surplus unit

        # thresholds, in the measure unit of the regulation
        self._vessel_threshold: dict[str, FloatArray] = {}  # per vessel
        self._shared_threshold: FloatArray = EMPTY_NAN  # shared

        # thresholds after adjustment for non-compliance, in the measure unit
        self._adjusted_vessel_threshold: dict[str, FloatArray] = {}  # per vessel
        self._adjusted_shared_threshold: FloatArray = EMPTY_NAN  # shared

        # allowances, ton/year
        self._vessel_allowance: dict[str, FloatArray] = {}  # per vessel
        self._shared_allowance: FloatArray = EMPTY_NAN  # shared

        # compliance, in the measure unit of the regulation
        self._vessel_compliance: dict[str, FloatArray] = {}  # per vessel
        self._shared_compliance: FloatArray = EMPTY_NAN  # shared

        # compliance in absolute emissions, ton/year
        self._vessel_units: dict[str, FloatArray] = {}  # per vessel
        self._shared_units: FloatArray = EMPTY_NAN  # shared

        # traded units, ton emissions/year
        self._surplus_units: FloatArray = EMPTY_FLOAT  # generated
        self._flexibility_units: FloatArray = EMPTY_FLOAT  # traded
        self._remedial_units: FloatArray = EMPTY_FLOAT  # sold

        # compliance expenses, USD/year
        self._surplus_revenue: FloatArray = EMPTY_FLOAT  # revenue from surplus units
        self._flexibility_expenses: FloatArray = EMPTY_FLOAT  # flexibility units
        self._remedial_expenses: FloatArray = EMPTY_FLOAT  # remedial units

    def initialize(self, timeline: FloatArray, vessels: dict[str, Vessel]) -> None:
        self._initialize_base(timeline)

        self._flexibility_cost = self._default_array(default=np.nan)
        self._remedial_cost = self._default_array(default=np.nan)

        self._vessel_threshold = self._default_dict(vessels, default=np.nan)
        self._shared_threshold = self._default_array(default=np.nan)

        self._adjusted_vessel_threshold = self._default_dict(vessels, default=np.nan)
        self._adjusted_shared_threshold = self._default_array(default=np.nan)

        self._vessel_allowance = self._default_dict(vessels, default=np.nan)
        self._shared_allowance = self._default_array(default=np.nan)

        self._vessel_compliance = self._default_dict(vessels, default=np.nan)
        self._shared_compliance = self._default_array(default=np.nan)
        self._vessel_units = self._default_dict(vessels, default=np.nan)
        self._shared_units = self._default_array(default=np.nan)

        self._surplus_units = self._default_array()
        self._flexibility_units = self._default_array()
        self._remedial_units = self._default_array()

        self._surplus_revenue = self._default_array()
        self._flexibility_expenses = self._default_array()
        self._remedial_expenses = self._default_array()

    def set_remedial_cost(self, idx: int, cost: float) -> None:
        self._remedial_cost[idx] = cost

    def set_flexibility_cost(self, idx: int, cost: float) -> None:
        self._flexibility_cost[idx] = cost

    def set_vessel_threshold(
        self, idx: int, vessel_name: str, vessel_threshold: float
    ) -> None:
        self._vessel_threshold[vessel_name][idx] = vessel_threshold

    def set_shared_threshold(self, idx: int, shared_threshold: float) -> None:
        self._shared_threshold[idx] = shared_threshold

    def set_adjusted_vessel_threshold(
        self, idx: int, vessel_name: str, threshold: float
    ) -> None:
        self._adjusted_vessel_threshold[vessel_name][idx] = threshold

    def get_adjusted_vessel_threshold(self) -> dict[str, FloatArray]:
        return dict(self._adjusted_vessel_threshold)

    def set_adjusted_shared_threshold(self, idx: int, threshold: float) -> None:
        self._adjusted_shared_threshold[idx] = threshold

    def get_adjusted_shared_threshold(self) -> FloatArray:
        return self._adjusted_shared_threshold

    def set_vessel_allowance(
        self, idx: int, vessel_name: str, vessel_allowance: float
    ) -> None:
        self._vessel_allowance[vessel_name][idx] = vessel_allowance

    def set_shared_allowance(self, idx: int, shared_allowance: float) -> None:
        self._shared_allowance[idx] = shared_allowance

    def set_vessel_compliance(
        self, idx: int, vessel_name: str, compliance: float
    ) -> None:
        self._vessel_compliance[vessel_name][idx] = compliance

    def set_shared_compliance(self, idx: int, compliance: float) -> None:
        self._shared_compliance[idx] = compliance

    def set_vessel_units(self, idx: int, vessel_name: str, units: float) -> None:
        self._vessel_units[vessel_name][idx] = units

    def set_shared_units(self, idx: int, units: float) -> None:
        self._shared_units[idx] = units

    def set_surplus_units(self, idx: int, units: float) -> None:
        self._surplus_units[idx] = units

    def set_flexibility_units(self, idx: int, units: float) -> None:
        self._flexibility_units[idx] = units

    def add_remedial_units(self, units: float, idx: int | slice = np.s_[:]) -> None:
        self._remedial_units[idx] += units

    def set_surplus_revenue(self, idx: int, revenue: float) -> None:
        self._surplus_revenue[idx] = revenue

    def set_flexibility_expenses(self, idx: int, expenses: float) -> None:
        self._flexibility_expenses[idx] = expenses

    def add_remedial_expenses(
        self, expenses: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._remedial_expenses[idx] += expenses

    def get_remedial_cost(self) -> FloatArray:
        return self._remedial_cost

    def get_flexibility_cost(self) -> FloatArray:
        return self._flexibility_cost

    def get_vessel_threshold(self) -> dict[str, FloatArray]:
        return dict(self._vessel_threshold)

    def get_shared_threshold(self) -> FloatArray:
        return self._shared_threshold

    def get_vessel_allowance(self) -> dict[str, FloatArray]:
        return dict(self._vessel_allowance)

    def get_shared_allowance(self) -> FloatArray:
        return self._shared_allowance

    def get_vessel_compliance(self) -> dict[str, FloatArray]:
        return dict(self._vessel_compliance)

    def get_shared_compliance(self) -> FloatArray:
        return self._shared_compliance

    def get_vessel_units(self) -> dict[str, FloatArray]:
        return dict(self._vessel_units)

    def get_shared_units(self) -> FloatArray:
        return self._shared_units

    def get_surplus_units(self) -> FloatArray:
        return self._surplus_units

    def get_flexibility_units(self) -> FloatArray:
        return self._flexibility_units

    def get_remedial_units(self) -> FloatArray:
        return self._remedial_units

    def get_non_compliance_units(self) -> FloatArray:
        return self._flexibility_units + self._remedial_units

    def get_surplus_revenue(self) -> FloatArray:
        return self._surplus_revenue

    def get_flexibility_expenses(self) -> FloatArray:
        return self._flexibility_expenses

    def get_remedial_expenses(self) -> FloatArray:
        return self._remedial_expenses
