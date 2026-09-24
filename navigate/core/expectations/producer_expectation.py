# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Producer node, read across the fuel domain."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.expectations._expectation import _Expectation
from navigate.util import slice_dict

if TYPE_CHECKING:
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.process import Process
    from navigate.util.types_ import FloatArray, FloatLike, Index


class ProducerExpectation(_Expectation):
    """Feedstock use, fair-share demand and production paths of a single producer."""

    def __init__(self) -> None:
        super().__init__()

        self._export_distribution: dict[str, FloatArray] = {}

        self._plant_feed_consumption: dict[tuple[str, str], float] = {}
        self._existing_feed: dict[str, float] = {}
        self._pipeline_feed: dict[str, float] = {}
        self._feed_gap: dict[str, FloatArray] = {}

        self._development_potential: dict[str, float] = {}

        self._fair_share_demand: dict[str, FloatArray] = {}

        self._existing_production: dict[str, FloatArray] = {}
        self._pipeline_production: dict[str, FloatArray] = {}
        self._newbuild_production: dict[str, FloatArray] = {}

    def initialize(
        self,
        length: int,
        plant_names: list[str],
        feedstocks: dict[str, Feedstock],
        fuels: dict[str, Fuel],
        ports: dict[str, Port],
        processes: dict[str, Process],
    ) -> None:
        self._initialize_expectation(length)

        self._export_distribution = self._default_dict_array(ports)

        feeds = {**feedstocks, **processes}
        self._plant_feed_consumption = self._default_tuple_dict_float(
            plant_names, feeds
        )
        self._existing_feed = self._default_dict_float(feeds)
        self._pipeline_feed = self._default_dict_float(feeds)
        self._feed_gap = self._default_dict_array(feeds, default=np.inf)

        self._development_potential = self._default_dict_float(fuels, default=np.inf)

        self._fair_share_demand = self._default_dict_array(fuels)

        self._existing_production = self._default_dict_array(plant_names)
        self._pipeline_production = self._default_dict_array(plant_names)
        self._newbuild_production = self._default_dict_array(plant_names)

    def reset_additive_properties(self) -> None:

        self._reset_dict_float(self._existing_feed)
        self._reset_dict_float(self._pipeline_feed)

    def set_export_distribution(
        self, idx: int, port_name: str, export_distribution: FloatLike
    ) -> None:
        self._export_distribution[port_name][idx:] = export_distribution

    def add_existing_feed(self, feed_name: str, existing_feed: float) -> None:
        self._existing_feed[feed_name] += existing_feed

    def add_pipeline_feed(self, feed_name: str, pipeline_feed: float) -> None:
        self._pipeline_feed[feed_name] += pipeline_feed

    def set_feed_gap(self, idx: int, feed_name: str, feed_gap: FloatLike) -> None:
        self._feed_gap[feed_name][idx:] = feed_gap

    def set_plant_feed_consumption(
        self, plant_name: str, feed_name: str, consumption: float
    ) -> None:
        self._plant_feed_consumption[(plant_name, feed_name)] = consumption

    def set_development_potential(
        self, fuel_name: str, development_potential: float
    ) -> None:
        self._development_potential[fuel_name] = development_potential

    def set_fair_share_demand(
        self, idx: int, fuel_name: str, fair_share_demand: FloatLike
    ) -> None:
        self._fair_share_demand[fuel_name][idx:] = fair_share_demand

    def set_existing_production(
        self, idx: int, plant_name: str, production: FloatLike
    ) -> None:
        self._existing_production[plant_name][idx:] = production

    def set_pipeline_production(
        self, idx: int, plant_name: str, production: FloatLike
    ) -> None:
        self._pipeline_production[plant_name][idx:] = production

    def set_newbuild_production(
        self, idx: int, plant_name: str, production: FloatLike
    ) -> None:
        self._newbuild_production[plant_name][idx:] = production

    def get_export_distribution(self, idx: Index = np.s_[:]) -> dict[str, FloatLike]:
        return slice_dict(self._export_distribution, idx)

    def get_plant_feed_consumption(self, plant_name: str, feed_name: str) -> float:
        return self._plant_feed_consumption[(plant_name, feed_name)]

    def get_existing_feed(self, feed_name: str) -> float:
        return self._existing_feed[feed_name]

    def get_pipeline_feed(self, feed_name: str) -> float:
        return self._pipeline_feed[feed_name]

    def get_feed_gap(self, feed_name: str, idx: Index = np.s_[:]) -> FloatLike:
        return self._feed_gap[feed_name][idx]

    def get_development_potential(self, fuel_name: str) -> float:
        return self._development_potential[fuel_name]

    def get_fair_share_demand(self) -> dict[str, FloatArray]:
        return self._fair_share_demand

    def get_guaranteed_production(
        self, plant_name: str, idx: Index = np.s_[:]
    ) -> FloatLike:
        return (
            self._existing_production[plant_name][idx]
            + self._pipeline_production[plant_name][idx]
        )

    def get_expected_production(
        self, plant_name: str, idx: Index = np.s_[:]
    ) -> FloatLike:
        return (
            self._existing_production[plant_name][idx]
            + self._pipeline_production[plant_name][idx]
            + self._newbuild_production[plant_name][idx]
        )
