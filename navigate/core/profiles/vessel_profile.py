# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import EnergyDemandTypeID, EnergyDemandTypePortID
from navigate.core.misc import EMPTY_BOOL, EMPTY_FLOAT, EMPTY_NAN
from navigate.core.profiles._fuel_consumer_profile import _FuelConsumerProfile
from navigate.util import divide_nonzero, extract_from_dict

if TYPE_CHECKING:
    from navigate.fuel import Emission, Fuel


class VesselProfile(_FuelConsumerProfile):
    def __init__(self):
        super().__init__()

        self._lifetime: np.ndarray = EMPTY_FLOAT   # year, lifetime of the vessel
        self._lead_time: np.ndarray = EMPTY_FLOAT  # year, lead time of the vessel

        # speeds
        self._reference_speed: np.ndarray = EMPTY_NAN       # reference speed, knots
        self._minimum_speed: np.ndarray = EMPTY_NAN         # minimum possible speed, knots
        self._maximum_speed: np.ndarray = EMPTY_NAN         # maximum possible speed, knots
        self._actual_speed: np.ndarray = EMPTY_NAN          # average actual speed, knots
        self._optimal_speed: np.ndarray = EMPTY_NAN         # average optimal speed, knots
        self._lowest_speed: np.ndarray = EMPTY_NAN          # lowest actual speed, knots
        self._highest_speed: np.ndarray = EMPTY_NAN         # highest actual speed, knots

        # investment signals (energy-weighted average of the smoothed energy-conservation duals, USD/GJ)
        self._investment_signal_technology: np.ndarray = EMPTY_NAN  # technology-horizon belief
        self._investment_signal_speed: np.ndarray = EMPTY_NAN       # speed-horizon belief

        # shore power
        self._shore_power_energy: np.ndarray = EMPTY_FLOAT    # shore power energy, GJ/year
        self._shore_power_expenses: np.ndarray = EMPTY_FLOAT  # shore power cost, USD/year
        self._shore_power_emission: dict[str, np.ndarray] = {}  # shore power emission, ton/year

        # technology costs
        self._technology_cost: np.ndarray = EMPTY_FLOAT       # USD/year, average yearly purchase cost

        # freight rates
        self._asset_charter_rate: np.ndarray = EMPTY_NAN
        self._cargo_charter_rate: np.ndarray = EMPTY_NAN
        self._investment_freight_rate: np.ndarray = EMPTY_NAN        # USD/cargo-mile
        self._instantaneous_freight_rate: np.ndarray = EMPTY_NAN     # USD/cargo-mile

        # various boolean properties
        self._in_fleet: np.ndarray = EMPTY_BOOL               # whether multiplier > 0
        self._cost_is_calculated: np.ndarray = EMPTY_BOOL     # whether cost is calculated

    def initialize(self, timeline: np.ndarray, emissions: dict[str, Emission],
                   fuels: dict[str, Fuel], emissions_lifetime: float,
                   regulation_names: list[str] = (), levy_names: list[str] = ()) -> None:
        """

        Parameters
        ----------
        timeline : np.ndarray
            Simulation timeline in years.
        emissions : dict[Emission]
            All emissions in the simulation.
        fuels : dict[Fuel]
            All fuels in the simulation
        emissions_lifetime : float
            GWP lifetime.
        regulation_names : list[str]
            Names of all regulations in the simulation.
        levy_names : list[str]
            Names of all levies in the simulation.
        """

        self._initialize_base(timeline)
        self._initialize_fuel_base(fuels)
        self._initialize_fuel_consumer(fuels, emissions, emissions_lifetime, regulation_names, levy_names)

        self._lifetime = self._default_array()
        self._lead_time = self._default_array()

        # speeds
        self._reference_speed = self._default_array(default=np.nan)
        self._minimum_speed = self._default_array(default=np.nan)
        self._maximum_speed = self._default_array(default=np.nan)
        self._actual_speed = self._default_array(default=np.nan)
        self._optimal_speed = self._default_array(default=np.nan)
        self._lowest_speed = self._default_array(default=np.nan)
        self._highest_speed = self._default_array(default=np.nan)

        # investment signals
        self._investment_signal_technology = self._default_array(default=np.nan)
        self._investment_signal_speed = self._default_array(default=np.nan)

        # shore power
        self._shore_power_energy = self._default_array()
        self._shore_power_expenses = self._default_array()
        self._shore_power_emission = self._default_dict(emissions)

        self._technology_cost = self._default_array()

        self._in_fleet = self._default_array(default=False)
        self._cost_is_calculated = self._default_array(default=False)

        # investment metrics
        self._asset_charter_rate = self._default_array(np.nan)
        self._cargo_charter_rate = self._default_array(np.nan)
        self._investment_freight_rate = self._default_array(np.nan)
        self._instantaneous_freight_rate = self._default_array(np.nan)

    def set_lifetime(self, idx: int, lifetime: float) -> None:
        self._lifetime[idx] = lifetime

    def set_lead_time(self, idx: int, lead_time: float) -> None:
        self._lead_time[idx] = lead_time

    def set_reference_speed(self, idx: int, reference_speed: float) -> None:
        self._reference_speed[idx] = reference_speed

    def set_minimum_speed(self, idx: int, minimum_speed: float) -> None:
        self._minimum_speed[idx] = minimum_speed

    def set_maximum_speed(self, idx: int, maximum_speed: float) -> None:
        self._maximum_speed[idx] = maximum_speed

    def set_actual_speed(self, idx: int, actual_speed: float) -> None:
        self._actual_speed[idx] = actual_speed

    def set_optimal_speed(self, idx: int, optimal_speed: float) -> None:
        self._optimal_speed[idx] = optimal_speed

    def set_lowest_speed(self, idx: int, lowest_speed: float) -> None:
        self._lowest_speed[idx] = lowest_speed

    def set_highest_speed(self, idx: int, highest_speed: float) -> None:
        self._highest_speed[idx] = highest_speed

    def set_investment_signal_technology(self, idx: int, investment_signal: float) -> None:
        self._investment_signal_technology[idx] = investment_signal

    def set_investment_signal_speed(self, idx: int, investment_signal: float) -> None:
        self._investment_signal_speed[idx] = investment_signal

    def set_raw_energy_sea(self, idx: int, energy: dict[EnergyDemandTypeID, np.ndarray]) -> None:
        for energy_id in EnergyDemandTypeID:
            self._raw_energy_sea[energy_id][idx] = energy[energy_id]

    def set_raw_energy_port(self, idx: int, energy: dict[EnergyDemandTypeID, np.ndarray]) -> None:
        for energy_id in EnergyDemandTypePortID:
            self._raw_energy_port[energy_id][idx] = energy[energy_id]

    def set_operational_energy_sea(self, idx: int, energy: dict[EnergyDemandTypeID, np.ndarray]) -> None:
        for energy_id in EnergyDemandTypeID:
            self._operational_energy_sea[energy_id][idx] = energy[energy_id]

    def set_operational_energy_port(self, idx: int, energy: dict[EnergyDemandTypeID, np.ndarray]) -> None:
        for energy_id in EnergyDemandTypePortID:
            self._operational_energy_port[energy_id][idx] = energy[energy_id]

    def set_energy_sea(self, idx: int, energy: dict[EnergyDemandTypeID, np.ndarray]) -> None:
        for energy_id in EnergyDemandTypeID:
            self._energy_sea[energy_id][idx] = energy[energy_id]

    def set_energy_port(self, idx: int, energy: dict[EnergyDemandTypeID, np.ndarray]) -> None:
        for energy_id in EnergyDemandTypePortID:
            self._energy_port[energy_id][idx] = energy[energy_id]

    def add_shore_power_energy(self, idx: int, energy: float) -> None:
        self._shore_power_energy[idx] += energy

    def add_shore_power_expenses(self, idx: int, expenses: float) -> None:
        self._shore_power_expenses[idx] += expenses

    def add_shore_power_emission(self, emission_name: str, idx: int, emission: float) -> None:
        self._shore_power_emission[emission_name][idx] += emission

    def set_technology_cost(self, idx: int, cost: float) -> None:
        self._technology_cost[idx] = cost

    def set_in_fleet(self, idx: int, in_fleet: bool) -> None:
        self._in_fleet[idx] = in_fleet

    def set_cost_is_calculated(self, idx: int, cost_is_calculated: bool) -> None:
        self._cost_is_calculated[idx] = cost_is_calculated

    def set_asset_charter_rate(self, idx: int, asset_charter_rate: float) -> None:
        self._asset_charter_rate[idx] = asset_charter_rate

    def set_cargo_charter_rate(self, idx: int, cargo_charter_rate: float) -> None:
        self._cargo_charter_rate[idx] = cargo_charter_rate

    def set_investment_freight_rate(self, idx: int, investment_freight_rate: float) -> None:
        self._investment_freight_rate[idx] = investment_freight_rate

    def set_instantaneous_freight_rate(self, idx: int, instantaneous_freight_rate: float) -> None:
        self._instantaneous_freight_rate[idx] = instantaneous_freight_rate

    def get_lifetime(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._lifetime[idx]

    def get_lead_time(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._lead_time[idx]

    def get_reference_speed(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._reference_speed[idx]

    def get_minimum_speed(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._minimum_speed[idx]

    def get_maximum_speed(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._maximum_speed[idx]

    def get_actual_speed(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._actual_speed[idx]

    def get_optimal_speed(self, idx: int | slice) -> np.ndarray:
        return self._optimal_speed[idx]

    def get_lowest_speed(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._lowest_speed[idx]

    def get_highest_speed(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._highest_speed[idx]

    def get_investment_signal_technology(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._investment_signal_technology[idx]

    def get_investment_signal_speed(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._investment_signal_speed[idx]

    def get_speed_energy_saving(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return 1. - divide_nonzero(self.get_raw_energy(idx=idx), self.get_raw_energy(idx=0), default=1.)

    def get_operational_energy_saving(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return 1. - divide_nonzero(self.get_operational_energy(idx=idx), self.get_raw_energy(idx=0), default=1.)

    def get_technology_energy_saving(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return 1. - divide_nonzero(self.get_energy(idx=idx), self.get_operational_energy(idx=idx), default=1.)

    def get_energy_saving(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return 1. - divide_nonzero(self.get_energy(idx=idx), self.get_raw_energy(idx=0), default=1.)

    def get_shore_power_energy(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._shore_power_energy[idx]

    def get_shore_power_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._shore_power_expenses[idx]

    def get_shore_power_emission(
            self, emission_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._shore_power_emission, emission_name, idx)

    def is_active(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._in_fleet[idx]

    def is_in_fleet(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._in_fleet[idx]

    def cost_is_calculated(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._cost_is_calculated[idx]

    def get_asset_charter_rate(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._asset_charter_rate[idx]

    def get_cargo_charter_rate(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._cargo_charter_rate[idx]

    def get_investment_freight_rate(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._investment_freight_rate[idx]

    def get_instantaneous_freight_rate(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._instantaneous_freight_rate[idx]
