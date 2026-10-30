# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Producer node, read across the fuel domain."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np

from navigate.core.expectations._expectation import _Expectation
from navigate.util import slice_dict

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from navigate.util.types_ import FloatArray, FloatLike, Index


class ProducerExpectation(_Expectation):
    """Export shares, feed use, fair-share demand and production paths of a producer."""

    def __init__(self) -> None:
        super().__init__()

        self._export_distribution: dict[str, FloatArray]

        self._plant_feed_consumption: dict[tuple[str, str], float]
        self._existing_feed: dict[str, float]
        self._pipeline_feed: dict[str, float]
        self._feed_gap: dict[str, FloatArray]

        self._development_potential: dict[str, float]
        self._fair_share_demand: dict[str, FloatArray]

        self._guaranteed_production: dict[str, FloatArray]
        self._expected_production: dict[str, FloatArray]

    def initialize(
        self,
        length: int,
        plant_names: Collection[str],
        feedstock_names: Collection[str],
        fuel_names: Collection[str],
        port_names: Collection[str],
        process_names: Collection[str],
    ) -> None:
        self._initialize_expectation(length)

        self._export_distribution = self._default_dict_array(port_names)

        feed_names = [*feedstock_names, *process_names]
        self._plant_feed_consumption = self._default_tuple_dict_float(
            plant_names, feed_names
        )
        self._existing_feed = self._default_dict_float(feed_names)
        self._pipeline_feed = self._default_dict_float(feed_names)
        self._feed_gap = self._default_dict_array(feed_names, default=np.inf)

        self._development_potential = self._default_dict_float(fuel_names)
        self._fair_share_demand = self._default_dict_array(fuel_names)

        self._guaranteed_production = self._default_dict_array(plant_names)
        self._expected_production = self._default_dict_array(plant_names)

    def reset_feed_totals(self) -> None:
        self._reset_dict_float(self._existing_feed)
        self._reset_dict_float(self._pipeline_feed)

    def set_export_distribution(
        self, port_name: str, idx: int, distribution: FloatArray
    ) -> None:
        self._export_distribution[port_name][idx:] = distribution

    def set_plant_feed_consumption(
        self, plant_name: str, feed_name: str, consumption: float
    ) -> None:
        self._plant_feed_consumption[plant_name, feed_name] = consumption

    def add_existing_feed(self, feed_name: str, feed: float) -> None:
        self._existing_feed[feed_name] += feed

    def add_pipeline_feed(self, feed_name: str, feed: float) -> None:
        self._pipeline_feed[feed_name] += feed

    def set_feed_gap(self, feed_name: str, idx: int, gap: FloatLike) -> None:
        self._feed_gap[feed_name][idx:] = gap

    def set_development_potential(self, fuel_name: str, potential: float) -> None:
        self._development_potential[fuel_name] = potential

    def set_fair_share_demand(
        self, fuel_name: str, idx: int, demand: FloatLike
    ) -> None:
        self._fair_share_demand[fuel_name][idx:] = demand

    def set_guaranteed_production(
        self, plant_name: str, idx: int, production: FloatArray
    ) -> None:
        self._guaranteed_production[plant_name][idx:] = production

    def set_expected_production(
        self, plant_name: str, idx: int, production: FloatArray
    ) -> None:
        self._expected_production[plant_name][idx:] = production

    @overload
    def get_export_distribution(self, idx: int) -> dict[str, float]: ...

    @overload
    def get_export_distribution(self, idx: slice) -> dict[str, FloatArray]: ...

    def get_export_distribution(self, idx: Index) -> Mapping[str, FloatLike]:
        return slice_dict(self._export_distribution, idx)

    def get_plant_feed_consumption(self, plant_name: str, feed_name: str) -> float:
        return self._plant_feed_consumption[plant_name, feed_name]

    def get_existing_feed(self, feed_name: str) -> float:
        return self._existing_feed[feed_name]

    def get_pipeline_feed(self, feed_name: str) -> float:
        return self._pipeline_feed[feed_name]

    def get_feed_gap(self, feed_name: str, idx: int) -> float:
        gap: float = self._feed_gap[feed_name][idx]
        return gap

    def get_development_potential(self, fuel_name: str) -> float:
        return self._development_potential[fuel_name]

    def get_fair_share_demand(self) -> dict[str, FloatArray]:
        return self._fair_share_demand

    def get_guaranteed_production(self, plant_name: str, idx: slice) -> FloatArray:
        return self._guaranteed_production[plant_name][idx]

    def get_expected_production(self, plant_name: str, idx: slice) -> FloatArray:
        return self._expected_production[plant_name][idx]
