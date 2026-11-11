# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The results layer for the bunkering infrastructure: the port and global results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from navigate.core.results.base_results import BaseResults, Unit, accumulate, result

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class _FuelInfrastructureResults(BaseResults):
    """Fuel bunkered and supplied at a bunkering location."""

    # each mass is written, its energy computed from it
    bunker_mass: dict[str, FloatArray] = result(Unit.TON_PER_YEAR)
    bunker_supply_mass: dict[str, FloatArray] = result(Unit.TON_PER_YEAR)

    bunker_energy: dict[str, FloatArray] = result(Unit.GJ_PER_YEAR)
    bunker_supply_energy: dict[str, FloatArray] = result(Unit.GJ_PER_YEAR)

    def _initialize_fuel_infrastructure(self) -> None:
        fuels = self.context.fuels

        self.bunker_mass = self._default_dict(fuels)
        self.bunker_supply_mass = self._default_dict(fuels)

    def add_fuel_infrastructure_results(
        self, results: _FuelInfrastructureResults
    ) -> None:
        """
        Add another fuel infrastructure's results into this one.

        Parameters
        ----------
        results
            Infrastructure results from another node.
        """
        accumulate(self.bunker_mass, results.bunker_mass)
        accumulate(self.bunker_supply_mass, results.bunker_supply_mass)
