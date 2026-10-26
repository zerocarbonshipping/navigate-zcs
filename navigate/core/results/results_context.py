# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""ResultsContext, the run-wide constants all results are sized and converted by."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import FuelTypeID

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.util.types_ import FloatArray


@dataclass(frozen=True, slots=True, eq=False)
class ResultsContext:
    """
    The timeline, fuels and emissions of a run, shared by all of its results.

    Parameters
    ----------
    timeline
        Simulation timeline, in years.
    lower_heating_value
        Lower heating value per fuel, GJ/ton; its keys are the fuels of the run.
    fuel_type
        Fuel type per fuel.
    liquid_market_fuels
        The fuels traded on a liquid market.
    global_warming_potential
        Global warming potential per emission at the run's emissions lifetime; its
        keys are the emissions of the run.
    """

    timeline: FloatArray
    lower_heating_value: dict[str, float]
    fuel_type: dict[str, FuelTypeID]
    liquid_market_fuels: frozenset[str]
    global_warming_potential: dict[str, float]

    @classmethod
    def from_nodes(
        cls,
        timeline: FloatArray,
        fuels: dict[str, Fuel],
        emissions: dict[str, Emission],
        emissions_lifetime: float,
    ) -> ResultsContext:
        """
        Read the constants of a run off its fuel and emission nodes.

        Parameters
        ----------
        timeline
            Simulation timeline, in years.
        fuels
            All fuels in the simulation.
        emissions
            All emissions in the simulation.
        emissions_lifetime
            Lifetime the global warming potentials are read at, in years.

        Returns
        -------
        ResultsContext
            The context all results of the run are initialized with.
        """
        lower_heating_value: dict[str, float] = {}
        fuel_type: dict[str, FuelTypeID] = {}
        liquid_market_fuels: set[str] = set()

        # read without an input, a heating value is one number, not an array
        for name, fuel in fuels.items():
            lower_heating_value[name] = float(fuel.lower_heating_value.get())
            fuel_type[name] = fuel.fuel_type

            if fuel.liquid_market:
                liquid_market_fuels.add(name)

        global_warming_potential: dict[str, float] = {}

        # read at one lifetime, a warming potential is one number, not an array
        for name, emission in emissions.items():
            potential = emission.global_warming_potential.get(emissions_lifetime)
            global_warming_potential[name] = float(potential)

        return cls(
            timeline=timeline,
            lower_heating_value=lower_heating_value,
            fuel_type=fuel_type,
            liquid_market_fuels=frozenset(liquid_market_fuels),
            global_warming_potential=global_warming_potential,
        )

    @property
    def fuels(self) -> list[str]:
        """Name the fuels of the run."""
        return list(self.lower_heating_value)

    @property
    def emissions(self) -> list[str]:
        """Name the emissions of the run."""
        return list(self.global_warming_potential)

    def energy(self, mass: dict[str, FloatArray]) -> dict[str, FloatArray]:
        """
        Convert fuel masses to their energy, GJ, at the fuels' heating values.

        Parameters
        ----------
        mass
            Mass per fuel, t.

        Returns
        -------
        dict[str, FloatArray]
            Energy per fuel, GJ.
        """
        heating_value = self.lower_heating_value
        energy: dict[str, FloatArray] = {}

        for fuel_name, fuel_mass in mass.items():
            energy[fuel_name] = fuel_mass * heating_value[fuel_name]

        return energy

    def fuel_type_energy(
        self, mass: dict[str, FloatArray]
    ) -> dict[FuelTypeID, FloatArray]:
        """
        Sum the energy of fuel masses per fuel type, every fuel type included.

        Parameters
        ----------
        mass
            Mass per fuel of the run, t.

        Returns
        -------
        dict[FuelTypeID, FloatArray]
            Energy per fuel type, GJ; 0 for a type no fuel of the run has.
        """
        energy = {fuel_type: np.zeros(self.timeline.shape) for fuel_type in FuelTypeID}

        for fuel_name, fuel_energy in self.energy(mass).items():
            energy[self.fuel_type[fuel_name]] += fuel_energy

        return energy

    def equivalent(
        self, emissions: dict[tuple[str, str], FloatArray]
    ) -> dict[tuple[str, str], FloatArray]:
        """
        Weigh emissions by their global warming potential into CO2-equivalents.

        Parameters
        ----------
        emissions
            Emissions keyed by (fuel, emission).

        Returns
        -------
        dict[tuple[str, str], FloatArray]
            The CO2-equivalents under the same keys.
        """
        potential = self.global_warming_potential
        equivalents: dict[tuple[str, str], FloatArray] = {}

        for (fuel_name, emission_name), emission in emissions.items():
            equivalents[fuel_name, emission_name] = emission * potential[emission_name]

        return equivalents

    def equivalent_by_emission(
        self, emissions: dict[str, FloatArray]
    ) -> dict[str, FloatArray]:
        """
        Weigh emissions by their global warming potential into CO2-equivalents.

        Parameters
        ----------
        emissions
            Emissions keyed by emission.

        Returns
        -------
        dict[str, FloatArray]
            The CO2-equivalents under the same keys.
        """
        potential = self.global_warming_potential
        equivalents: dict[str, FloatArray] = {}

        for emission_name, emission in emissions.items():
            equivalents[emission_name] = emission * potential[emission_name]

        return equivalents
