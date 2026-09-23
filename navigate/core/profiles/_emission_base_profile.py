# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from navigate.core.profiles._base_profile import _BaseProfile

if TYPE_CHECKING:
    from collections.abc import Mapping

    from navigate.util.types_ import FloatArray


class _GlobalWarmingPotential(Protocol):
    """Calculator duck type: the warming potential is read at an emissions lifetime."""

    def get(self, emissions_lifetime: float, /) -> float: ...


class _EmissionNode(Protocol):
    """Duck type of an emission node: the lookup reads only its warming potential."""

    @property
    def global_warming_potential(self) -> _GlobalWarmingPotential: ...


class _EmissionBaseProfile(_BaseProfile):
    """Base class used exclusively for sub-classing."""

    def __init__(self) -> None:
        super().__init__()

        self._global_warming_potential: dict[str, float] = {}  # CO2 equivalence factor

    def _initialize_global_warming_potential(
        self, emissions: Mapping[str, _EmissionNode], emissions_lifetime: float
    ) -> None:
        """
        Initialize the global warming potential lookup for every emission.

        Parameters
        ----------
        emissions :
            All emissions in the simulation.
        emissions_lifetime :
            Emissions lifetime used for calculating GWP.
        """
        self._global_warming_potential = {
            emission_name: emission.global_warming_potential.get(emissions_lifetime)
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
