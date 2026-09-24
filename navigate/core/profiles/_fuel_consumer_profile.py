# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import EnergyDemandTypeID, EnergyDemandTypePortID, FuelTypeID
from navigate.core.initial_values import EMPTY_FLOAT
from navigate.core.profiles._fuel_emission_profile import _FuelEmissionProfile

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.util.types_ import FloatArray

from navigate.util import add_dicts, divide_nonzero, multiply_dicts


class _FuelConsumerProfile(_FuelEmissionProfile):
    """Base class used exclusively for sub-classing."""

    def __init__(self):
        super().__init__()

        # raw energy demand
        self._raw_energy_sea: dict[EnergyDemandTypeID, np.ndarray] = {}  # GJ/year
        self._raw_energy_port: dict[EnergyDemandTypePortID, np.ndarray] = {}  # GJ/year

        # operational energy demand (after operational savings, before technology)
        self._operational_energy_sea: dict[
            EnergyDemandTypeID, np.ndarray
        ] = {}  # GJ/year
        self._operational_energy_port: dict[
            EnergyDemandTypePortID, np.ndarray
        ] = {}  # GJ/year

        # energy demand
        self._energy_sea: dict[EnergyDemandTypeID, np.ndarray] = {}  # GJ/year
        self._energy_port: dict[EnergyDemandTypePortID, np.ndarray] = {}  # GJ/year

        # consumed
        self._consumed_mass: dict[str, np.ndarray] = {}  # consumed fuel, tons/year

        # converter
        self._converter_mass: dict[FuelTypeID, dict[str, np.ndarray]] = {}  # tons/year

        # emissions
        self._wtt: dict[tuple[str, str], np.ndarray] = {}  # WTT emissions, tons/year
        self._ttw: dict[tuple[str, str], np.ndarray] = {}  # TTW emissions, tons/year

        # expenses
        self._fuel_expenses: dict[
            str, np.ndarray
        ] = {}  # expenses from purchasing fuel, USD/year
        self._levy_expenses: dict[
            str, np.ndarray
        ] = {}  # expenses from fuel levies, USD/year
        self._remedial_expenses: np.ndarray = EMPTY_FLOAT  # USD/year
        self._remedial_units: dict[
            str, np.ndarray
        ] = {}  # per-policy remedial units, policy units/year
        self._levy_units: dict[
            str, np.ndarray
        ] = {}  # per-policy levy emission units, policy units/year
        self._flexibility_expenses: np.ndarray = EMPTY_FLOAT  # USD/year
        self._surplus_revenue: np.ndarray = EMPTY_FLOAT  # USD/year

        # shore power (WTW-lumped emission, no fuel attribution)
        self._shore_power_energy: np.ndarray = EMPTY_FLOAT  # GJ/year
        self._shore_power_expenses: np.ndarray = EMPTY_FLOAT  # USD/year
        self._shore_power_emission: dict[str, np.ndarray] = {}  # ton/year

    def _initialize_fuel_consumer(
        self,
        fuels: dict[str, Fuel],
        emissions: dict[str, Emission],
        regulation_names: list[str] = (),
        levy_names: list[str] = (),
    ) -> None:
        """
        Initialize per-fuel and per-emission lookups for the fuel consumer profile.

        Parameters
        ----------
        fuels :
            All fuels in the simulation.
        emissions :
            All emissions in the simulation.
        regulation_names :
            Names of all regulations in the simulation.
        levy_names :
            Names of all levies in the simulation.
        """
        self._raw_energy_sea = self._default_dict(EnergyDemandTypeID)
        self._raw_energy_port = self._default_dict(EnergyDemandTypePortID)

        self._operational_energy_sea = self._default_dict(EnergyDemandTypeID)
        self._operational_energy_port = self._default_dict(EnergyDemandTypePortID)

        self._energy_sea = self._default_dict(EnergyDemandTypeID)
        self._energy_port = self._default_dict(EnergyDemandTypePortID)

        self._consumed_mass = self._default_dict(fuels)

        self._converter_mass = self._default_nested_dict(FuelTypeID, fuels)

        self._wtt = self._default_tuple_dict(fuels, emissions)
        self._ttw = self._default_tuple_dict(fuels, emissions)

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

    def add_fuel_consumer_profile(
        self,
        profile: _FuelConsumerProfile,
        multiplier: float | np.ndarray = 1.0,
        idx: int | slice = np.s_[:],
    ) -> None:
        """
        Add another fuel consumer profile's values into this one.

        Parameters
        ----------
        profile : _FuelConsumerProfile
            Consumer profile from another node.
        multiplier : float | np.ndarray
            Multiplier applied to each additive attribute when adding; a
            scalar, or elementwise weights matching the idx selection.
        idx : int | slice
            Time-step index or slice.
        """
        for energy_id in EnergyDemandTypeID:
            self._raw_energy_sea[energy_id][idx] += (
                multiplier * profile._raw_energy_sea[energy_id][idx]
            )

        for energy_id in EnergyDemandTypePortID:
            self._raw_energy_port[energy_id][idx] += (
                multiplier * profile._raw_energy_port[energy_id][idx]
            )

        for energy_id in EnergyDemandTypeID:
            self._operational_energy_sea[energy_id][idx] += (
                multiplier * profile._operational_energy_sea[energy_id][idx]
            )

        for energy_id in EnergyDemandTypePortID:
            self._operational_energy_port[energy_id][idx] += (
                multiplier * profile._operational_energy_port[energy_id][idx]
            )

        for energy_id in EnergyDemandTypeID:
            self._energy_sea[energy_id][idx] += (
                multiplier * profile._energy_sea[energy_id][idx]
            )

        for energy_id in EnergyDemandTypePortID:
            self._energy_port[energy_id][idx] += (
                multiplier * profile._energy_port[energy_id][idx]
            )

        for key in self._consumed_mass:
            self._consumed_mass[key][idx] += (
                profile._consumed_mass[key][idx] * multiplier
            )

        for key1, fuel_mass in self._converter_mass.items():
            for key2 in fuel_mass:
                self._converter_mass[key1][key2][idx] += (
                    profile._converter_mass[key1][key2][idx] * multiplier
                )

        for key in self._wtt:
            self._wtt[key][idx] += profile._wtt[key][idx] * multiplier

        for key in self._ttw:
            self._ttw[key][idx] += profile._ttw[key][idx] * multiplier

        for key in self._fuel_expenses:
            self._fuel_expenses[key][idx] += (
                profile._fuel_expenses[key][idx] * multiplier
            )

        for key in self._levy_expenses:
            self._levy_expenses[key][idx] += (
                profile._levy_expenses[key][idx] * multiplier
            )

        self._remedial_expenses[idx] += profile._remedial_expenses[idx] * multiplier
        self._flexibility_expenses[idx] += (
            profile._flexibility_expenses[idx] * multiplier
        )
        self._surplus_revenue[idx] += profile._surplus_revenue[idx] * multiplier

        self._shore_power_energy[idx] += profile._shore_power_energy[idx] * multiplier
        self._shore_power_expenses[idx] += (
            profile._shore_power_expenses[idx] * multiplier
        )

        for key in self._shore_power_emission:
            self._shore_power_emission[key][idx] += (
                profile._shore_power_emission[key][idx] * multiplier
            )

    def _to_intensity(
        self, emissions: dict[tuple[str, str], FloatArray]
    ) -> dict[tuple[str, str], FloatArray]:
        energy = self.get_total_consumed_energy()
        return {
            key: self._convert_to_intensity(emission, energy)
            for key, emission in emissions.items()
        }

    def _to_total_intensity(self, emission: FloatArray) -> FloatArray:
        return self._convert_to_intensity(emission, self.get_total_consumed_energy())

    def _saving(self, demand_type: EnergyDemandTypeID) -> FloatArray:
        if demand_type == EnergyDemandTypeID.PROPULSION:
            return 1.0 - divide_nonzero(
                self._energy_sea[demand_type],
                self._raw_energy_sea[demand_type],
                default=1.0,
            )
        else:
            return 1.0 - divide_nonzero(
                self._energy_sea[demand_type] + self._energy_port[demand_type],
                self._raw_energy_sea[demand_type] + self._raw_energy_port[demand_type],
                default=1.0,
            )

    def _shore_power_equivalent(self) -> FloatArray:
        return self._sum_values(
            multiply_dicts(self._shore_power_emission, self._global_warming_potential)
        )

    def _converter_fuel_type_share(self, fuel_type: FuelTypeID) -> FloatArray:
        # TODO: may not work when using multiple main fuel types

        energy = self._fuel_mass_to_energy(self._converter_mass[fuel_type])
        main_fuel = np.sum(
            [
                e
                for fuel_name, e in energy.items()
                if self._fuel_type[fuel_name] == fuel_type
            ],
            axis=0,
        )
        total_fuel = np.sum(list(energy.values()), axis=0)

        return divide_nonzero(main_fuel, total_fuel)

    def add_consumed_mass(
        self, fuel_name: str, mass: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._consumed_mass[fuel_name][idx] += mass

    def add_converter_mass(
        self,
        fuel_type: FuelTypeID,
        fuel_name: str,
        mass: float,
        idx: int | slice = np.s_[:],
    ) -> None:
        self._converter_mass[fuel_type][fuel_name][idx] += mass

    def add_wtt(
        self,
        fuel_name: str,
        emission_name: str,
        wtt: float,
        idx: int | slice = np.s_[:],
    ) -> None:
        self._wtt[(fuel_name, emission_name)][idx] += wtt

    def add_ttw(
        self,
        fuel_name: str,
        emission_name: str,
        ttw: float,
        idx: int | slice = np.s_[:],
    ) -> None:
        self._ttw[(fuel_name, emission_name)][idx] += ttw

    def add_fuel_expenses(
        self, fuel_name: str, expenses: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._fuel_expenses[fuel_name][idx] += expenses

    def add_levy_expenses(
        self, fuel_name: str, expenses: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._levy_expenses[fuel_name][idx] += expenses

    def add_remedial_expenses(
        self, expenses: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._remedial_expenses[idx] += expenses

    def add_remedial_units(
        self, policy_name: str, units: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._remedial_units[policy_name][idx] += units

    def get_remedial_units(self) -> dict[str, FloatArray]:
        return dict(self._remedial_units)

    def add_levy_units(
        self, policy_name: str, units: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._levy_units[policy_name][idx] += units

    def get_levy_units(self) -> dict[str, FloatArray]:
        return dict(self._levy_units)

    def add_flexibility_expenses(
        self, expenses: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._flexibility_expenses[idx] += expenses

    def add_surplus_revenue(self, revenue: float, idx: int | slice = np.s_[:]) -> None:
        self._surplus_revenue[idx] += revenue

    def add_shore_power_energy(
        self, energy: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._shore_power_energy[idx] += energy

    def add_shore_power_expenses(
        self, expenses: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._shore_power_expenses[idx] += expenses

    def add_shore_power_emission(
        self, emission_name: str, emission: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._shore_power_emission[emission_name][idx] += emission

    def get_raw_energy_sea(self) -> dict[EnergyDemandTypeID, FloatArray]:
        return dict(self._raw_energy_sea)

    def get_raw_energy_port(self) -> dict[EnergyDemandTypeID, FloatArray]:
        return dict(self._raw_energy_port)

    def get_raw_energy(self) -> FloatArray:
        return self._sum_values(self._raw_energy_sea) + self._sum_values(
            self._raw_energy_port
        )

    def get_operational_energy_sea(self) -> dict[EnergyDemandTypeID, FloatArray]:
        return dict(self._operational_energy_sea)

    def get_operational_energy_port(self) -> dict[EnergyDemandTypeID, FloatArray]:
        return dict(self._operational_energy_port)

    def get_operational_energy(self) -> FloatArray:
        return self._sum_values(self._operational_energy_sea) + self._sum_values(
            self._operational_energy_port
        )

    def get_energy_sea(self) -> dict[EnergyDemandTypeID, FloatArray]:
        return dict(self._energy_sea)

    def get_energy_port(self) -> dict[EnergyDemandTypeID, FloatArray]:
        return dict(self._energy_port)

    def get_total_energy_port(self) -> FloatArray:
        return self._sum_values(self._energy_port)

    def get_energy(self) -> FloatArray:
        return self._sum_values(self._energy_sea) + self._sum_values(self._energy_port)

    def get_saving(self) -> dict[EnergyDemandTypeID, FloatArray]:
        return {
            demand_type: self._saving(demand_type) for demand_type in self._energy_sea
        }

    def get_speed_energy_intensity_saving(self) -> FloatArray:
        return 1.0 - divide_nonzero(
            self.get_raw_energy(), self.get_baseline_energy(), default=1.0
        )

    def get_operational_energy_intensity_saving(self) -> FloatArray:
        return 1.0 - divide_nonzero(
            self.get_operational_energy(), self.get_baseline_energy(), default=1.0
        )

    def get_technology_energy_intensity_saving(self) -> FloatArray:
        # cargo-miles cancel between energy and operational energy
        return 1.0 - divide_nonzero(
            self.get_energy(), self.get_operational_energy(), default=1.0
        )

    def get_energy_intensity_saving(self) -> FloatArray:
        return 1.0 - divide_nonzero(
            self.get_energy(), self.get_baseline_energy(), default=1.0
        )

    def get_consumed_energy(self) -> dict[str, FloatArray]:
        return self._fuel_mass_to_energy(self._consumed_mass)

    def get_fuel_type_energy(self) -> dict[FuelTypeID, FloatArray]:
        return self._fuel_type_mass_to_energy(self._consumed_mass)

    def get_total_consumed_energy(self) -> FloatArray:
        return self._sum_values(self.get_consumed_energy()) + self._shore_power_energy

    def get_converter_energy(self) -> dict[FuelTypeID, dict[str, FloatArray]]:
        return {
            fuel_type: self._fuel_mass_to_energy(mass)
            for fuel_type, mass in self._converter_mass.items()
        }

    def get_pilot_fuel_share(self) -> dict[FuelTypeID, FloatArray]:
        return {
            fuel_type: 1.0 - self._converter_fuel_type_share(fuel_type)
            for fuel_type in self._converter_mass
        }

    def get_shore_power_energy(self) -> FloatArray:
        return self._shore_power_energy

    def get_shore_power_expenses(self) -> FloatArray:
        return self._shore_power_expenses

    def get_shore_power_emission(self) -> dict[str, FloatArray]:
        return dict(self._shore_power_emission)

    def get_fuel_expenses(self) -> dict[str, FloatArray]:
        return dict(self._fuel_expenses)

    def get_levy_expenses(self) -> dict[str, FloatArray]:
        return dict(self._levy_expenses)

    def get_fuel_related_expenses(self) -> dict[str, FloatArray]:
        return add_dicts(self._fuel_expenses, self._levy_expenses)

    def get_remedial_expenses(self) -> FloatArray:
        return self._remedial_expenses

    def get_flexibility_expenses(self) -> FloatArray:
        return self._flexibility_expenses

    def get_surplus_revenue(self) -> FloatArray:
        return self._surplus_revenue

    def get_regulation_expenses(self) -> FloatArray:
        return (
            self._remedial_expenses + self._flexibility_expenses - self._surplus_revenue
        )

    def get_total_fuel_expenses(self) -> FloatArray:
        return self._sum_values(self._fuel_expenses) + self._shore_power_expenses

    def get_total_levy_expenses(self) -> FloatArray:
        return self._sum_values(self._levy_expenses)

    def get_total_fuel_related_expenses(self) -> FloatArray:
        return self.get_total_fuel_expenses() + self.get_total_levy_expenses()

    def get_cumulative_fuel_expenses(self) -> dict[str, FloatArray]:
        return self._to_cumulative_dict(self._fuel_expenses)

    def get_cumulative_levy_expenses(self) -> dict[str, FloatArray]:
        return self._to_cumulative_dict(self._levy_expenses)

    def get_cumulative_fuel_related_expenses(self) -> dict[str, FloatArray]:
        return self._to_cumulative_dict(
            add_dicts(self._fuel_expenses, self._levy_expenses)
        )

    def get_cumulative_remedial_expenses(self) -> FloatArray:
        return self._to_cumulative(self.get_remedial_expenses())

    def get_cumulative_flexibility_expenses(self) -> FloatArray:
        return self._to_cumulative(self.get_flexibility_expenses())

    def get_cumulative_surplus_revenue(self) -> FloatArray:
        return self._to_cumulative(self.get_surplus_revenue())

    def get_cumulative_regulation_expenses(self) -> FloatArray:
        return self._to_cumulative(self.get_regulation_expenses())

    def get_cumulative_total_fuel_expenses(self) -> FloatArray:
        return self._to_cumulative(self.get_total_fuel_expenses())

    def get_cumulative_total_levy_expenses(self) -> FloatArray:
        return self._to_cumulative(self.get_total_levy_expenses())

    def get_cumulative_total_fuel_related_expenses(self) -> FloatArray:
        return self._to_cumulative(self.get_total_fuel_related_expenses())

    def get_equivalent_wtt(self) -> dict[tuple[str, str], FloatArray]:
        return self._equivalent(self._wtt)

    def get_total_equivalent_wtt(self) -> FloatArray:
        return self._sum_values(self.get_equivalent_wtt())

    def get_cumulative_equivalent_wtt(self) -> dict[tuple[str, str], FloatArray]:
        return self._to_cumulative_dict(self.get_equivalent_wtt())

    def get_cumulative_total_equivalent_wtt(self) -> FloatArray:
        return self._to_cumulative(self.get_total_equivalent_wtt())

    def get_intensity_equivalent_wtt(self) -> dict[tuple[str, str], FloatArray]:
        return self._to_intensity(self.get_equivalent_wtt())

    def get_intensity_total_equivalent_wtt(self) -> FloatArray:
        return self._to_total_intensity(self.get_total_equivalent_wtt())

    def get_equivalent_ttw(self) -> dict[tuple[str, str], FloatArray]:
        return self._equivalent(self._ttw)

    def get_total_equivalent_ttw(self) -> FloatArray:
        return self._sum_values(self.get_equivalent_ttw())

    def get_cumulative_equivalent_ttw(self) -> dict[tuple[str, str], FloatArray]:
        return self._to_cumulative_dict(self.get_equivalent_ttw())

    def get_cumulative_total_equivalent_ttw(self) -> FloatArray:
        return self._to_cumulative(self.get_total_equivalent_ttw())

    def get_intensity_equivalent_ttw(self) -> dict[tuple[str, str], FloatArray]:
        return self._to_intensity(self.get_equivalent_ttw())

    def get_intensity_total_equivalent_ttw(self) -> FloatArray:
        return self._to_total_intensity(self.get_total_equivalent_ttw())

    def get_equivalent_wtw(self) -> dict[tuple[str, str], FloatArray]:
        return self._equivalent(add_dicts(self._wtt, self._ttw))

    def get_total_equivalent_wtw(self) -> FloatArray:
        # shore power emissions are a WTW lump with no (fuel, emission) attribution,
        # so they enter the total but not the per-key getters
        return (
            self._sum_values(self.get_equivalent_wtw()) + self._shore_power_equivalent()
        )

    def get_cumulative_equivalent_wtw(self) -> dict[tuple[str, str], FloatArray]:
        return self._to_cumulative_dict(self.get_equivalent_wtw())

    def get_cumulative_total_equivalent_wtw(self) -> FloatArray:
        return self._to_cumulative(self.get_total_equivalent_wtw())

    def get_intensity_equivalent_wtw(self) -> dict[tuple[str, str], FloatArray]:
        return self._to_intensity(self.get_equivalent_wtw())

    def get_intensity_total_equivalent_wtw(self) -> FloatArray:
        return self._to_total_intensity(self.get_total_equivalent_wtw())
