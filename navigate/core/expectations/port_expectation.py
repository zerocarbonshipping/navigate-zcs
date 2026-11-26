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

        self.handling_cost = self._paths(fuel_names)  # currency/t
        self.bunkering_limit = self._paths(fuel_names, default=np.inf)  # t/year

        self.fuel_price = self._paths(fuel_names, default=np.nan)  # currency/t
        self.fuel_wtt = self._paths(fuel_emissions, default=np.nan)  # t/t

        self.bunker_supply = self._paths(fuel_names)  # t/year
        self.bunker_price = self._paths(fuel_names)  # currency/t
        self.bunker_wtt = self._paths(fuel_emissions)  # t/t

        self.shore_power_price = self._path()  # currency/GJ
        self.shore_power_availability = self._path()  # -
        self.shore_power_wtt = self._paths(emission_names)  # t/GJ
