# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The profile layer that turns a fuel mass into the energy it carries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.profiles._base_profile import _BaseProfile

if TYPE_CHECKING:
    from navigate.core.nodes.fuel import Fuel
    from navigate.util.types_ import FloatArray


class _FuelBaseProfile(_BaseProfile):
    """Lower heating value of each fuel, for the branches that report fuel energy."""

    def __init__(self) -> None:
        super().__init__()

        self._lower_heating_value: dict[str, float] = {}

    def _initialize_fuel_base(self, fuels: dict[str, Fuel]) -> None:
        """
        Initialize the lower heating value lookup.

        Parameters
        ----------
        fuels
            All fuels in the simulation.
        """
        for fuel_name, fuel in fuels.items():
            # a heating value read without an input is one number, while the
            # getter's return type also covers the array an array input produces
            self._lower_heating_value[fuel_name] = float(fuel.lower_heating_value.get())

    def _fuel_mass_to_energy(
        self, mass: dict[str, FloatArray]
    ) -> dict[str, FloatArray]:
        return {
            fuel_name: fuel_mass * self._lower_heating_value[fuel_name]
            for fuel_name, fuel_mass in mass.items()
        }
