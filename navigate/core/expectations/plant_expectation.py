# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Plant node, read across the fuel domain and the output layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

from navigate.core.expectations._expectation import _Expectation
from navigate.util import slice_dict

if TYPE_CHECKING:
    from collections.abc import Collection, KeysView, Mapping

    from navigate.util.types_ import FloatArray, FloatLike, Index, IntArray, Step


class PlantExpectation(_Expectation):
    """Production, cost, emission and uptake-decision paths of a single plant."""

    def __init__(self) -> None:
        super().__init__()

        self._lifetime: FloatArray
        self._lead_time: FloatArray

        self._size: FloatArray
        self._production: FloatArray

        # feed per mass of fuel
        self._feed_conversion: dict[str, FloatArray]

        self._levelized_production_cost: FloatArray
        self._levelized_delivery_cost: dict[str, FloatArray]

        self._tied_capital: list[FloatArray]

        self._production_wtt: dict[str, FloatArray]
        self._delivery_wtt: dict[tuple[str, str], FloatArray]

        # production-weighted properties across plants
        self._expected_production_cost: FloatArray
        self._expected_production_wtt: dict[str, FloatArray]

        # uptake decision
        self._demand_newbuilds: float
        self._inter_fuel_metric: float
        self._intra_fuel_metric: float

    def initialize(
        self,
        length: int,
        emission_names: Collection[str],
        feedstock_names: Collection[str],
        port_names: Collection[str],
        process_names: Collection[str],
    ) -> None:
        self._initialize_expectation(length)

        self._lifetime = self._default_array()
        self._lead_time = self._default_array()

        self._size = self._default_array()
        self._production = self._default_array()

        feed_names = [*feedstock_names, *process_names]
        self._feed_conversion = self._default_dict_array(feed_names)

        self._levelized_production_cost = self._default_array()
        self._levelized_delivery_cost = self._default_dict_array(port_names)

        self._tied_capital = self._default_list_array(self._length)

        self._production_wtt = self._default_dict_array(emission_names)
        self._delivery_wtt = self._default_tuple_dict_array(port_names, emission_names)

        self._expected_production_cost = self._default_array()
        self._expected_production_wtt = self._default_dict_array(emission_names)

        self._demand_newbuilds = 0.0
        self._inter_fuel_metric = 0.0
        self._intra_fuel_metric = 0.0

    def reset_feed_conversion(self, idx: int) -> None:
        # the steps before idx keep the feed conversions of the plants decided then
        self._reset_dict_array_partial(self._feed_conversion, idx)

    def set_lifetime(self, idx: int, lifetime: FloatArray) -> None:
        self._lifetime[idx:] = lifetime

    def set_lead_time(self, idx: int, lead_time: FloatArray) -> None:
        self._lead_time[idx:] = lead_time

    def set_size(self, idx: int, size: FloatArray) -> None:
        self._size[idx:] = size

    def set_production(self, idx: int, production: FloatArray) -> None:
        self._production[idx:] = production

    def add_feed_conversion(self, feed_name: str, idx: int, conversion: float) -> None:
        # additive: a feed can occur several times in the process tree of idx
        self._feed_conversion[feed_name][idx] += conversion

    def set_levelized_production_cost(self, idx: int, cost: float) -> None:
        self._levelized_production_cost[idx] = cost

    def set_levelized_delivery_cost(
        self, port_name: str, idx: int, cost: float
    ) -> None:
        self._levelized_delivery_cost[port_name][idx] = cost

    def set_tied_capital(self, idx: int, capital: FloatArray) -> None:
        self._tied_capital[idx] = capital

    def set_production_wtt(self, emission_name: str, idx: int, wtt: float) -> None:
        self._production_wtt[emission_name][idx] = wtt

    def set_delivery_wtt(
        self, port_name: str, emission_name: str, idx: int, wtt: FloatArray
    ) -> None:
        self._delivery_wtt[port_name, emission_name][idx:] = wtt

    def set_expected_production_cost(self, idx: int, cost: FloatArray) -> None:
        self._expected_production_cost[idx:] = cost

    def set_expected_production_wtt(
        self, emission_name: str, idx: int, wtt: FloatArray
    ) -> None:
        self._expected_production_wtt[emission_name][idx:] = wtt

    def set_demand_newbuilds(self, newbuilds: float) -> None:
        self._demand_newbuilds = newbuilds

    def set_inter_fuel_metric(self, metric: float) -> None:
        self._inter_fuel_metric = metric

    def set_intra_fuel_metric(self, metric: float) -> None:
        self._intra_fuel_metric = metric

    def get_lifetime(self, idx: int) -> float:
        lifetime: float = self._lifetime[idx]
        return lifetime

    def get_lead_time(self, idx: int) -> float:
        lead_time: float = self._lead_time[idx]
        return lead_time

    def get_size(self, idx: int) -> float:
        size: float = self._size[idx]
        return size

    @overload
    def get_production(self, idx: Step) -> float: ...

    @overload
    def get_production(self, idx: IntArray) -> FloatArray: ...

    def get_production(self, idx: Index) -> FloatLike:
        return self._production[idx]

    def get_feed_conversion(self, feed_name: str, idx: Step) -> float:
        conversion: float = self._feed_conversion[feed_name][idx]
        return conversion

    @overload
    def get_feed_conversions(self, idx: Step) -> dict[str, float]: ...

    @overload
    def get_feed_conversions(self, idx: IntArray) -> dict[str, FloatArray]: ...

    def get_feed_conversions(self, idx: Index) -> Mapping[str, FloatLike]:
        return slice_dict(self._feed_conversion, idx)

    def get_levelized_production_cost(self, idx: Step) -> float:
        cost: float = self._levelized_production_cost[idx]
        return cost

    @overload
    def get_levelized_delivery_cost(self, port_name: str, idx: int) -> float: ...

    @overload
    def get_levelized_delivery_cost(self, port_name: str, idx: slice) -> FloatArray: ...

    def get_levelized_delivery_cost(self, port_name: str, idx: Index) -> FloatLike:
        return self._levelized_delivery_cost[port_name][idx]

    def get_tied_capital(self, idx: int) -> FloatArray:
        return self._tied_capital[idx]

    def get_emissions(self) -> KeysView[str]:
        return self._production_wtt.keys()

    @overload
    def get_production_wtt(self, emission_name: str, idx: Step) -> float: ...

    @overload
    def get_production_wtt(self, emission_name: str, idx: slice) -> FloatArray: ...

    def get_production_wtt(self, emission_name: str, idx: Index) -> FloatLike:
        return self._production_wtt[emission_name][idx]

    def get_delivery_wtt(
        self, port_name: str, emission_name: str, idx: slice
    ) -> FloatArray:
        return self._delivery_wtt[port_name, emission_name][idx]

    def get_expected_production_cost(self, idx: slice) -> FloatArray:
        return self._expected_production_cost[idx]

    def get_expected_production_wtt(self, emission_name: str, idx: slice) -> FloatArray:
        return self._expected_production_wtt[emission_name][idx]

    def get_demand_newbuilds(self) -> float:
        return self._demand_newbuilds

    def get_inter_fuel_metric(self) -> float:
        return self._inter_fuel_metric

    def get_intra_fuel_metric(self) -> float:
        return self._intra_fuel_metric
