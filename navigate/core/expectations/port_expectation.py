# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.expectations._expectation import _Expectation
from navigate.core.misc import EMPTY_FLOAT

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel


class PortExpectation(_Expectation):
    def __init__(self):
        super().__init__()

        self._handling_cost: dict[str, np.ndarray] = {}

        self._bunkering_limit: dict[str, np.ndarray] = {}

        self._bunker_price_overwrite: dict[str, np.ndarray] = {}
        self._bunker_WTT_overwrite: dict[tuple[str, str], np.ndarray] = {}

        self._bunker_supply: dict[str, np.ndarray] = {}   # expected future bunker supply, tons/year
        self._bunker_price: dict[str, np.ndarray] = {}    # dict[fuel_name: np.ndarray], expected future bunker price, USD/ton
        self._bunker_WTT: dict[tuple[str, str], np.ndarray] = {}      # expected future bunker WTT, ton/ton

        # bunkering used for inertia
        self._bunker_mass_expected: dict[str, float] = {}     # bunkered in previous nested time-step, tons
        self._bunker_mass_existing: dict[str, float] = {}     # dict[fuel_name: float], bunkered in previous time-step, tons

        # shore power
        self._shore_power_cost: np.ndarray = EMPTY_FLOAT               # np.ndarray, USD/GJ
        self._shore_power_connection_share: np.ndarray = EMPTY_FLOAT    # np.ndarray, fraction [0,1]
        self._shore_power_emission_factor: dict[str, np.ndarray] = {}   # dict[emission_name: np.ndarray], ton/GJ

    def initialize(self, length: int, fuels: dict[str, Fuel], emissions: dict[str, Emission]) -> None:
        self._initialize_expectation(length)

        self._handling_cost = self._default_dict_array(fuels)

        self._bunkering_limit = self._default_dict_array(fuels, default=np.inf)

        self._bunker_price_overwrite = self._default_dict_array(fuels, default=np.nan)
        self._bunker_WTT_overwrite = self._default_tuple_dict_array(fuels, emissions, default=np.nan)

        self._bunker_price = self._default_dict_array(fuels)
        self._bunker_WTT = self._default_tuple_dict_array(fuels, emissions)

        self._bunker_mass_expected = self._default_dict_float(fuels)
        self._bunker_mass_existing = self._default_dict_float(fuels)

        # shore power
        self._shore_power_cost = self._default_array()
        self._shore_power_connection_share = self._default_array()
        self._shore_power_emission_factor = self._default_dict_array(emissions)

        for fuel_name, fuel in fuels.items():
            if fuel.belongs_to_liquid_market():
                self._bunker_supply[fuel_name] = self._default_array(default=np.inf)
            else:
                self._bunker_supply[fuel_name] = self._default_array()

    def reset_bunker_mass_expected(self) -> None:
        self._reset_dict_float(self._bunker_mass_expected)

    def reset_bunker_mass_existing(self) -> None:
        self._reset_dict_float(self._bunker_mass_existing)

    def set_handling_cost(self, idx: int, fuel_name: str, handling_cost: np.ndarray) -> None:
        self._handling_cost[fuel_name][idx:] = handling_cost

    def set_bunkering_limit(self, idx: int, fuel_name: str, bunkering_limit: np.ndarray) -> None:
        self._bunkering_limit[fuel_name][idx:] = bunkering_limit

    def set_bunker_price_overwrite(self, idx: int, fuel_name: str, bunker_price_overwrite: np.ndarray) -> None:
        self._bunker_price_overwrite[fuel_name][idx:] = bunker_price_overwrite

    def set_bunker_WTT_overwrite(self, idx: int, fuel_name: str, emission_name: str, bunker_WTT_overwrite: np.ndarray) -> None:
        self._bunker_WTT_overwrite[(fuel_name, emission_name)][idx:] = bunker_WTT_overwrite

    def set_bunker_supply(self, idx: int, fuel_name: str, bunker_supply: np.ndarray) -> None:
        self._bunker_supply[fuel_name][idx:] = bunker_supply

    def set_bunker_price(self, idx: int, fuel_name: str, bunker_price: np.ndarray) -> None:
        self._bunker_price[fuel_name][idx:] = bunker_price

    def set_bunker_WTT(self, idx: int, fuel_name: str, emission_name: str, bunker_WTT: np.ndarray) -> None:
        self._bunker_WTT[(fuel_name, emission_name)][idx:] = bunker_WTT

    def add_bunker_mass_expected(self, fuel_name: str, fuel_mass: float) -> None:
        self._bunker_mass_expected[fuel_name] += fuel_mass

    def add_bunker_mass_existing(self, fuel_name: str, fuel_mass: float) -> None:
        self._bunker_mass_existing[fuel_name] += fuel_mass

    def get_handling_cost(self, fuel_name: str, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._handling_cost[fuel_name][idx]

    def get_bunkering_limit(self, fuel_name: str, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._bunkering_limit[fuel_name][idx]

    def get_bunker_price_overwrite(self, fuel_name: str, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._bunker_price_overwrite[fuel_name][idx]

    def get_bunker_WTT_overwrite(self, fuel_name: str, emission_name: str, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._bunker_WTT_overwrite[(fuel_name, emission_name)][idx]

    def get_bunker_supply(self, fuel_name: str, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._bunker_supply[fuel_name][idx]

    def get_bunker_price(self, fuel_name: str, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._bunker_price[fuel_name][idx]

    def get_bunker_WTT(self, fuel_name: str, emission_name: str, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._bunker_WTT[(fuel_name, emission_name)][idx]

    def get_bunker_mass_expected(self, fuel_name: str) -> float:
        return self._bunker_mass_expected[fuel_name]

    def get_bunker_mass_existing(self, fuel_name: str) -> float:
        return self._bunker_mass_existing[fuel_name]

    # shore power
    def set_shore_power_cost(self, idx: int, cost: np.ndarray) -> None:
        self._shore_power_cost[idx:] = cost

    def set_shore_power_connection_share(self, idx: int, share: np.ndarray) -> None:
        self._shore_power_connection_share[idx:] = share

    def set_shore_power_emission_factor(self, idx: int, emission_name: str, ef: np.ndarray) -> None:
        self._shore_power_emission_factor[emission_name][idx:] = ef

    def get_shore_power_cost(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._shore_power_cost[idx]

    def get_shore_power_connection_share(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._shore_power_connection_share[idx]

    def get_shore_power_emission_factor(self, emission_name: str, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._shore_power_emission_factor[emission_name][idx]
