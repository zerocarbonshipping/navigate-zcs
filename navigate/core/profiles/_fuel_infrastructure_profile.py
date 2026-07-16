# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.profiles._fuel_base_profile import _FuelBaseProfile
from navigate.util import extract_from_dict

if TYPE_CHECKING:
    from navigate.fuel import Fuel


class _FuelInfrastructureProfile(_FuelBaseProfile):
    """
    This class is used exclusively for sub-classing.
    """

    def __init__(self):
        super().__init__()

        self._bunker_mass: dict[str, np.ndarray] = {}           # amount bunkered, tons/year
        self._bunker_supply_mass: dict[str, np.ndarray] = {}    # available supply, tons/year
        self._bunkering_limit_mass: dict[str, np.ndarray] = {}  # infrastructure capacity, tons/year

    def _initialize_fuel_infrastructure(self, fuels: dict[str, Fuel]) -> None:

        self._bunker_mass = self._default_dict(fuels)
        self._bunkering_limit_mass = self._default_dict(fuels, default=np.nan)

        for fuel_name, fuel in fuels.items():

            if fuel.belongs_to_liquid_market():
                self._bunker_supply_mass[fuel_name] = self._default_array(default=np.nan)
            else:
                self._bunker_supply_mass[fuel_name] = self._default_array()

    def add_fuel_infrastructure_profile(self, profile: _FuelInfrastructureProfile, idx: int | slice = np.s_[:]) -> None:
        """

        Parameters
        ----------
        profile : _FuelInfrastructureProfile
            Profile to be added.
        idx : int
            Time-step index.
        """

        for key in self._bunker_mass:
            self._bunker_mass[key][idx] += profile._bunker_mass[key][idx]

        for key in self._bunker_supply_mass:
            self._bunker_supply_mass[key][idx] += profile._bunker_supply_mass[key][idx]

        for key in self._bunkering_limit_mass:
            self._bunkering_limit_mass[key][idx] += profile._bunkering_limit_mass[key][idx]

    def add_bunker_mass(self, idx: int, fuel_name: str, mass: float) -> None:
        self._bunker_mass[fuel_name][idx] += mass

    def set_bunkering_limit_mass(self, idx: int, fuel_name: str, mass: float) -> None:
        self._bunkering_limit_mass[fuel_name][idx] = mass

    def set_bunker_supply_mass(self, idx: int, fuel_name: str, supply: float) -> None:
        self._bunker_supply_mass[fuel_name][idx] = supply

    def get_bunker_mass(self, fuel_name: str | None = None, idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._bunker_mass, fuel_name, idx)

    def get_bunker_energy(self, fuel_name: str | None = None,
                          idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._fuel_mass_to_energy(self._bunker_mass, fuel_name, idx)

    def get_bunker_volume(self, fuel_name: str | None = None,
                          idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._fuel_mass_to_volume(self._bunker_mass, fuel_name, idx)

    def get_bunker_supply_mass(self, fuel_name: str | None = None,
                               idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._bunker_supply_mass, fuel_name, idx)

    def get_bunker_supply_energy(self, fuel_name: str | None = None,
                                 idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._fuel_mass_to_energy(self._bunker_supply_mass, fuel_name, idx)

    def get_bunker_supply_volume(self, fuel_name: str | None = None,
                                 idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._fuel_mass_to_volume(self._bunker_supply_mass, fuel_name, idx)

    def get_bunkering_limit_mass(self, fuel_name: str | None = None,
                                 idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._bunkering_limit_mass, fuel_name, idx)

    def get_bunkering_limit_energy(self, fuel_name: str | None = None,
                                   idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._fuel_mass_to_energy(self._bunkering_limit_mass, fuel_name, idx)

    def get_bunkering_limit_volume(self, fuel_name: str | None = None,
                                   idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._fuel_mass_to_volume(self._bunkering_limit_mass, fuel_name, idx)
