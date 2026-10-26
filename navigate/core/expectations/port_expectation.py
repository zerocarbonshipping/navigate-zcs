# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Port node, read by the bunkering LP and the fuel domain."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np

from navigate.core.expectations._expectation import _Expectation
from navigate.util import slice_array

if TYPE_CHECKING:
    from collections.abc import Collection

    from navigate.util.types_ import FloatArray, FloatLike, Index


class PortExpectation(_Expectation):
    """Bunker supply, price and emission paths a single port offers each fuel."""

    def __init__(self) -> None:
        super().__init__()

        self._handling_cost: dict[str, FloatArray]
        self._bunkering_limit: dict[str, FloatArray]

        self._bunker_price_overwrite: dict[str, FloatArray]
        self._bunker_wtt_overwrite: dict[tuple[str, str], FloatArray]

        self._bunker_supply: dict[str, FloatArray]
        self._bunker_price: dict[str, FloatArray]
        self._bunker_wtt: dict[tuple[str, str], FloatArray]

        self._shore_power_cost: FloatArray
        self._shore_power_connection_share: FloatArray
        self._shore_power_emission_factor: dict[str, FloatArray]

    def initialize(
        self, length: int, fuel_names: Collection[str], emission_names: Collection[str]
    ) -> None:
        self._initialize_expectation(length)

        self._handling_cost = self._default_dict_array(fuel_names)
        self._bunkering_limit = self._default_dict_array(fuel_names, default=np.inf)

        self._bunker_price_overwrite = self._default_dict_array(
            fuel_names, default=np.nan
        )
        self._bunker_wtt_overwrite = self._default_tuple_dict_array(
            fuel_names, emission_names, default=np.nan
        )

        self._bunker_supply = self._default_dict_array(fuel_names)
        self._bunker_price = self._default_dict_array(fuel_names)
        self._bunker_wtt = self._default_tuple_dict_array(fuel_names, emission_names)

        self._shore_power_cost = self._default_array()
        self._shore_power_connection_share = self._default_array()
        self._shore_power_emission_factor = self._default_dict_array(emission_names)

    def set_handling_cost(self, idx: int, fuel_name: str, cost: FloatArray) -> None:
        self._handling_cost[fuel_name][idx:] = cost

    def set_bunkering_limit(self, idx: int, fuel_name: str, limit: FloatArray) -> None:
        self._bunkering_limit[fuel_name][idx:] = limit

    def set_bunker_price_overwrite(
        self, idx: int, fuel_name: str, overwrite: FloatArray
    ) -> None:
        self._bunker_price_overwrite[fuel_name][idx:] = overwrite

    def set_bunker_wtt_overwrite(
        self, idx: int, fuel_name: str, emission_name: str, overwrite: FloatArray
    ) -> None:
        self._bunker_wtt_overwrite[fuel_name, emission_name][idx:] = overwrite

    def set_bunker_supply(self, idx: int, fuel_name: str, supply: FloatArray) -> None:
        self._bunker_supply[fuel_name][idx:] = supply

    def set_bunker_price(self, idx: int, fuel_name: str, price: FloatArray) -> None:
        self._bunker_price[fuel_name][idx:] = price

    def set_bunker_wtt(
        self, idx: int, fuel_name: str, emission_name: str, wtt: FloatArray
    ) -> None:
        self._bunker_wtt[fuel_name, emission_name][idx:] = wtt

    def set_shore_power_cost(self, idx: int, cost: FloatArray) -> None:
        self._shore_power_cost[idx:] = cost

    def set_shore_power_connection_share(self, idx: int, share: FloatArray) -> None:
        self._shore_power_connection_share[idx:] = share

    def set_shore_power_emission_factor(
        self, idx: int, emission_name: str, factor: FloatArray
    ) -> None:
        self._shore_power_emission_factor[emission_name][idx:] = factor

    def get_handling_cost(self, fuel_name: str, idx: slice) -> FloatArray:
        return slice_array(self._handling_cost[fuel_name], idx)

    def get_bunkering_limit(self, fuel_name: str, idx: slice) -> FloatArray:
        return slice_array(self._bunkering_limit[fuel_name], idx)

    def get_bunker_price_overwrite(self, fuel_name: str, idx: slice) -> FloatArray:
        return slice_array(self._bunker_price_overwrite[fuel_name], idx)

    def get_bunker_wtt_overwrite(
        self, fuel_name: str, emission_name: str, idx: slice
    ) -> FloatArray:
        return slice_array(self._bunker_wtt_overwrite[fuel_name, emission_name], idx)

    def get_bunker_supply(self, fuel_name: str, idx: int) -> float:
        return slice_array(self._bunker_supply[fuel_name], idx)

    @overload
    def get_bunker_price(self, fuel_name: str, idx: int) -> float: ...

    @overload
    def get_bunker_price(self, fuel_name: str, idx: slice) -> FloatArray: ...

    def get_bunker_price(self, fuel_name: str, idx: Index) -> FloatLike:
        return slice_array(self._bunker_price[fuel_name], idx)

    def get_bunker_wtt(self, fuel_name: str, emission_name: str, idx: int) -> float:
        return slice_array(self._bunker_wtt[fuel_name, emission_name], idx)

    def get_shore_power_cost(self, idx: int) -> float:
        return slice_array(self._shore_power_cost, idx)

    def get_shore_power_connection_share(self, idx: slice) -> FloatArray:
        return slice_array(self._shore_power_connection_share, idx)

    @overload
    def get_shore_power_emission_factor(
        self, emission_name: str, idx: int
    ) -> float: ...

    @overload
    def get_shore_power_emission_factor(
        self, emission_name: str, idx: slice
    ) -> FloatArray: ...

    def get_shore_power_emission_factor(
        self, emission_name: str, idx: Index
    ) -> FloatLike:
        return slice_array(self._shore_power_emission_factor[emission_name], idx)
