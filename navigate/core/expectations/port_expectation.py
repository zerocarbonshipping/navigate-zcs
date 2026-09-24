# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Port node, read by the bunkering LP and the fuel domain."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.expectations._expectation import _Expectation
from navigate.core.initial_values import EMPTY_FLOAT

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.util.types_ import FloatArray, FloatLike, Index


class PortExpectation(_Expectation):
    """Bunker supply, price and emission paths a single port offers each fuel."""

    def __init__(self) -> None:
        super().__init__()

        self._handling_cost: dict[
            str, FloatArray
        ] = {}  # storage and bunkering service cost, USD/ton

        self._bunkering_limit: dict[
            str, FloatArray
        ] = {}  # upper bound on what may be bunkered, tons/year

        self._bunker_price_overwrite: dict[
            str, FloatArray
        ] = {}  # deck-set bunker price replacing the modelled one, USD/ton
        self._bunker_wtt_overwrite: dict[
            tuple[str, str], FloatArray
        ] = {}  # deck-set bunker WTT replacing the modelled one, ton e/ton f

        self._bunker_supply: dict[
            str, FloatArray
        ] = {}  # expected future bunker supply, tons/year
        self._bunker_price: dict[
            str, FloatArray
        ] = {}  # expected future bunker price, USD/ton
        self._bunker_wtt: dict[
            tuple[str, str], FloatArray
        ] = {}  # expected future bunker WTT, ton e/ton f

        # shore power
        self._shore_power_cost: FloatArray = EMPTY_FLOAT  # shore power cost, USD/GJ
        self._shore_power_connection_share: FloatArray = (
            EMPTY_FLOAT  # share of port calls able to connect, fraction [0,1]
        )
        self._shore_power_emission_factor: dict[
            str, FloatArray
        ] = {}  # shore power emissions, ton/GJ

    def initialize(
        self, length: int, fuels: dict[str, Fuel], emissions: dict[str, Emission]
    ) -> None:
        self._initialize_expectation(length)

        self._handling_cost = self._default_dict_array(fuels)

        self._bunkering_limit = self._default_dict_array(fuels, default=np.inf)

        self._bunker_price_overwrite = self._default_dict_array(fuels, default=np.nan)
        self._bunker_wtt_overwrite = self._default_tuple_dict_array(
            fuels, emissions, default=np.nan
        )

        self._bunker_price = self._default_dict_array(fuels)
        self._bunker_wtt = self._default_tuple_dict_array(fuels, emissions)

        # shore power
        self._shore_power_cost = self._default_array()
        self._shore_power_connection_share = self._default_array()
        self._shore_power_emission_factor = self._default_dict_array(emissions)

        for fuel_name, fuel in fuels.items():
            if fuel.liquid_market:
                self._bunker_supply[fuel_name] = self._default_array(default=np.inf)
            else:
                self._bunker_supply[fuel_name] = self._default_array()

    def set_handling_cost(
        self, idx: int, fuel_name: str, handling_cost: FloatLike
    ) -> None:
        self._handling_cost[fuel_name][idx:] = handling_cost

    def set_bunkering_limit(
        self, idx: int, fuel_name: str, bunkering_limit: FloatLike
    ) -> None:
        self._bunkering_limit[fuel_name][idx:] = bunkering_limit

    def set_bunker_price_overwrite(
        self, idx: int, fuel_name: str, bunker_price_overwrite: FloatLike
    ) -> None:
        self._bunker_price_overwrite[fuel_name][idx:] = bunker_price_overwrite

    def set_bunker_wtt_overwrite(
        self,
        idx: int,
        fuel_name: str,
        emission_name: str,
        bunker_wtt_overwrite: FloatLike,
    ) -> None:
        self._bunker_wtt_overwrite[(fuel_name, emission_name)][idx:] = (
            bunker_wtt_overwrite
        )

    def set_bunker_supply(
        self, idx: int, fuel_name: str, bunker_supply: FloatLike
    ) -> None:
        self._bunker_supply[fuel_name][idx:] = bunker_supply

    def set_bunker_price(
        self, idx: int, fuel_name: str, bunker_price: FloatLike
    ) -> None:
        self._bunker_price[fuel_name][idx:] = bunker_price

    def set_bunker_wtt(
        self, idx: int, fuel_name: str, emission_name: str, bunker_wtt: FloatLike
    ) -> None:
        self._bunker_wtt[(fuel_name, emission_name)][idx:] = bunker_wtt

    def get_handling_cost(self, fuel_name: str, idx: Index = np.s_[:]) -> FloatLike:
        return self._handling_cost[fuel_name][idx]

    def get_bunkering_limit(self, fuel_name: str, idx: Index = np.s_[:]) -> FloatLike:
        return self._bunkering_limit[fuel_name][idx]

    def get_bunker_price_overwrite(
        self, fuel_name: str, idx: Index = np.s_[:]
    ) -> FloatLike:
        return self._bunker_price_overwrite[fuel_name][idx]

    def get_bunker_wtt_overwrite(
        self, fuel_name: str, emission_name: str, idx: Index = np.s_[:]
    ) -> FloatLike:
        return self._bunker_wtt_overwrite[(fuel_name, emission_name)][idx]

    def get_bunker_supply(self, fuel_name: str, idx: Index = np.s_[:]) -> FloatLike:
        return self._bunker_supply[fuel_name][idx]

    def get_bunker_price(self, fuel_name: str, idx: Index = np.s_[:]) -> FloatLike:
        return self._bunker_price[fuel_name][idx]

    def get_bunker_wtt(
        self, fuel_name: str, emission_name: str, idx: Index = np.s_[:]
    ) -> FloatLike:
        return self._bunker_wtt[(fuel_name, emission_name)][idx]

    # shore power
    def set_shore_power_cost(self, idx: int, cost: FloatLike) -> None:
        self._shore_power_cost[idx:] = cost

    def set_shore_power_connection_share(self, idx: int, share: FloatLike) -> None:
        self._shore_power_connection_share[idx:] = share

    def set_shore_power_emission_factor(
        self, idx: int, emission_name: str, ef: FloatLike
    ) -> None:
        self._shore_power_emission_factor[emission_name][idx:] = ef

    def get_shore_power_cost(self, idx: Index = np.s_[:]) -> FloatLike:
        return self._shore_power_cost[idx]

    def get_shore_power_connection_share(self, idx: Index = np.s_[:]) -> FloatLike:
        return self._shore_power_connection_share[idx]

    def get_shore_power_emission_factor(
        self, emission_name: str, idx: Index = np.s_[:]
    ) -> FloatLike:
        return self._shore_power_emission_factor[emission_name][idx]
