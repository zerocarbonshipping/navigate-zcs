# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The profile layer for the bunkering infrastructure: ports and the manager."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.profiles._fuel_emission_profile import _FuelEmissionProfile

if TYPE_CHECKING:
    from navigate.core.nodes.fuel import Fuel
    from navigate.util.types_ import FloatArray


class _FuelInfrastructureProfile(_FuelEmissionProfile):
    """Fuel bunkered, supplied and permitted by capacity at a bunkering location."""

    def __init__(self) -> None:
        super().__init__()

        self._bunker_mass: dict[str, FloatArray] = {}
        self._bunker_supply_mass: dict[str, FloatArray] = {}
        self._bunkering_limit_mass: dict[str, FloatArray] = {}

    def _initialize_fuel_infrastructure(self, fuels: dict[str, Fuel]) -> None:
        self._bunker_mass = self._default_dict(fuels)
        self._bunkering_limit_mass = self._default_dict(fuels, default=np.nan)

        for fuel_name, fuel in fuels.items():
            if fuel.liquid_market:
                self._bunker_supply_mass[fuel_name] = self._default_array(
                    default=np.nan
                )
            else:
                self._bunker_supply_mass[fuel_name] = self._default_array()

    def add_fuel_infrastructure_profile(
        self, profile: _FuelInfrastructureProfile, idx: int | slice = np.s_[:]
    ) -> None:
        """
        Add another fuel infrastructure profile's values into this one.

        Parameters
        ----------
        profile
            Infrastructure profile from another node.
        idx
            Time-step index or slice.
        """
        for fuel_name in self._bunker_mass:
            self._bunker_mass[fuel_name][idx] += profile._bunker_mass[fuel_name][idx]

        for fuel_name in self._bunker_supply_mass:
            self._bunker_supply_mass[fuel_name][idx] += profile._bunker_supply_mass[
                fuel_name
            ][idx]

        for fuel_name in self._bunkering_limit_mass:
            self._bunkering_limit_mass[fuel_name][idx] += profile._bunkering_limit_mass[
                fuel_name
            ][idx]

    def add_bunker_mass(
        self, fuel_name: str, mass: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._bunker_mass[fuel_name][idx] += mass

    def set_bunkering_limit_mass(self, idx: int, fuel_name: str, mass: float) -> None:
        self._bunkering_limit_mass[fuel_name][idx] = mass

    def set_bunker_supply_mass(self, idx: int, fuel_name: str, supply: float) -> None:
        self._bunker_supply_mass[fuel_name][idx] = supply

    def get_bunker_mass(self) -> dict[str, FloatArray]:
        return dict(self._bunker_mass)

    def get_bunker_energy(self) -> dict[str, FloatArray]:
        return self._fuel_mass_to_energy(self._bunker_mass)

    def get_bunker_supply_mass(self) -> dict[str, FloatArray]:
        return dict(self._bunker_supply_mass)

    def get_bunker_supply_energy(self) -> dict[str, FloatArray]:
        return self._fuel_mass_to_energy(self._bunker_supply_mass)

    def get_bunkering_limit_mass(self) -> dict[str, FloatArray]:
        return dict(self._bunkering_limit_mass)

    def get_bunkering_limit_energy(self) -> dict[str, FloatArray]:
        return self._fuel_mass_to_energy(self._bunkering_limit_mass)
