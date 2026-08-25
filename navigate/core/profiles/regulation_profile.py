# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.initial_values import EMPTY_FLOAT, EMPTY_NAN
from navigate.core.profiles._base_profile import _BaseProfile
from navigate.util import extract_from_dict

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel


class RegulationProfile(_BaseProfile):
    def __init__(self):
        super().__init__()

        # unit costs
        self._remedial_cost: np.ndarray = EMPTY_NAN         # USD/ton, cost of a remedial compliance unit
        self._flexibility_cost: np.ndarray = EMPTY_NAN      # USD/ton, cost of flexible/surplus compliance unit

        # thresholds
        self._vessel_threshold: dict[str, np.ndarray] = {}         # individual vessel threshold in measure unit
        self._shared_threshold: np.ndarray = EMPTY_NAN    # shared threshold in measure unit

        # adjusted thresholds (from threshold adjustment when non-compliant)
        self._adjusted_vessel_threshold: dict[str, np.ndarray] = {}              # vessel adjusted threshold
        self._adjusted_shared_threshold: np.ndarray = EMPTY_NAN         # shared adjusted threshold

        # allowances
        self._vessel_allowance: dict[str, np.ndarray] = {}         # ton/year, individual vessel allowance
        self._shared_allowance: np.ndarray = EMPTY_NAN     # ton/year, shared allowance

        # compliance
        self._vessel_compliance: dict[str, np.ndarray] = {}        # individual vessel compliance in measure unit
        self._shared_compliance: np.ndarray = EMPTY_NAN    # shared compliance in measure unit
        self._vessel_units: dict[str, np.ndarray] = {}             # ton/year, vessel compliance in absolute emissions
        self._shared_units: np.ndarray = EMPTY_NAN         # ton/year, shared compliance in absolute emissions

        # traded units
        self._surplus_units: np.ndarray = EMPTY_FLOAT         # surplus units generated, ton emissions/year
        self._flexibility_units: np.ndarray = EMPTY_FLOAT     # flexibility units traded, ton emissions/year
        self._remedial_units: np.ndarray = EMPTY_FLOAT        # remedial units sold, ton emissions/year

        # compliance expenses
        self._surplus_revenue: np.ndarray = EMPTY_FLOAT       # total revenue from selling surplus units, USD/year
        self._flexibility_expenses: np.ndarray = EMPTY_FLOAT  # total expenses from flexibility units, USD/year
        self._remedial_expenses: np.ndarray = EMPTY_FLOAT     # total expenses from remedial units, USD/year

    def initialize(self, timeline: np.ndarray, vessels: dict[str, Vessel]) -> None:

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

    def set_vessel_threshold(self, idx: int, vessel_name: str, vessel_threshold: float) -> None:
        self._vessel_threshold[vessel_name][idx] = vessel_threshold

    def set_shared_threshold(self, idx: int, shared_threshold: float) -> None:
        self._shared_threshold[idx] = shared_threshold

    def set_adjusted_vessel_threshold(self, idx: int, vessel_name: str, threshold: float) -> None:
        self._adjusted_vessel_threshold[vessel_name][idx] = threshold

    def get_adjusted_vessel_threshold(
            self, vessel_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._adjusted_vessel_threshold, vessel_name, idx)

    def set_adjusted_shared_threshold(self, idx: int, threshold: float) -> None:
        self._adjusted_shared_threshold[idx] = threshold

    def get_adjusted_shared_threshold(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._adjusted_shared_threshold[idx]

    def set_vessel_allowance(self, idx: int, vessel_name: str, vessel_allowance: float) -> None:
        self._vessel_allowance[vessel_name][idx] = vessel_allowance

    def set_shared_allowance(self, idx: int, shared_allowance: float) -> None:
        self._shared_allowance[idx] = shared_allowance

    def set_vessel_compliance(self, idx: int, vessel_name: str, compliance: float) -> None:
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

    def add_remedial_units(self, idx: int, units: float) -> None:
        self._remedial_units[idx] += units

    def set_surplus_revenue(self, idx: int, revenue: float) -> None:
        self._surplus_revenue[idx] = revenue

    def set_flexibility_expenses(self, idx: int, expenses: float) -> None:
        self._flexibility_expenses[idx] = expenses

    def add_remedial_expenses(self, idx: int, expenses: float) -> None:
        self._remedial_expenses[idx] += expenses

    def get_remedial_cost(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._remedial_cost[idx]

    def get_flexibility_cost(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._flexibility_cost[idx]

    def get_vessel_threshold(
            self, vessel_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._vessel_threshold, vessel_name, idx)

    def get_shared_threshold(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._shared_threshold[idx]

    def get_vessel_allowance(
            self, vessel_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._vessel_allowance, vessel_name, idx)

    def get_shared_allowance(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._shared_allowance[idx]

    def get_vessel_compliance(
            self, vessel_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._vessel_compliance, vessel_name, idx)

    def get_shared_compliance(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._shared_compliance[idx]

    def get_vessel_units(
            self, vessel_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._vessel_units, vessel_name, idx)

    def get_shared_units(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._shared_units[idx]

    def get_surplus_units(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._surplus_units[idx]

    def get_flexibility_units(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._flexibility_units[idx]

    def get_remedial_units(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._remedial_units[idx]

    def get_non_compliance_units(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._flexibility_units[idx] + self._remedial_units[idx]

    def get_surplus_revenue(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._surplus_revenue[idx]

    def get_flexibility_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._flexibility_expenses[idx]

    def get_remedial_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._remedial_expenses[idx]
