# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import FuelTypeID
from navigate.core.profiles._base_profile import _BaseProfile

if TYPE_CHECKING:
    from navigate.fuel import Fuel


class _FuelBaseProfile(_BaseProfile):
    """
    This class is used exclusively for sub-classing.
    """
    def __init__(self):
        super().__init__()

        # constants
        self._fuel_type: dict[str, FuelTypeID] = {}            # fuel type of fuel, for convenience
        self._lower_heating_value: dict[str, float] = {}  # lower heating value of fuel, for convenience
        self._mass_density: dict[str, float] = {}         # mass density of fuel, for convenience

    def _initialize_fuel_base(self, fuels: dict[str, Fuel]) -> None:
        """

        Parameters
        ----------
        fuels :
            All fuels in the simulation.
        """

        for fuel_name, fuel in fuels.items():

            self._fuel_type[fuel_name] = fuel.fuel_type
            self._lower_heating_value[fuel_name] = fuel.lower_heating_value.get()
            self._mass_density[fuel_name] = fuel.mass_density.get()

    @staticmethod
    def _fuel_mass_grouping(out: dict[str, np.ndarray], group: dict[str, str],
                            mass: dict[str, np.ndarray], idx: int | slice,
                            conversion: dict[str, float] | None = None) -> dict[str, np.ndarray]:

        if conversion is None:
            conversion = {fuel_name: 1. for fuel_name in group}

        for fuel_name, key in group.items():
            out[key] += mass[fuel_name][idx] * conversion[fuel_name]

        return out

    def _fuel_mass_to_energy(self, mass: dict[str, np.ndarray], fuel_name: str | None,
                             idx: int | slice) -> np.ndarray | dict[str, np.ndarray]:
        return self._extract_multiply_dict(mass, self._lower_heating_value, fuel_name, idx)

    def _fuel_mass_to_volume(self, mass: dict[str, np.ndarray], fuel_name: str | None,
                             idx: int | slice) -> np.ndarray | dict[str, np.ndarray]:
        return self._extract_multiply_dict(mass, self._mass_density, fuel_name, idx)

    def _fuel_type_mass_to_mass(self, mass: dict[str, np.ndarray],
                                idx: int | slice) -> dict[str, np.ndarray]:
        result = self._default_dict(FuelTypeID)
        return self._fuel_mass_grouping(result, self._fuel_type, mass, idx)

    def _fuel_type_mass_to_energy(self, mass: dict[str, np.ndarray],
                                  idx: int | slice) -> dict[str, np.ndarray]:
        result = self._default_dict(FuelTypeID)
        return self._fuel_mass_grouping(result, self._fuel_type, mass, idx, conversion=self._lower_heating_value)
