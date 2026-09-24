# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.profiles._base_profile import _BaseProfile
from navigate.util import multiply_dicts

if TYPE_CHECKING:
    from navigate.core.nodes.fuel import Fuel
    from navigate.util.types_ import FloatArray


class _FuelBaseProfile(_BaseProfile):
    """Base class used exclusively for sub-classing."""

    def __init__(self):
        super().__init__()

        # constants
        self._lower_heating_value: dict[
            str, float
        ] = {}  # lower heating value of fuel, for convenience

    def _initialize_fuel_base(self, fuels: dict[str, Fuel]) -> None:
        """
        Initialize the lower heating value lookup.

        Parameters
        ----------
        fuels :
            All fuels in the simulation.
        """
        for fuel_name, fuel in fuels.items():
            self._lower_heating_value[fuel_name] = fuel.lower_heating_value.get()

    def _fuel_mass_to_energy(
        self, mass: dict[str, FloatArray]
    ) -> dict[str, FloatArray]:
        return multiply_dicts(mass, self._lower_heating_value)
