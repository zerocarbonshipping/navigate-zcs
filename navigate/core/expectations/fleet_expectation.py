# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Fleet node, read by the fleet, fuel and bunker domains."""

from __future__ import annotations

from itertools import product
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import BunkerScopeID, FuelTypeID
from navigate.core.expectations._expectation import _Expectation

if TYPE_CHECKING:
    from collections.abc import Collection


class FleetExpectation(_Expectation):
    """Vessel counts, fuel demand, uptakes and realized fuel-type totals."""

    def __init__(
        self, length: int, vessel_names: Collection[str], fuel_names: Collection[str]
    ) -> None:
        super().__init__(length)

        self.count = self._paths(product(vessel_names, BunkerScopeID))
        self.fuel_demand = self._paths(fuel_names)

        # one row per vessel, one column per time step
        self.uptakes = np.zeros((len(vessel_names), length))

        self.fuel_type_capacity = self._values(FuelTypeID)
        self.fuel_type_supply = self._values(FuelTypeID)

    def reset_fuel_type_totals(self) -> None:
        """Zero the fuel-type capacity and supply totals, summed anew each step."""
        self.fuel_type_capacity = self._values(FuelTypeID)
        self.fuel_type_supply = self._values(FuelTypeID)
