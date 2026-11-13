# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Producer node, read across the fuel domain."""

from __future__ import annotations

from itertools import product
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.expectations._expectation import _Expectation

if TYPE_CHECKING:
    from collections.abc import Collection


class ProducerExpectation(_Expectation):
    """Export shares, feed use, fair-share demand and production paths of a producer."""

    def __init__(
        self,
        length: int,
        plant_names: Collection[str],
        feedstock_names: Collection[str],
        fuel_names: Collection[str],
        port_names: Collection[str],
        process_names: Collection[str],
    ) -> None:
        super().__init__(length)

        feed_names = [*feedstock_names, *process_names]

        # per fuel, then per port
        self.export_share = {name: self._paths(port_names) for name in fuel_names}

        self.plant_feed_consumption = self._values(product(plant_names, feed_names))
        self.feed_gap = self._paths(feed_names, default=np.inf)

        self.development_potential = self._values(fuel_names)
        self.fair_share_demand = self._paths(fuel_names)

        # the producer's guaranteed production its fair-share demand was measured
        # against
        self.fair_share_baseline = self._paths(fuel_names)

        self.guaranteed_production = self._paths(plant_names)
        self.expected_production = self._paths(plant_names)
