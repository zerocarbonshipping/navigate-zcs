# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The profile layer that weighs emissions by their global warming potential."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.profiles._fuel_base_profile import _FuelBaseProfile

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.util.types_ import FloatArray


class _FuelEmissionProfile(_FuelBaseProfile):
    """Global warming potentials for the fuel profiles that weigh emissions."""

    def __init__(self) -> None:
        super().__init__()

        self._global_warming_potential: dict[str, float] = {}

    def _initialize_fuel_emission(
        self, emissions: dict[str, Emission], emissions_lifetime: float
    ) -> None:
        """
        Read each emission's global warming potential at the given lifetime.

        Parameters
        ----------
        emissions
            All emissions in the simulation.
        emissions_lifetime
            Lifetime the global warming potentials are read at, in years.
        """
        # a warming potential read at a single lifetime is one number, while the
        # getter's return type also covers the array an array input would produce
        self._global_warming_potential = {
            emission_name: float(
                emission.global_warming_potential.get(emissions_lifetime)
            )
            for emission_name, emission in emissions.items()
        }

    def _equivalent(
        self, emissions: dict[tuple[str, str], FloatArray]
    ) -> dict[tuple[str, str], FloatArray]:
        return {
            (fuel_name, emission_name): emission
            * self._global_warming_potential[emission_name]
            for (fuel_name, emission_name), emission in emissions.items()
        }

    def _equivalent_by_emission(
        self, emissions: dict[str, FloatArray]
    ) -> dict[str, FloatArray]:
        return {
            emission_name: emission * self._global_warming_potential[emission_name]
            for emission_name, emission in emissions.items()
        }
