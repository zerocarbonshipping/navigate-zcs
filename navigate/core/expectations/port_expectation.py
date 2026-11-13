# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Port node, read by the bunkering LP and the fuel domain."""

from __future__ import annotations

from itertools import product
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.expectations._expectation import _Expectation

if TYPE_CHECKING:
    from collections.abc import Collection


class PortExpectation(_Expectation):
    """Bunker supply, price and emission paths a single port offers each fuel."""

    def __init__(
        self, length: int, fuel_names: Collection[str], emission_names: Collection[str]
    ) -> None:
        super().__init__(length)

        fuel_emissions = list(product(fuel_names, emission_names))

        self.handling_cost = self._paths(fuel_names)
        self.bunkering_limit = self._paths(fuel_names, default=np.inf)

        self.bunker_price_overwrite = self._paths(fuel_names, default=np.nan)
        self.bunker_wtt_overwrite = self._paths(fuel_emissions, default=np.nan)

        self.bunker_supply = self._paths(fuel_names)
        self.bunker_price = self._paths(fuel_names)
        self.bunker_wtt = self._paths(fuel_emissions)

        self.shore_power_cost = self._path()
        self.shore_power_connection_share = self._path()
        self.shore_power_emission_factor = self._paths(emission_names)
