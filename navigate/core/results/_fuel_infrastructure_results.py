# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The results layer for the bunkering infrastructure: the port and global results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.results._base_results import _BaseResults, accumulate, result

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class _FuelInfrastructureResults(_BaseResults):
    """Fuel bunkered, supplied and permitted by capacity at a bunkering location."""

    # the masses are written, the energies computed from them
    bunker_mass: dict[str, FloatArray] = result("t/year")
    bunker_supply_mass: dict[str, FloatArray] = result("t/year")
    bunkering_limit_mass: dict[str, FloatArray] = result("t/year")

    bunker_energy: dict[str, FloatArray] = result("GJ/year")
    bunker_supply_energy: dict[str, FloatArray] = result("GJ/year")
    bunkering_limit_energy: dict[str, FloatArray] = result("GJ/year")

    def _initialize_fuel_infrastructure(self) -> None:
        fuels = self.context.fuels

        self.bunker_mass = self._default_dict(fuels)
        self.bunker_supply_mass = self._default_dict(fuels)
        self.bunkering_limit_mass = self._default_dict(fuels, default=np.nan)

        # liquid-market supply is recorded only where a finite bunkering limit bounds it
        for fuel_name in self.context.liquid_market_fuels:
            self.bunker_supply_mass[fuel_name] = self._default_array(np.nan)

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
        accumulate(self.bunkering_limit_mass, results.bunkering_limit_mass)
