# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import FuelTypeID
from navigate.core.misc import EMPTY_FLOAT
from navigate.core.profiles._fuel_consumer_profile import _FuelConsumerProfile
from navigate.util import divide_nonzero, extract_from_dict, extract_from_tuple_dict

if TYPE_CHECKING:
    from navigate.fuel import Fuel


class _VesselAggregateProfile(_FuelConsumerProfile):
    def __init__(self):
        super().__init__()

        # fleet level energy
        self._average_raw_energy: np.ndarray = EMPTY_FLOAT             # raw energy demand without trade-growth
        self._average_operational_energy: np.ndarray = EMPTY_FLOAT     # without trade-growth
        self._average_energy: np.ndarray = EMPTY_FLOAT                 # energy demand without trade-growth

        # power
        self._installed_power: dict[FuelTypeID, np.ndarray] = {}
        self._newbuild_power: dict[FuelTypeID, np.ndarray] = {}
        self._scrapped_power: dict[FuelTypeID, np.ndarray] = {}
        self._fuel_converted_power: dict[tuple[FuelTypeID, FuelTypeID], np.ndarray] = {}

        # expenses
        self._vessel_expenses: np.ndarray = EMPTY_FLOAT
        self._technology_newbuild_expenses: np.ndarray = EMPTY_FLOAT
        self._technology_retrofit_expenses: np.ndarray = EMPTY_FLOAT
        self._fuel_conversion_expenses: np.ndarray = EMPTY_FLOAT
        self._vessel_tied_capital: np.ndarray = EMPTY_FLOAT

        # shore power (aggregated from vessel profiles)
        self._shore_power_energy: np.ndarray = EMPTY_FLOAT    # shore power energy, GJ/year

        # weighted average age (numerator and denominator for correct aggregation)
        self._weighted_age_numerator: dict[FuelTypeID, np.ndarray] = {}   # sum(age * power)
        self._weighted_age_denominator: dict[FuelTypeID, np.ndarray] = {}  # sum(power)

        # fuel
        self._fuel_type_demand: dict[FuelTypeID, np.ndarray] = {}
        self._demand_expectation: dict[str, list[np.ndarray]] = {}  # results of expected bunkering per fuel

    def _initialize_vessel_aggregate(self, fuels: dict[str, Fuel]) -> None:

        self._average_raw_energy = self._default_array()
        self._average_operational_energy = self._default_array()
        self._average_energy = self._default_array()

        self._installed_power = self._default_dict(FuelTypeID)
        self._newbuild_power = self._default_dict(FuelTypeID)
        self._scrapped_power = self._default_dict(FuelTypeID)
        self._fuel_converted_power = self._default_tuple_dict(FuelTypeID, FuelTypeID)

        self._vessel_expenses = self._default_array()
        self._technology_newbuild_expenses = self._default_array()
        self._technology_retrofit_expenses = self._default_array()
        self._fuel_conversion_expenses = self._default_array()
        self._vessel_tied_capital = self._default_array()

        self._shore_power_energy = self._default_array()

        self._weighted_age_numerator = self._default_dict(FuelTypeID)
        self._weighted_age_denominator = self._default_dict(FuelTypeID)

        self._fuel_type_demand = self._default_dict(FuelTypeID)
        self._demand_expectation = {f: self._default_list(self.get_length(), default=0.) for f in fuels}

    def add_vessel_aggregate_profile(self, profile: _VesselAggregateProfile, idx: int | slice = np.s_[:]) -> None:
        """

        Parameters
        ----------
        profile : _VesselAggregateProfile | VesselProfile
            Aggregate profile from another node.
        idx : int
            Current time-step index.
        """

        self._average_raw_energy[idx] += profile._average_raw_energy[idx]
        self._average_operational_energy[idx] += profile._average_operational_energy[idx]
        self._average_energy[idx] += profile._average_energy[idx]

        for key in self._installed_power:
            self._installed_power[key][idx] += profile._installed_power[key][idx]

        for key in self._newbuild_power:
            self._newbuild_power[key][idx] += profile._newbuild_power[key][idx]

        for key in self._scrapped_power:
            self._scrapped_power[key][idx] += profile._scrapped_power[key][idx]

        for key in self._fuel_converted_power:
            self._fuel_converted_power[key][idx] += profile._fuel_converted_power[key][idx]

        self._vessel_expenses[idx] += profile._vessel_expenses[idx]
        self._technology_newbuild_expenses[idx] += profile._technology_newbuild_expenses[idx]
        self._technology_retrofit_expenses[idx] += profile._technology_retrofit_expenses[idx]
        self._fuel_conversion_expenses[idx] += profile._fuel_conversion_expenses[idx]
        self._vessel_tied_capital[idx] += profile._vessel_tied_capital[idx]

        self._shore_power_energy[idx] += profile._shore_power_energy[idx]

        for key in self._weighted_age_numerator:
            self._weighted_age_numerator[key][idx] += profile._weighted_age_numerator[key][idx]

        for key in self._weighted_age_denominator:
            self._weighted_age_denominator[key][idx] += profile._weighted_age_denominator[key][idx]

        for key in self._fuel_type_demand:
            self._fuel_type_demand[key][idx] += profile._fuel_type_demand[key][idx]

        for key in self._demand_expectation:
            for i, value in enumerate(profile._demand_expectation[key]):
                self._demand_expectation[key][i] += value

    def add_installed_power(self, fuel_type: FuelTypeID, power: float, idx: int | slice = np.s_[:]) -> None:
        self._installed_power[fuel_type][idx] += power

    def add_newbuild_power(self, fuel_type: FuelTypeID, power: float, idx: int | slice = np.s_[:]) -> None:
        self._newbuild_power[fuel_type][idx] += power

    def add_scrapped_power(self, fuel_type: FuelTypeID, power: float, idx: int | slice = np.s_[:]) -> None:
        self._scrapped_power[fuel_type][idx] += power

    def add_fuel_converted_power(self, fuel_type_to: FuelTypeID, fuel_type_from: FuelTypeID,
                                 power: float, idx: int | slice = np.s_[:]) -> None:
        self._fuel_converted_power[(fuel_type_to, fuel_type_from)][idx] += power

    def add_vessel_expenses(self, expenses: float, idx: int | slice = np.s_[:]) -> None:
        self._vessel_expenses[idx] += expenses

    def add_technology_newbuild_expenses(self, expenses: float, idx: int | slice = np.s_[:]) -> None:
        self._technology_newbuild_expenses[idx] += expenses

    def add_technology_retrofit_expenses(self, expenses: float, idx: int | slice = np.s_[:]) -> None:
        self._technology_retrofit_expenses[idx] += expenses

    def add_vessel_tied_capital(self, tied_capital: float, idx: int) -> None:
        self._vessel_tied_capital[idx] += tied_capital

    def add_fuel_conversion_expenses(self, expenses: float, idx: int | slice = np.s_[:]) -> None:
        self._fuel_conversion_expenses[idx] += expenses

    def add_weighted_age(self, fuel_type: FuelTypeID, numerator: float, denominator: float,
                         idx: int | slice = np.s_[:]) -> None:
        self._weighted_age_numerator[fuel_type][idx] += numerator
        self._weighted_age_denominator[fuel_type][idx] += denominator

    def add_fuel_type_demand(self, fuel_type: FuelTypeID, demand: float, idx: int | slice = np.s_[:]) -> None:
        self._fuel_type_demand[fuel_type][idx] += demand

    def set_average_raw_energy(self, idx: int, demand: float) -> None:
        self._average_raw_energy[idx] = demand

    def set_average_operational_energy(self, idx: int, demand: float) -> None:
        self._average_operational_energy[idx] = demand

    def set_average_energy(self, idx: int, demand: float) -> None:
        self._average_energy[idx] = demand

    def set_demand_expectation(self, fuel_name: str, idx1: int, idx2: int, demand_expectation: np.ndarray) -> None:
        self._demand_expectation[fuel_name][idx1][idx2] = demand_expectation

    def get_average_raw_energy(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._average_raw_energy[idx]

    def get_average_operational_energy(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._average_operational_energy[idx]

    def get_average_energy(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._average_energy[idx]

    def get_speed_energy_saving(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return 1. - divide_nonzero(self._average_raw_energy[idx], self._average_raw_energy[0], default=1.)

    def get_operational_energy_saving(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return 1. - divide_nonzero(self._average_operational_energy[idx], self._average_raw_energy[0], default=1.)

    def get_technology_energy_saving(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return 1. - divide_nonzero(self._average_energy[idx], self._average_operational_energy[idx], default=1.)

    def get_energy_saving(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return 1. - divide_nonzero(self._average_energy[idx], self._average_raw_energy[0], default=1.)

    def get_shore_power_energy(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._shore_power_energy[idx]

    def get_weighted_average_age(
            self, fuel_type: FuelTypeID | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[FuelTypeID, np.ndarray]:
        if fuel_type is not None:
            return divide_nonzero(self._weighted_age_numerator[fuel_type][idx],
                                  self._weighted_age_denominator[fuel_type][idx])
        return {ft: divide_nonzero(self._weighted_age_numerator[ft][idx],
                                   self._weighted_age_denominator[ft][idx])
                for ft in self._weighted_age_numerator}

    def get_installed_power(
            self, fuel_type: FuelTypeID | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[FuelTypeID, np.ndarray]:
        return extract_from_dict(self._installed_power, fuel_type, idx)

    def get_newbuild_power(
            self, fuel_type: FuelTypeID | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[FuelTypeID, np.ndarray]:
        return extract_from_dict(self._newbuild_power, fuel_type, idx)

    def get_scrapped_power(
            self, fuel_type: FuelTypeID | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[FuelTypeID, np.ndarray]:
        return extract_from_dict(self._scrapped_power, fuel_type, idx)

    def get_fuel_converted_power(
            self, fuel_type_from: FuelTypeID | None = None,
            fuel_type_to: FuelTypeID | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[tuple[FuelTypeID, FuelTypeID], np.ndarray]:
        return extract_from_tuple_dict(self._fuel_converted_power, fuel_type_from, fuel_type_to, idx)

    def get_cumulative_newbuild_power(self, fuel_type: FuelTypeID | None = None) -> np.ndarray | dict[FuelTypeID, np.ndarray]:
        return self._to_cumulative_any(extract_from_dict(self._newbuild_power, fuel_type))

    def get_cumulative_scrapped_power(self, fuel_type: FuelTypeID | None = None) -> np.ndarray | dict[FuelTypeID, np.ndarray]:
        return self._to_cumulative_any(extract_from_dict(self._scrapped_power, fuel_type))

    def get_cumulative_fuel_converted_power(self) -> dict[tuple[FuelTypeID, FuelTypeID], np.ndarray]:
        return self._to_cumulative_dict(self._fuel_converted_power)

    def get_vessel_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._vessel_expenses[idx]

    def get_technology_newbuild_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._technology_newbuild_expenses[idx]

    def get_technology_retrofit_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._technology_retrofit_expenses[idx]

    def get_fuel_conversion_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._fuel_conversion_expenses[idx]

    def get_vessel_related_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return (self._vessel_expenses[idx]
                + self._technology_newbuild_expenses[idx]
                + self._technology_retrofit_expenses[idx]
                + self._fuel_conversion_expenses[idx])

    def get_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return (self.get_total_fuel_related_expenses(idx)
                + self.get_regulation_expenses(idx)
                + self.get_vessel_related_expenses(idx))

    def get_cumulative_vessel_expenses(self) -> np.ndarray:
        return self._to_cumulative(self._vessel_expenses)

    def get_cumulative_technology_newbuild_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._to_cumulative_dict(self._technology_newbuild_expenses[idx])

    def get_cumulative_technology_retrofit_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._to_cumulative_dict(self._technology_retrofit_expenses[idx])

    def get_cumulative_fuel_conversion_expenses(self) -> np.ndarray:
        return self._to_cumulative(self._fuel_conversion_expenses)

    def get_cumulative_vessel_related_expenses(self) -> np.ndarray:
        return self._to_cumulative(self.get_vessel_related_expenses())

    def get_cumulative_expenses(self) -> np.ndarray:
        return self._to_cumulative(self.get_expenses())

    def get_vessel_tied_capital(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._vessel_tied_capital[idx]

    def get_fuel_type_demand(
            self, fuel_type: FuelTypeID | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[FuelTypeID, np.ndarray]:
        return extract_from_dict(self._fuel_type_demand, fuel_type, idx)

    def get_demand_expectation(self) -> dict[str, list[np.ndarray]]:
        return self._demand_expectation
