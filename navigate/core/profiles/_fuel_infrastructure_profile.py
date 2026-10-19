# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The profile layer for the bunkering infrastructure: the port and global profiles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.profiles._base_profile import _BaseProfile, accumulate, result

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class _FuelInfrastructureProfile(_BaseProfile):
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
        liquid_market = self.context.liquid_market_fuels

        self.bunker_mass = self._default_dict(fuels)
        self.bunkering_limit_mass = self._default_dict(fuels, default=np.nan)
        self.bunker_supply_mass = {
            fuel_name: self._default_array(
                np.nan if fuel_name in liquid_market else None
            )
            for fuel_name in fuels
        }

    def add_fuel_infrastructure_profile(
        self, profile: _FuelInfrastructureProfile
    ) -> None:
        """
        Add another fuel infrastructure profile's values into this one.

        Parameters
        ----------
        profile
            Infrastructure profile from another node.
        """
        accumulate(self.bunker_mass, profile.bunker_mass)
        accumulate(self.bunker_supply_mass, profile.bunker_supply_mass)
        accumulate(self.bunkering_limit_mass, profile.bunkering_limit_mass)
