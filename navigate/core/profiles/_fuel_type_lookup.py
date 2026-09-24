# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Fuel-type lookup, mixed into the profile branches that aggregate by fuel type."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import FuelTypeID
from navigate.core.profiles._base_profile import _BaseProfile
from navigate.exceptions import no_value_assigned_error

if TYPE_CHECKING:
    from navigate.core.nodes.fuel import Fuel
    from navigate.util.types_ import FloatArray


class _FuelTypeLookup(_BaseProfile):
    """Fuel type of each fuel, mixed into the branches that aggregate by fuel type."""

    # filled by _FuelBaseProfile, which every class mixing this in also inherits
    _lower_heating_value: dict[str, float]

    def __init__(self) -> None:
        super().__init__()

        self._fuel_type: dict[str, FuelTypeID] = {}  # fuel type of fuel

    def _initialize_fuel_type(self, fuels: dict[str, Fuel]) -> None:
        """
        Initialize the fuel type lookup.

        Parameters
        ----------
        fuels :
            All fuels in the simulation.
        """
        for fuel_name, fuel in fuels.items():
            if fuel.fuel_type is None:
                no_value_assigned_error(fuel, "FuelType")

            self._fuel_type[fuel_name] = fuel.fuel_type

    def _fuel_type_mass_to_energy(
        self, mass: dict[str, FloatArray]
    ) -> dict[FuelTypeID, FloatArray]:
        energy = self._default_dict(FuelTypeID)

        for fuel_name, fuel_type in self._fuel_type.items():
            energy[fuel_type] += mass[fuel_name] * self._lower_heating_value[fuel_name]

        return energy
