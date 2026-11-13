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
    """Production, cost, emission and uptake-decision paths of a single plant."""

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

        self.lifetime = self._path()
        self.lead_time = self._path()

        self.size = self._path()
        self.production = self._path()

        # feed per mass of fuel
        self.feed_conversion = self._paths(feed_names)

        self.levelized_production_cost = self._path()
        self.levelized_delivery_cost = self._paths(port_names)

        # per time step, the tied-up capital flow of a plant decided then
        self.tied_capital = [self._path() for _ in range(length)]

        self.production_wtt = self._paths(emission_names)
        self.delivery_wtt = self._paths(product(port_names, emission_names))

        # production-weighted properties across plants
        self.expected_production_cost = self._path()
        self.expected_production_wtt = self._paths(emission_names)

        # uptake decision
        self.demand_newbuilds = 0.0
        self.inter_fuel_metric = 0.0
        self.intra_fuel_metric = 0.0

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
