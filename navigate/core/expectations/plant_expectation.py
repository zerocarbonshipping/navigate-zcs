# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Plant node, read across the fuel domain and the output layer."""

from __future__ import annotations

from itertools import product
from typing import TYPE_CHECKING

from navigate.core.expectations._expectation import _Expectation

if TYPE_CHECKING:
    from collections.abc import Collection


class PlantExpectation(_Expectation):
    """Production, cost, emission and uptake-decision paths of one plant of the type."""

    def __init__(
        self,
        length: int,
        emission_names: Collection[str],
        feedstock_names: Collection[str],
        port_names: Collection[str],
        process_names: Collection[str],
    ) -> None:
        super().__init__(length)

        feed_names = [*feedstock_names, *process_names]

        self.lifetime = self._path()  # years
        self.lead_time = self._path()  # years

        self.size = self._path()  # t/day
        self.production = self._path()  # t/year

        # feed per mass of fuel
        self.feed_conversion = self._paths(feed_names)  # t/t

        self.levelized_production_cost = self._path()  # currency/t
        self.levelized_delivery_cost = self._paths(port_names)  # currency/t

        # per time step, the capital a plant decided then ties up each year in service
        self.tied_capital = [self._path() for _ in range(length)]  # currency

        self.production_wtt = self._paths(emission_names)  # t/t
        self.delivery_wtt = self._paths(product(port_names, emission_names))  # t/t

        # production-weighted properties across plants
        self.expected_production_cost = self._path()  # currency/t
        self.expected_production_wtt = self._paths(emission_names)  # t/t

        # uptake decision
        self.demand_newbuilds = 0.0  # plants, exact zero without demand
        self.inter_fuel_metric = 0.0  # GJ/year of unmet demand for the fuel
        self.intra_fuel_metric = 0.0  # currency/t

    def reset_feed_conversion(self, idx: int) -> None:
        """
        Zero the feed conversions from a time step on.

        The steps before keep the feed conversions of the plants decided then.

        Parameters
        ----------
        idx
            First time-step index zeroed.
        """
        for conversion in self.feed_conversion.values():
            conversion[idx:] = 0.0
