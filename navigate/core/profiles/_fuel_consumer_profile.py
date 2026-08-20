# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable, KeysView
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import EnergyDemandTypeID, EnergyDemandTypePortID, FuelTypeID
from navigate.core.misc import EMPTY_FLOAT
from navigate.core.profiles._fuel_base_profile import _FuelBaseProfile

if TYPE_CHECKING:
    from navigate.fuel import Emission, Fuel

from navigate.util import (
    add_dicts,
    divide_nonzero,
    extract_from_dict,
    extract_from_tuple_dict,
    is_single_dict,
    is_tuple_dict,
    multiply_dicts,
    sum_dict_results,
)


class _FuelConsumerProfile(_FuelBaseProfile):
    """
    This class is used exclusively for sub-classing.
    """

    def __init__(self):
        super().__init__()

        # constants
        self._GWP: dict[str, float] = {}  # global warming potential of emission

        # raw energy demand
        self._raw_energy_sea: dict[EnergyDemandTypeID, np.ndarray] = {}     # GJ/year
        self._raw_energy_port: dict[EnergyDemandTypePortID, np.ndarray] = {}    # GJ/year

        # operational energy demand (after operational savings, before technology)
        self._operational_energy_sea: dict[EnergyDemandTypeID, np.ndarray] = {}     # GJ/year
        self._operational_energy_port: dict[EnergyDemandTypePortID, np.ndarray] = {}    # GJ/year

        # energy demand
        self._energy_sea: dict[EnergyDemandTypeID, np.ndarray] = {}     # GJ/year
        self._energy_port: dict[EnergyDemandTypePortID, np.ndarray] = {}    # GJ/year

        # consumed
        self._consumed_mass: dict[str, np.ndarray] = {}    # consumed fuel, tons/year

        # converter
        self._converter_mass: dict[FuelTypeID, dict[str, np.ndarray]] = {}  # tons/year

        # emissions
        self._WTT: dict[tuple[str, str], np.ndarray] = {}  # WTT emissions, tons/year
        self._TTW: dict[tuple[str, str], np.ndarray] = {}  # TTW emissions, tons/year

        # expenses
        self._fuel_expenses: dict[str, np.ndarray] = {}            # expenses from purchasing fuel, USD/year
        self._levy_expenses: dict[str, np.ndarray] = {}            # expenses from fuel levies, USD/year
        self._remedial_expenses: np.ndarray = EMPTY_FLOAT      # USD/year
        self._remedial_units: dict[str, np.ndarray] = {}           # per-policy remedial units, policy units/year
        self._levy_units: dict[str, np.ndarray] = {}               # per-policy levy emission units, policy units/year
        self._flexibility_expenses: np.ndarray = EMPTY_FLOAT   # USD/year
        self._surplus_revenue: np.ndarray = EMPTY_FLOAT        # USD/year

        # shore power (WTW-lumped emission, no fuel attribution)
        self._shore_power_energy: np.ndarray = EMPTY_FLOAT      # GJ/year
        self._shore_power_expenses: np.ndarray = EMPTY_FLOAT    # USD/year
        self._shore_power_emission: dict[str, np.ndarray] = {}  # ton/year

    def _initialize_fuel_consumer(self, fuels: dict[str, Fuel], emissions: dict[str, Emission], emissions_lifetime: float,
                                  regulation_names: list[str] = (), levy_names: list[str] = ()) -> None:
        """

        Parameters
        ----------
        fuels :
            All fuels in the simulation.
        emissions :
            All emissions in the simulation.
        emissions_lifetime :
            Emissions lifetime used for calculating GWP.
        regulation_names :
            Names of all regulations in the simulation.
        levy_names :
            Names of all levies in the simulation.
        """

        for emission_name, emission in emissions.items():
            self._GWP[emission_name] = emission.global_warming_potential.get(emissions_lifetime)

        self._raw_energy_sea = self._default_dict(EnergyDemandTypeID)
        self._raw_energy_port = self._default_dict(EnergyDemandTypePortID)

        self._operational_energy_sea = self._default_dict(EnergyDemandTypeID)
        self._operational_energy_port = self._default_dict(EnergyDemandTypePortID)

        self._energy_sea = self._default_dict(EnergyDemandTypeID)
        self._energy_port = self._default_dict(EnergyDemandTypePortID)

        self._consumed_mass = self._default_dict(fuels)

        self._converter_mass = {fuel_type: self._default_dict(fuels) for fuel_type in FuelTypeID}

        self._WTT = self._default_tuple_dict(fuels, emissions)
        self._TTW = self._default_tuple_dict(fuels, emissions)

        self._fuel_expenses = self._default_dict(fuels)
        self._levy_expenses = self._default_dict(fuels)
        self._remedial_expenses = self._default_array()
        self._remedial_units = self._default_dict(regulation_names)
        self._levy_units = self._default_dict(levy_names)
        self._flexibility_expenses = self._default_array()
        self._surplus_revenue = self._default_array()

        self._shore_power_energy = self._default_array()
        self._shore_power_expenses = self._default_array()
        self._shore_power_emission = self._default_dict(emissions)

    def add_fuel_consumer_profile(self, profile: _FuelConsumerProfile,
                                  multiplier: float = 1., idx: int | slice = np.s_[:]) -> None:
        """

        Parameters
        ----------
        profile : _FuelConsumerProfile
            Consumer profile from another node.
        multiplier : float
            Multiplier applied to each additive attribute when adding.
        idx : int
            Current time-step index.
        """

        for energy_id in EnergyDemandTypeID:
            self._raw_energy_sea[energy_id][idx] += multiplier * profile._raw_energy_sea[energy_id][idx]

        for energy_id in EnergyDemandTypePortID:
            self._raw_energy_port[energy_id][idx] += multiplier * profile._raw_energy_port[energy_id][idx]

        for energy_id in EnergyDemandTypeID:
            self._operational_energy_sea[energy_id][idx] += multiplier * profile._operational_energy_sea[energy_id][idx]

        for energy_id in EnergyDemandTypePortID:
            self._operational_energy_port[energy_id][idx] += multiplier * profile._operational_energy_port[energy_id][idx]

        for energy_id in EnergyDemandTypeID:
            self._energy_sea[energy_id][idx] += multiplier * profile._energy_sea[energy_id][idx]

        for energy_id in EnergyDemandTypePortID:
            self._energy_port[energy_id][idx] += multiplier * profile._energy_port[energy_id][idx]

        for key in self._consumed_mass:
            self._consumed_mass[key][idx] += profile._consumed_mass[key][idx] * multiplier

        for key1, fuel_mass in self._converter_mass.items():
            for key2 in fuel_mass:
                self._converter_mass[key1][key2][idx] += profile._converter_mass[key1][key2][idx] * multiplier

        for key in self._WTT:
            self._WTT[key][idx] += profile._WTT[key][idx] * multiplier

        for key in self._TTW:
            self._TTW[key][idx] += profile._TTW[key][idx] * multiplier

        for key in self._fuel_expenses:
            self._fuel_expenses[key][idx] += profile._fuel_expenses[key][idx] * multiplier

        for key in self._levy_expenses:
            self._levy_expenses[key][idx] += profile._levy_expenses[key][idx] * multiplier

        self._remedial_expenses[idx] += profile._remedial_expenses[idx] * multiplier
        self._flexibility_expenses[idx] += profile._flexibility_expenses[idx] * multiplier
        self._surplus_revenue[idx] += profile._surplus_revenue[idx] * multiplier

        self._shore_power_energy[idx] += profile._shore_power_energy[idx] * multiplier
        self._shore_power_expenses[idx] += profile._shore_power_expenses[idx] * multiplier

        for key in self._shore_power_emission:
            self._shore_power_emission[key][idx] += profile._shore_power_emission[key][idx] * multiplier

    def _get_equivalent(self, data: dict[tuple[str, str], np.ndarray], fuel_name: str | None = None,
                        emission_name: str | None = None,
                        idx: int | slice = np.s_[:]) -> np.ndarray | dict[tuple[str, str], np.ndarray]:

        if emission_name is not None:
            return extract_from_tuple_dict(data, key1=fuel_name, key2=emission_name, idx=idx,
                                           transform=lambda x: x * self._GWP[emission_name])

        if fuel_name is not None:
            return {(fuel_name, en): self._get_equivalent(data, fuel_name, en, idx)
                    for en in self._get_emissions()}

        return {key: self._get_equivalent(data, *key, idx) for key in self._get_fuel_emissions()}

    def _to_intensity(self, method: Callable, fuel_name: str | None = None,
                      emission_name: str | None = None, idx: int | slice = np.s_[:]) -> np.ndarray | dict:

        if fuel_name is not None:

            return self._to_fuel_intensity(method(fuel_name, emission_name, idx), idx)

        elif emission_name is not None:

            return self._to_emission_intensity(method(fuel_name, emission_name, idx), idx)

        else:

            energy = self.get_total_consumed_energy(idx)

            try:

                return {key: self._convert_to_intensity(method(*key, idx), energy)
                        for key in self._get_fuel_emissions()}

            except TypeError:

                return self._convert_to_intensity(method(idx), energy)

    def _to_emission_intensity(self, emissions: dict[str, np.ndarray],
                               idx: int | slice) -> dict[str, np.ndarray] | None:

        energy = self.get_total_consumed_energy(idx)

        if isinstance(emissions, dict):

            return {emission_name: self._convert_to_intensity(emission[idx], energy)
                    for emission_name, emission in emissions.items()}

    def _to_fuel_intensity(self, emissions: np.ndarray | dict,
                           idx: int | slice) -> np.ndarray | dict | None:
        """

        Parameters
        ----------
        emissions : np.ndarray | dict[np.ndarray]
            Dict of emissions for each fuel. May be either a single dict (emissions collapsed) or a tuple dict.
        idx : int
            Time-step index.

        Returns
        -------
        np.ndarray | dict[np.ndarray]
            Emissions intensity.
        """

        if isinstance(emissions, dict):

            if is_single_dict(emissions):

                return {fuel_name: self._convert_to_intensity(emission[idx],
                                                              self.get_consumed_energy(fuel_name, idx))
                        for fuel_name, emission in emissions.items()}

            elif is_tuple_dict(emissions):

                return {(fuel_name, emission_name): self._convert_to_intensity(emission[idx],
                                                                               self.get_consumed_energy(fuel_name, idx))
                        for (fuel_name, emission_name), emission in emissions.items()}

    def _convert_to_intensity(self, emission: np.ndarray, energy: np.ndarray) -> np.ndarray:
        # emissions are converted from ton to g (10^6)
        # and energy is converted from GJ to MJ (10^3),
        # so dividing by 10^3
        return divide_nonzero(emission, (energy / 1e3))

    def _converter_fuel_type_share(self, fuel_type: FuelTypeID,
                                   idx: int | slice = np.s_[:]) -> np.ndarray:
        # TODO: may not work when using multiple main fuel types

        energy = self.get_converter_energy(fuel_type, idx)
        main_fuel = np.sum([e for fuel_name, e in energy.items() if self._fuel_type[fuel_name] == fuel_type], axis=0)
        total_fuel = np.sum(list(energy.values()), axis=0)

        return divide_nonzero(main_fuel, total_fuel)

    def _get_emissions(self) -> KeysView[str]:
        return self._GWP.keys()

    def _get_fuel_emissions(self) -> KeysView[tuple[str, str]]:
        return self._WTT.keys()

    def add_consumed_mass(self, fuel_name: str, mass: float, idx: int | slice = np.s_[:]) -> None:
        self._consumed_mass[fuel_name][idx] += mass

    def add_converter_mass(self, fuel_type: FuelTypeID, fuel_name: str, mass: float, idx: int | slice = np.s_[:]) -> None:
        self._converter_mass[fuel_type][fuel_name][idx] += mass

    def add_WTT(self, fuel_name: str, emission_name: str, WTT: float, idx: int | slice = np.s_[:]) -> None:
        self._WTT[(fuel_name, emission_name)][idx] += WTT

    def add_TTW(self, fuel_name: str, emission_name: str, TTW: float, idx: int | slice = np.s_[:]) -> None:
        self._TTW[(fuel_name, emission_name)][idx] += TTW

    def add_fuel_expenses(self, fuel_name: str, expenses: float, idx: int | slice = np.s_[:]) -> None:
        self._fuel_expenses[fuel_name][idx] += expenses

    def add_levy_expenses(self, fuel_name: str, expenses: float, idx: int | slice = np.s_[:]) -> None:
        self._levy_expenses[fuel_name][idx] += expenses

    def add_remedial_expenses(self, idx: int | slice, expenses: float) -> None:
        self._remedial_expenses[idx] += expenses

    def add_remedial_units(self, policy_name: str, idx: int | slice, units: float) -> None:
        self._remedial_units[policy_name][idx] += units

    def get_remedial_units(self, policy_name: str, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._remedial_units[policy_name][idx]

    def add_levy_units(self, policy_name: str, idx: int | slice, units: float) -> None:
        self._levy_units[policy_name][idx] += units

    def get_levy_units(self, policy_name: str, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._levy_units[policy_name][idx]

    def add_flexibility_expenses(self, idx: int | slice, expenses: float) -> None:
        self._flexibility_expenses[idx] += expenses

    def add_surplus_revenue(self, idx: int | slice, revenue: float) -> None:
        self._surplus_revenue[idx] += revenue

    def add_shore_power_energy(self, idx: int | slice, energy: float) -> None:
        self._shore_power_energy[idx] += energy

    def add_shore_power_expenses(self, idx: int | slice, expenses: float) -> None:
        self._shore_power_expenses[idx] += expenses

    def add_shore_power_emission(self, emission_name: str, idx: int | slice, emission: float) -> None:
        self._shore_power_emission[emission_name][idx] += emission

    def get_raw_energy_sea(self, energy_id: EnergyDemandTypeID | None = None,
                           idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._raw_energy_sea, energy_id, idx)

    def get_raw_energy_port(self, energy_id: EnergyDemandTypeID | None = None,
                            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._raw_energy_port, energy_id, idx)

    def get_raw_energy(self, energy_id: EnergyDemandTypeID | None = None, idx: int | slice = np.s_[:]) -> np.ndarray:
        sea_energies = self.get_raw_energy_sea(energy_id, idx)
        port_energies = 0. if energy_id == EnergyDemandTypeID.PROPULSION else self.get_raw_energy_port(energy_id, idx)
        if energy_id:
            return sea_energies + port_energies
        else:
            return np.sum(list(sea_energies.values()), axis=0) + np.sum(list(port_energies.values()), axis=0)

    def get_operational_energy_sea(self, energy_id: EnergyDemandTypeID | None = None,
                                   idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._operational_energy_sea, energy_id, idx)

    def get_operational_energy_port(self, energy_id: EnergyDemandTypeID | None = None,
                                    idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._operational_energy_port, energy_id, idx)

    def get_operational_energy(self, energy_id: EnergyDemandTypeID | None = None, idx: int | slice = np.s_[:]) -> np.ndarray:
        sea_energies = self.get_operational_energy_sea(energy_id, idx)
        port_energies = 0. if energy_id == EnergyDemandTypeID.PROPULSION else self.get_operational_energy_port(energy_id, idx)
        if energy_id:
            return sea_energies + port_energies
        else:
            return np.sum(list(sea_energies.values()), axis=0) + np.sum(list(port_energies.values()), axis=0)

    def get_energy_sea(self, energy_id: EnergyDemandTypeID | None = None,
                       idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._energy_sea, energy_id, idx)

    def get_energy_port(self, energy_id: EnergyDemandTypeID | None = None,
                        idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._energy_port, energy_id, idx)

    def get_total_energy_port(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._get_total_method(self.get_energy_port, idx)

    def get_energy(self, energy_id: EnergyDemandTypeID | None = None, idx: int | slice = np.s_[:]) -> np.ndarray:
        sea_energies = self.get_energy_sea(energy_id, idx)
        port_energies = 0. if energy_id == EnergyDemandTypeID.PROPULSION else self.get_energy_port(energy_id, idx)
        if energy_id:
            return sea_energies + port_energies
        else:
            return np.sum(list(sea_energies.values()), axis=0) + np.sum(list(port_energies.values()), axis=0)

    def get_saving(self, demand_type: EnergyDemandTypeID, idx: int | slice = np.s_[:]) -> np.ndarray:
        if demand_type == EnergyDemandTypeID.PROPULSION:
            return 1. - divide_nonzero(self._energy_sea[demand_type][idx],
                                       self._raw_energy_sea[demand_type][idx], default=1.)
        else:
            return 1. - divide_nonzero(self._energy_sea[demand_type][idx] + self._energy_port[demand_type][idx],
                                       self._raw_energy_sea[demand_type][idx] + self._raw_energy_port[demand_type][idx],
                                       default=1.)

    def get_speed_energy_intensity_saving(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return 1. - divide_nonzero(self.get_raw_energy(idx=idx), self.get_baseline_energy(idx), default=1.)

    def get_operational_energy_intensity_saving(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return 1. - divide_nonzero(self.get_operational_energy(idx=idx), self.get_baseline_energy(idx), default=1.)

    def get_technology_energy_intensity_saving(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        # cargo-miles cancel between energy and operational energy
        return 1. - divide_nonzero(self.get_energy(idx=idx), self.get_operational_energy(idx=idx), default=1.)

    def get_energy_intensity_saving(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return 1. - divide_nonzero(self.get_energy(idx=idx), self.get_baseline_energy(idx), default=1.)

    def get_consumed_energy(self, fuel_name: str | None = None,
                            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._fuel_mass_to_energy(self._consumed_mass, fuel_name, idx)

    def get_fuel_type_energy(self, idx: int | slice = np.s_[:]) -> dict[str, np.ndarray]:
        return self._fuel_type_mass_to_energy(self._consumed_mass, idx)

    def get_total_consumed_energy(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._get_total_method(self.get_consumed_energy, idx) + self._shore_power_energy[idx]

    def get_converter_energy(self, fuel_type: FuelTypeID | None = None,
                             idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._extract_multiply_nested_dict(self._converter_mass, self._lower_heating_value, fuel_type, idx)

    def get_pilot_fuel_share(self, fuel_type: FuelTypeID | None = None,
                             idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        if fuel_type is not None:
            return 1. - self._converter_fuel_type_share(fuel_type, idx)
        else:
            return {fuel_type: self.get_pilot_fuel_share(fuel_type, idx) for fuel_type in FuelTypeID}

    def get_shore_power_energy(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._shore_power_energy[idx]

    def get_shore_power_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._shore_power_expenses[idx]

    def get_shore_power_emission(
            self, emission_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._shore_power_emission, emission_name, idx)

    def _get_shore_power_equivalent(self, idx: int | slice = np.s_[:]) -> np.ndarray | float:
        return sum_dict_results(multiply_dicts(self._shore_power_emission, self._GWP), idx=idx)

    def get_fuel_expenses(self, fuel_name: str | None = None,
                          idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._fuel_expenses, fuel_name, idx)

    def get_levy_expenses(self, fuel_name: str | None = None,
                          idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._levy_expenses, fuel_name, idx)

    def get_fuel_related_expenses(self, fuel_name: str | None = None,
                                  idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._extract_add_dicts(self._fuel_expenses, self._levy_expenses,
                                       key=fuel_name, idx=idx)

    def get_remedial_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._remedial_expenses[idx]

    def get_flexibility_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._flexibility_expenses[idx]

    def get_surplus_revenue(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._surplus_revenue[idx]

    def get_regulation_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._remedial_expenses[idx] + self._flexibility_expenses[idx] - self._surplus_revenue[idx]

    def get_total_fuel_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._get_total_method(self.get_fuel_expenses, idx) + self._shore_power_expenses[idx]

    def get_total_levy_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._get_total_method(self.get_levy_expenses, idx)

    def get_total_fuel_related_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return (self.get_total_fuel_expenses(idx)
                + self.get_total_levy_expenses(idx))

    def get_cumulative_fuel_expenses(self) -> dict[str, np.ndarray]:
        return self._to_cumulative_dict(self._fuel_expenses)

    def get_cumulative_levy_expenses(self) -> dict[str, np.ndarray]:
        return self._to_cumulative_dict(self._levy_expenses)

    def get_cumulative_fuel_related_expenses(self) -> dict[str, np.ndarray]:
        return self._to_cumulative_dict(add_dicts(self._fuel_expenses,
                                                  self._levy_expenses))

    def get_cumulative_remedial_expenses(self) -> np.ndarray:
        return self._to_cumulative(self.get_remedial_expenses())

    def get_cumulative_flexibility_expenses(self) -> np.ndarray:
        return self._to_cumulative(self.get_flexibility_expenses())

    def get_cumulative_surplus_revenue(self) -> np.ndarray:
        return self._to_cumulative(self.get_surplus_revenue())

    def get_cumulative_regulation_expenses(self) -> np.ndarray:
        return self._to_cumulative(self.get_regulation_expenses())

    def get_cumulative_total_fuel_expenses(self) -> np.ndarray:
        return self._to_cumulative(self.get_total_fuel_expenses())

    def get_cumulative_total_levy_expenses(self) -> np.ndarray:
        return self._to_cumulative(self.get_total_levy_expenses())

    def get_cumulative_total_fuel_related_expenses(self) -> np.ndarray:
        return self._to_cumulative(self.get_total_fuel_related_expenses())

    def get_equivalent_WTT(self, fuel_name: str | None = None, emission_name: str | None = None,
                           idx: int | slice = np.s_[:]) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        return self._get_equivalent(self._WTT, fuel_name, emission_name, idx)

    def get_total_equivalent_WTT(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._get_total_method(self.get_equivalent_WTT, idx)

    def get_cumulative_equivalent_WTT(self, fuel_name: str | None = None,
                                      emission_name: str | None = None) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        return self._to_cumulative_any(self.get_equivalent_WTT(fuel_name, emission_name))

    def get_cumulative_total_equivalent_WTT(self) -> np.ndarray:
        return self._to_cumulative(self.get_total_equivalent_WTT())

    def get_intensity_equivalent_WTT(self, fuel_name: str | None = None, emission_name: str | None = None,
                                     idx: int | slice = np.s_[:]) -> np.ndarray | dict:
        return self._to_intensity(self.get_equivalent_WTT, fuel_name, emission_name, idx)

    def get_intensity_total_equivalent_WTT(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._to_intensity(self.get_total_equivalent_WTT, idx=idx)

    def get_equivalent_TTW(self, fuel_name: str | None = None, emission_name: str | None = None,
                           idx: int | slice = np.s_[:]) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        return self._get_equivalent(self._TTW, fuel_name, emission_name, idx)

    def get_total_equivalent_TTW(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._get_total_method(self.get_equivalent_TTW, idx)

    def get_cumulative_equivalent_TTW(self, fuel_name: str | None = None,
                                      emission_name: str | None = None) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        return self._to_cumulative_any(self.get_equivalent_TTW(fuel_name, emission_name))

    def get_cumulative_total_equivalent_TTW(self) -> np.ndarray:
        return self._to_cumulative(self.get_total_equivalent_TTW())

    def get_intensity_equivalent_TTW(self, fuel_name: str | None = None, emission_name: str | None = None,
                                     idx: int | slice = np.s_[:]) -> np.ndarray | dict:
        return self._to_intensity(self.get_equivalent_TTW, fuel_name, emission_name, idx)

    def get_intensity_total_equivalent_TTW(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._to_intensity(self.get_total_equivalent_TTW, idx=idx)

    def get_equivalent_WTW(self, fuel_name: str | None = None, emission_name: str | None = None,
                           idx: int | slice = np.s_[:]) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        return self._get_equivalent(add_dicts(self._WTT, self._TTW), fuel_name, emission_name, idx)

    def get_total_equivalent_WTW(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        # shore power emissions are a WTW lump with no (fuel, emission) attribution,
        # so they enter the total but not the per-key getters
        return self._get_total_method(self.get_equivalent_WTW, idx) + self._get_shore_power_equivalent(idx)

    def get_cumulative_equivalent_WTW(self, fuel_name: str | None = None,
                                      emission_name: str | None = None) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        return self._to_cumulative_any(self.get_equivalent_WTW(fuel_name, emission_name))

    def get_cumulative_total_equivalent_WTW(self) -> np.ndarray:
        return self._to_cumulative(self.get_total_equivalent_WTW())

    def get_intensity_equivalent_WTW(self, fuel_name: str | None = None, emission_name: str | None = None,
                                     idx: int | slice = np.s_[:]) -> np.ndarray | dict:
        return self._to_intensity(self.get_equivalent_WTW, fuel_name, emission_name, idx)

    def get_intensity_total_equivalent_WTW(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._to_intensity(self.get_total_equivalent_WTW, idx=idx)
