# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import KeysView
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.expectations._expectation import _Expectation
from navigate.core.misc import EMPTY_FLOAT
from navigate.util import extract_from_dict, extract_from_tuple_dict

if TYPE_CHECKING:
    from navigate.fuel import Emission, Feedstock, Process
    from navigate.route import Port


class PlantExpectation(_Expectation):
    def __init__(self):
        super().__init__()

        # durations
        self._lifetime: np.ndarray = EMPTY_FLOAT       # np.ndarray, plant lifetime, years
        self._lead_time: np.ndarray = EMPTY_FLOAT      # np.ndarray, plant construction lead time, years

        # production
        self._size: np.ndarray = EMPTY_FLOAT           # tons/day (for CAPEX/OPEX scaling)
        self._capacity: np.ndarray = EMPTY_FLOAT       # tons/year
        self._production: np.ndarray = EMPTY_FLOAT     # tons/year (incl. uptime)

        # feed
        self._feed_mass: dict[str, np.ndarray] = {}        # dict[feed_name: np.ndarray], feed used in production, ton/ton

        # levelized cost
        self._levelized_production_cost: np.ndarray = EMPTY_FLOAT  # USD/ton
        self._levelized_delivery_cost: dict[str, np.ndarray] = {}  # levelized cost of delivery, USD/ton

        # capital
        self._tied_capital: list[np.ndarray | None] = []     # list[time_step: np.ndarray], USD

        # emissions
        self._production_WTT: dict[str, np.ndarray] = {}   # dict[emission_name: np.ndarray], production emissions, ton e/ton f
        self._delivery_WTT: dict[tuple[str, str], np.ndarray] = {}     # delivery emissions, ton e/ton f

        # production-weighted properties across plants
        self._expected_production_cost: np.ndarray = EMPTY_FLOAT
        self._expected_production_WTT: dict[str, np.ndarray] = {}

        # decision related
        self._demand_newbuilds: float = 0.   # float, maximum number of newbuilds to satisfy expected supply gap
        self._inter_fuel_metric: float = 0.  # float
        self._intra_fuel_metric: float = 0.  # float

    def initialize(self, length: int, emissions: dict[str, Emission], feedstocks: dict[str, Feedstock],
                   ports: dict[str, Port], processes: dict[str, Process]) -> None:
        self._initialize_expectation(length)

        self._lifetime = self._default_array()
        self._lead_time = self._default_array()

        self._size = self._default_array()
        self._capacity = self._default_array()
        self._production = self._default_array()

        self._feed_mass = self._default_dict_array({**feedstocks, **processes})

        self._levelized_production_cost = self._default_array()
        self._levelized_delivery_cost = self._default_dict_array(ports)

        self._tied_capital = [None] * length

        self._production_WTT = self._default_dict_array(emissions)
        self._delivery_WTT = self._default_tuple_dict_array(ports, emissions)

        self._expected_production_cost = self._default_array()
        self._expected_production_WTT = self._default_dict_array(emissions)

        self._demand_newbuilds = self._default_float()
        self._inter_fuel_metric = self._default_float()
        self._intra_fuel_metric = self._default_float()

    def reset_additive_properties(self, idx: int) -> None:
        # reset from idx=0 since fuel properties are recomputed at all time-steps
        self._reset_dict_array_partial(self._feed_mass, idx=idx)

    def get_emissions(self) -> KeysView[str]:
        return self._production_WTT.keys()

    def set_lifetime(self, idx: int, lifetime: np.ndarray) -> None:
        self._lifetime[idx:] = lifetime

    def set_lead_time(self, idx: int, lead_time: np.ndarray) -> None:
        self._lead_time[idx:] = lead_time

    def set_size(self, idx: int, size: np.ndarray) -> None:
        self._size[idx:] = size

    def set_capacity(self, idx: int, capacity: np.ndarray) -> None:
        self._capacity[idx:] = capacity

    def set_production(self, idx: int, production: np.ndarray) -> None:
        self._production[idx:] = production

    def add_feed_mass(self, idx: int, feed_name: str, feed_mass: np.ndarray) -> None:
        self._feed_mass[feed_name][idx:] += feed_mass

    def set_production_WTT(self, idx: int, emission_name: str, production_WTT: float) -> None:
        self._production_WTT[emission_name][idx] = production_WTT

    def set_delivery_WTT(self, idx: int, port_name: str, emission_name: str, delivery_WTT: np.ndarray) -> None:
        self._delivery_WTT[(port_name, emission_name)][idx:] = delivery_WTT

    def set_levelized_production_cost(self, idx: int, levelized_production_cost: float) -> None:
        self._levelized_production_cost[idx] = levelized_production_cost

    def set_levelized_delivery_cost(self, idx: int, port_name: str, levelized_delivery_cost: float) -> None:
        self._levelized_delivery_cost[port_name][idx] = levelized_delivery_cost

    def set_tied_capital(self, idx: int, tied_capital: np.ndarray) -> None:
        self._tied_capital[idx] = tied_capital

    def set_expected_production_cost(self, idx: int, expected_cost: np.ndarray) -> None:
        self._expected_production_cost[idx:] = expected_cost

    def set_expected_production_WTT(self, idx: int, emission_name: str, expected_WTT: np.ndarray) -> None:
        self._expected_production_WTT[emission_name][idx:] = expected_WTT

    def set_demand_newbuilds(self, demand_newbuilds: float) -> None:
        self._demand_newbuilds = demand_newbuilds

    def set_inter_fuel_metric(self, inter_fuel_metric: float) -> None:
        self._inter_fuel_metric = inter_fuel_metric

    def set_intra_fuel_metric(self, intra_fuel_metric: float) -> None:
        self._intra_fuel_metric = intra_fuel_metric

    def get_lifetime(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._lifetime[idx]

    def get_lead_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._lead_time[idx]

    def get_size(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._size[idx]

    def get_capacity(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._capacity[idx]

    def get_production(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._production[idx]

    def get_feed_mass(self, feed_name: str | None = None, idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._feed_mass, feed_name, idx)

    def get_levelized_production_cost(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._levelized_production_cost[idx]

    def get_levelized_delivery_cost(self, port_name: str | None = None,
                                    idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._levelized_delivery_cost, port_name, idx)

    def get_levelized_delivered_cost(self, port_name: str, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self.get_levelized_production_cost(idx) + self.get_levelized_delivery_cost(port_name, idx)

    def get_expected_delivered_cost(self, port_name: str, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._expected_production_cost[idx] + self.get_levelized_delivery_cost(port_name, idx)

    def get_tied_capital(self, idx: int) -> np.ndarray:
        return self._tied_capital[idx]

    def get_production_WTT(self, emission_name: str | None = None,
                           idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._production_WTT, emission_name, idx)

    def get_delivery_WTT(self, port_name: str | None = None, emission_name: str | None = None,
                         idx: int | slice = np.s_[:]) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        return extract_from_tuple_dict(self._delivery_WTT, port_name, emission_name, idx)

    def get_expected_production_WTT(self, emission_name: str | None = None,
                                    idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._expected_production_WTT, emission_name, idx)

    def get_expected_delivered_WTT(self, port_name: str, emission_name: str, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self.get_delivery_WTT(port_name, emission_name, idx) + self.get_expected_production_WTT(emission_name, idx)

    def get_demand_newbuilds(self) -> float:
        return self._demand_newbuilds

    def get_inter_fuel_metric(self) -> float:
        return self._inter_fuel_metric

    def get_intra_fuel_metric(self) -> float:
        return self._intra_fuel_metric

    def is_in_demand(self) -> bool:
        return self._inter_fuel_metric > 0.
