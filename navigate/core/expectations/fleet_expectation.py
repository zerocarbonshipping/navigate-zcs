# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Fleet node, read by the fuel domain and the bunkering LP."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import FuelTypeID
from navigate.core.expectations._expectation import _Expectation
from navigate.core.initial_values import EMPTY_FLOAT
from navigate.util import slice_dict

if TYPE_CHECKING:
    from navigate.core.nodes.fuel import Fuel
    from navigate.util.types_ import FloatArray, FloatLike, Index


class FleetExpectation(_Expectation):
    """Vessel multipliers, expected fuel demand and realized fuel-type totals."""

    def __init__(self) -> None:
        super().__init__()

        self._existing_multipliers: dict[str, FloatArray] = {}
        self._newbuild_multipliers: dict[str, FloatArray] = {}

        self._fuel_demand: dict[str, FloatArray] = {}

        self._fuel_type_demand: dict[FuelTypeID, float] = {}
        self._fuel_type_supply: dict[FuelTypeID, float] = {}

        self._uptakes: FloatArray = EMPTY_FLOAT

    def initialize(
        self, length: int, vessel_names: list[str], fuels: dict[str, Fuel]
    ) -> None:
        self._initialize_expectation(length)

        self._existing_multipliers = self._default_dict_array(vessel_names)
        self._newbuild_multipliers = self._default_dict_array(vessel_names)

        self._fuel_demand = self._default_dict_array(fuels)

        self._fuel_type_demand = self._default_dict_float(FuelTypeID)
        self._fuel_type_supply = self._default_dict_float(FuelTypeID)

        self._uptakes = self._default_2d_array(len(vessel_names))

    def reset_fuel_type_totals(self) -> None:
        self._reset_dict_float(self._fuel_type_demand)
        self._reset_dict_float(self._fuel_type_supply)

    def set_existing_multipliers(
        self, idx: int, vessel_name: str, multipliers: FloatLike
    ) -> None:
        self._existing_multipliers[vessel_name][idx:] = multipliers

    def set_newbuild_multipliers(
        self, idx: int, vessel_name: str, multipliers: FloatLike
    ) -> None:
        self._newbuild_multipliers[vessel_name][idx:] = multipliers

    def set_fuel_demand(self, idx: int, fuel_name: str, demand: float) -> None:
        self._fuel_demand[fuel_name][idx] = demand

    def add_fuel_type_demand(self, fuel_type: FuelTypeID, demand: float) -> None:
        self._fuel_type_demand[fuel_type] += demand

    def add_fuel_type_supply(self, fuel_type: FuelTypeID, supply: float) -> None:
        self._fuel_type_supply[fuel_type] += supply

    def set_uptakes(self, idx: int, uptakes: FloatArray) -> None:
        self._uptakes[:, idx] = uptakes

    def get_existing_multipliers(
        self, vessel_name: str, idx: Index = np.s_[:]
    ) -> FloatLike:
        return self._existing_multipliers[vessel_name][idx]

    def get_expected_multipliers(
        self, vessel_name: str, idx: Index = np.s_[:]
    ) -> FloatLike:
        return (
            self._existing_multipliers[vessel_name][idx]
            + self._newbuild_multipliers[vessel_name][idx]
        )

    def get_fuel_demand(self, idx: Index = np.s_[:]) -> dict[str, FloatLike]:
        return slice_dict(self._fuel_demand, idx)

    def get_fuel_type_demand(self, fuel_type: FuelTypeID) -> float:
        return self._fuel_type_demand[fuel_type]

    def get_fuel_type_supply(self, fuel_type: FuelTypeID) -> float:
        return self._fuel_type_supply[fuel_type]

    def get_uptakes(self, idx: int) -> FloatArray:
        return self._uptakes[:, : (idx + 1)]
