# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Fleet node, read by the fleet, fuel and bunker domains."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID, FuelTypeID
from navigate.core.expectations._expectation import _Expectation
from navigate.util import slice_dict

if TYPE_CHECKING:
    from navigate.core.nodes.fuel import Fuel
    from navigate.util.types_ import FloatArray, FloatLike, Index


class FleetExpectation(_Expectation):
    """Vessel multipliers, fuel demand, uptakes and realized fuel-type totals."""

    def __init__(self) -> None:
        super().__init__()

        self._multipliers: dict[tuple[str, BunkerScopeID], FloatArray]
        self._fuel_demand: dict[str, FloatArray]

        self._uptakes: FloatArray

        self._fuel_type_capacity: dict[FuelTypeID, float]
        self._fuel_type_supply: dict[FuelTypeID, float]

    def initialize(
        self, length: int, vessel_names: list[str], fuels: dict[str, Fuel]
    ) -> None:
        self._initialize_expectation(length)

        self._multipliers = self._default_tuple_dict_array(vessel_names, BunkerScopeID)
        self._fuel_demand = self._default_dict_array(fuels)

        self._uptakes = self._default_2d_array(len(vessel_names))

        self._fuel_type_capacity = self._default_dict_float(FuelTypeID)
        self._fuel_type_supply = self._default_dict_float(FuelTypeID)

    def set_multiplier(
        self, idx: int, vessel_name: str, scope: BunkerScopeID, multiplier: FloatLike
    ) -> None:
        self._multipliers[vessel_name, scope][idx:] = multiplier

    def set_fuel_demand(self, idx: int, fuel_name: str, demand: FloatLike) -> None:
        self._fuel_demand[fuel_name][idx:] = demand

    def set_uptakes(self, idx: int, uptakes: FloatArray) -> None:
        self._uptakes[:, idx] = uptakes

    def reset_fuel_type_totals(self) -> None:
        self._reset_dict_float(self._fuel_type_capacity)
        self._reset_dict_float(self._fuel_type_supply)

    def add_fuel_type_capacity(self, fuel_type: FuelTypeID, capacity: float) -> None:
        self._fuel_type_capacity[fuel_type] += capacity

    def add_fuel_type_supply(self, fuel_type: FuelTypeID, supply: float) -> None:
        self._fuel_type_supply[fuel_type] += supply

    def get_multiplier(
        self, vessel_name: str, scope: BunkerScopeID, idx: Index
    ) -> FloatLike:
        return self._multipliers[vessel_name, scope][idx]

    def get_fuel_demand(self, idx: Index) -> dict[str, FloatLike]:
        return slice_dict(self._fuel_demand, idx)

    def get_uptakes(self, idx: int) -> FloatArray:
        return self._uptakes[:, : idx + 1]

    def get_fuel_type_capacity(self, fuel_type: FuelTypeID) -> float:
        return self._fuel_type_capacity[fuel_type]

    def get_fuel_type_supply(self, fuel_type: FuelTypeID) -> float:
        return self._fuel_type_supply[fuel_type]
