# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Vessel node, read by the fleet domain and the bunkering LP."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import EnergyDemandTypeID, EnergyDemandTypePortID
from navigate.core.expectations._expectation import _Expectation
from navigate.core.initial_values import EMPTY_FLOAT
from navigate.util import divide_nonzero, slice_dict_list, slice_list

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import SupportsIndex

    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.route import Route
    from navigate.util.types_ import FloatArray, FloatLike, Index


class VesselExpectation(_Expectation):
    """Voyage, energy, bunkering and investment paths of a single vessel."""

    def __init__(self) -> None:
        super().__init__()

        # voyage
        self._voyages: FloatArray = EMPTY_FLOAT

        # cargo
        self._cargo_miles: FloatArray = EMPTY_FLOAT
        self._cargo_miles_leg: list[FloatArray] = []
        self._cargo_miles_leg_nominal: list[FloatArray] = []

        # speeds
        self._speed_mean: float = np.nan
        self._speed_anchor_reference: float = np.nan
        self._speed_anchor_optimal: float = np.nan
        self._speeds: list[FloatArray] = []

        # durations
        self._time_sea: list[FloatArray] = []
        self._time_port: list[FloatArray] = []

        # energies
        self._raw_energy_sea: dict[EnergyDemandTypeID, list[FloatArray]] = {}
        self._raw_energy_port: dict[EnergyDemandTypeID, list[FloatArray]] = {}

        self._operational_energy_sea: dict[EnergyDemandTypeID, list[FloatArray]] = {}
        self._operational_energy_port: dict[EnergyDemandTypeID, list[FloatArray]] = {}

        self._operational_saving_fraction_sea: dict[EnergyDemandTypeID, float] = {}
        self._operational_saving_fraction_port: dict[EnergyDemandTypeID, float] = {}

        self._energy_sea: dict[EnergyDemandTypeID, list[FloatArray]] = {}
        self._energy_port: dict[EnergyDemandTypeID, list[FloatArray]] = {}

        self._regional_operational_energy_sea: dict[
            EnergyDemandTypeID, list[FloatArray]
        ] = {}
        self._regional_energy_sea: dict[EnergyDemandTypeID, list[FloatArray]] = {}

        # constraint attributes
        self._energy_conservation_pi_sea: dict[
            EnergyDemandTypeID, list[FloatArray]
        ] = {}
        self._energy_conservation_pi_port: dict[
            EnergyDemandTypeID, list[FloatArray]
        ] = {}
        self._energy_conservation_rhs_sea: dict[
            EnergyDemandTypeID, list[FloatArray]
        ] = {}
        self._energy_conservation_rhs_port: dict[
            EnergyDemandTypeID, list[FloatArray]
        ] = {}
        self._energy_conservation_sarhslow_sea: dict[
            EnergyDemandTypeID, list[FloatArray]
        ] = {}
        self._energy_conservation_sarhslow_port: dict[
            EnergyDemandTypeID, list[FloatArray]
        ] = {}
        self._energy_conservation_sarhsup_sea: dict[
            EnergyDemandTypeID, list[FloatArray]
        ] = {}
        self._energy_conservation_sarhsup_port: dict[
            EnergyDemandTypeID, list[FloatArray]
        ] = {}

        # per-leg, per-energy-type smoothed shadow-price beliefs (same shape as the raw
        # pi dicts above). Tech-horizon belief is amortised over the decision horizon
        # used by newbuild/retrofit NPVs; speed-horizon belief is faster, matched to the
        # timescale of operational speed management.
        self._belief_pi_sea_technology: dict[EnergyDemandTypeID, list[FloatArray]] = {}
        self._belief_pi_port_technology: dict[EnergyDemandTypeID, list[FloatArray]] = {}
        self._belief_pi_sea_speed: dict[EnergyDemandTypeID, list[FloatArray]] = {}
        self._belief_pi_port_speed: dict[EnergyDemandTypeID, list[FloatArray]] = {}

        # bunkering/spend
        self._bunker_mass_expected: dict[tuple[str, str], float] = {}
        self._bunker_mass_existing: dict[tuple[str, str], float] = {}
        self._spend_energy: dict[str, float] = {}

        # fair-share fuel supply
        self._fair_share_fuel_existing: dict[tuple[str, str], float] = {}
        self._fair_share_fuel_expected: dict[tuple[str, str], FloatArray] = {}

        # bunker results (expected bunkering)
        self._total_energy: FloatArray = EMPTY_FLOAT
        self._fuel_expenses: FloatArray = EMPTY_FLOAT
        self._policy_expenses: FloatArray = EMPTY_FLOAT

        # shore power
        self._shore_power_capacity: FloatArray = EMPTY_FLOAT

        # costs
        self._fuel_cost_flow: FloatArray = EMPTY_FLOAT

        # investment metrics
        self._asset_charter_npv: FloatArray = EMPTY_FLOAT
        self._capex_npv: FloatArray = EMPTY_FLOAT
        self._asset_charter_rate: FloatArray = EMPTY_FLOAT
        self._freight_rate: FloatArray = EMPTY_FLOAT
        self._technology_charter_rate: FloatArray = EMPTY_FLOAT
        self._tied_capital: list[FloatArray] = []

    def initialize(self, length: int, route: Route, fuels: dict[str, Fuel]) -> None:
        self._initialize_expectation(length)

        port_names = [port.name for port in route.ports]
        n_leg = route.get_number_of_legs()
        n_leg_regional = route.get_number_of_regional_legs()
        n_port = route.get_number_of_ports()

        # voyage
        self._voyages = self._default_array()

        # trade
        self._cargo_miles = self._default_array()
        self._cargo_miles_leg = self._default_list_array(n_leg)
        self._cargo_miles_leg_nominal = self._default_list_array(n_leg)

        # speeds
        self._speed_mean = self._default_float(default=np.nan)
        self._speed_anchor_reference = self._default_float(default=np.nan)
        self._speed_anchor_optimal = self._default_float(default=np.nan)
        self._speeds = self._default_list_array(n_leg)

        # durations
        self._time_sea = self._default_list_array(n_leg)
        self._time_port = self._default_list_array(n_port)

        # energy demand
        self._raw_energy_sea = self._default_dict_list_array(EnergyDemandTypeID, n_leg)
        self._raw_energy_port = self._default_dict_list_array(
            EnergyDemandTypePortID, n_port
        )
        self._operational_energy_sea = self._default_dict_list_array(
            EnergyDemandTypeID, n_leg
        )
        self._operational_energy_port = self._default_dict_list_array(
            EnergyDemandTypePortID, n_port
        )
        self._operational_saving_fraction_sea = self._default_dict_float(
            EnergyDemandTypeID
        )
        self._operational_saving_fraction_port = self._default_dict_float(
            EnergyDemandTypePortID
        )
        self._energy_sea = self._default_dict_list_array(EnergyDemandTypeID, n_leg)
        self._energy_port = self._default_dict_list_array(
            EnergyDemandTypePortID, n_port
        )
        self._regional_operational_energy_sea = self._default_dict_list_array(
            EnergyDemandTypeID, n_leg_regional
        )
        self._regional_energy_sea = self._default_dict_list_array(
            EnergyDemandTypeID, n_leg_regional
        )

        # energy conservation
        self._energy_conservation_pi_sea = self._default_dict_list_array(
            EnergyDemandTypeID, n_leg_regional
        )
        self._energy_conservation_pi_port = self._default_dict_list_array(
            EnergyDemandTypePortID, n_port
        )
        self._energy_conservation_rhs_sea = self._default_dict_list_array(
            EnergyDemandTypeID, n_leg_regional
        )
        self._energy_conservation_rhs_port = self._default_dict_list_array(
            EnergyDemandTypePortID, n_port
        )
        self._energy_conservation_sarhslow_sea = self._default_dict_list_array(
            EnergyDemandTypeID, n_leg_regional
        )
        self._energy_conservation_sarhslow_port = self._default_dict_list_array(
            EnergyDemandTypePortID, n_port
        )
        self._energy_conservation_sarhsup_sea = self._default_dict_list_array(
            EnergyDemandTypeID, n_leg_regional
        )
        self._energy_conservation_sarhsup_port = self._default_dict_list_array(
            EnergyDemandTypePortID, n_port
        )

        # per-leg shadow-price belief paths (same shape as the raw pi dicts)
        self._belief_pi_sea_technology = self._default_dict_list_array(
            EnergyDemandTypeID, n_leg_regional
        )
        self._belief_pi_port_technology = self._default_dict_list_array(
            EnergyDemandTypePortID, n_port
        )
        self._belief_pi_sea_speed = self._default_dict_list_array(
            EnergyDemandTypeID, n_leg_regional
        )
        self._belief_pi_port_speed = self._default_dict_list_array(
            EnergyDemandTypePortID, n_port
        )

        # bunkering saved for inertia
        self._bunker_mass_expected = self._default_tuple_dict_float(port_names, fuels)
        self._bunker_mass_existing = self._default_tuple_dict_float(port_names, fuels)

        # fair-share
        self._fair_share_fuel_existing = self._default_tuple_dict_float(
            port_names, fuels
        )
        self._fair_share_fuel_expected = self._default_tuple_dict_array(
            port_names, fuels
        )

        # shore power
        self._shore_power_capacity = self._default_array()

        # expected bunker results (from BunkerAlgorithm)
        self._total_energy = self._default_array()
        self._fuel_expenses = self._default_array()
        self._policy_expenses = self._default_array()

        # costs
        self._fuel_cost_flow = self._default_array()

        # investment metrics
        self._asset_charter_npv = self._default_array()
        self._capex_npv = self._default_array()
        self._asset_charter_rate = self._default_array()
        self._freight_rate = self._default_array()
        self._technology_charter_rate = self._default_array()
        self._tied_capital = self._default_list_array(self._length)

    def reset_expected_bunkering(self) -> None:
        self._total_energy = self._default_array()
        self._fuel_expenses = self._default_array()
        self._policy_expenses = self._default_array()

    def reset_bunker_mass_expected(self) -> None:
        self._reset_dict_float(self._bunker_mass_expected)

    def reset_bunker_mass_existing(self) -> None:
        self._reset_dict_float(self._bunker_mass_existing)

    def reset_spend_energy(self) -> None:
        self._spend_energy = {}

    def set_voyages(self, idx: int, voyages: FloatLike) -> None:
        self._voyages[idx:] = voyages

    def set_cargo_miles(self, idx: int, cargo_miles: FloatLike) -> None:
        self._cargo_miles[idx:] = cargo_miles

    def set_cargo_miles_per_leg(
        self, idx: int, cargo_miles_leg: Sequence[FloatLike]
    ) -> None:
        for i, cargo_miles in enumerate(cargo_miles_leg):
            self._cargo_miles_leg[i][idx:] = cargo_miles

    def set_cargo_miles_per_leg_nominal(
        self, idx: int, cargo_miles_leg_nominal: Sequence[FloatLike]
    ) -> None:
        for i, cargo_miles_nominal in enumerate(cargo_miles_leg_nominal):
            self._cargo_miles_leg_nominal[i][idx:] = cargo_miles_nominal

    def set_speed_mean(self, speed_mean: float) -> None:
        self._speed_mean = speed_mean

    def set_speed_anchor_reference(self, value: float) -> None:
        self._speed_anchor_reference = value

    def get_speed_anchor_reference(self) -> float:
        return self._speed_anchor_reference

    def set_speed_anchor_optimal(self, value: float) -> None:
        self._speed_anchor_optimal = value

    def get_speed_anchor_optimal(self) -> float:
        return self._speed_anchor_optimal

    def set_speeds(self, idx: int, speeds: Sequence[FloatLike]) -> None:
        for i, speed in enumerate(speeds):
            self._speeds[i][idx] = speed

    def set_time_sea(self, idx: int, time_sea: Sequence[FloatLike]) -> None:
        for i, time in enumerate(time_sea):
            self._time_sea[i][idx:] = time

    def set_time_port(self, idx: int, time_port: Sequence[FloatLike]) -> None:
        for i, time in enumerate(time_port):
            self._time_port[i][idx:] = time

    def set_raw_energy_sea(
        self,
        idx: int,
        raw_energy_sea: Mapping[EnergyDemandTypeID, Sequence[FloatLike]],
    ) -> None:
        for key, values in raw_energy_sea.items():
            for leg, value in enumerate(values):
                self._raw_energy_sea[key][leg][idx:] = value

    def set_raw_energy_port(
        self,
        idx: int,
        raw_energy_port: Mapping[EnergyDemandTypeID, Sequence[FloatLike]],
    ) -> None:
        for key, values in raw_energy_port.items():
            for port, value in enumerate(values):
                self._raw_energy_port[key][port][idx:] = value

    def set_operational_energy_sea(
        self,
        idx: int,
        operational_energy_sea: Mapping[EnergyDemandTypeID, Sequence[FloatLike]],
    ) -> None:
        for key, values in operational_energy_sea.items():
            for leg, value in enumerate(values):
                self._operational_energy_sea[key][leg][idx:] = value

    def set_operational_energy_port(
        self,
        idx: int,
        operational_energy_port: Mapping[EnergyDemandTypeID, Sequence[FloatLike]],
    ) -> None:
        for key, values in operational_energy_port.items():
            for port, value in enumerate(values):
                self._operational_energy_port[key][port][idx:] = value

    def set_operational_saving_fraction_sea(
        self, saving_dict: dict[EnergyDemandTypeID, float]
    ) -> None:
        self._operational_saving_fraction_sea.update(saving_dict)

    def set_operational_saving_fraction_port(
        self, saving_dict: dict[EnergyDemandTypeID, float]
    ) -> None:
        self._operational_saving_fraction_port.update(saving_dict)

    def get_operational_saving_fraction_sea(self) -> dict[EnergyDemandTypeID, float]:
        return self._operational_saving_fraction_sea

    def get_operational_saving_fraction_port(self) -> dict[EnergyDemandTypeID, float]:
        return self._operational_saving_fraction_port

    def set_energy_sea(
        self, idx: int, energy_sea: Mapping[EnergyDemandTypeID, Sequence[FloatLike]]
    ) -> None:
        for key, values in energy_sea.items():
            for leg, value in enumerate(values):
                self._energy_sea[key][leg][idx:] = value

    def set_energy_port(
        self, idx: int, energy_port: Mapping[EnergyDemandTypeID, Sequence[FloatLike]]
    ) -> None:
        for key, values in energy_port.items():
            for leg, value in enumerate(values):
                self._energy_port[key][leg][idx:] = value

    def set_regional_operational_energy_sea(
        self,
        idx: int,
        regional_operational_energy_sea: Mapping[
            EnergyDemandTypeID, Sequence[FloatLike]
        ],
    ) -> None:
        for key, values in regional_operational_energy_sea.items():
            for leg, value in enumerate(values):
                self._regional_operational_energy_sea[key][leg][idx:] = value

    def set_regional_energy_sea(
        self,
        idx: int,
        regional_energy_sea: Mapping[EnergyDemandTypeID, Sequence[FloatLike]],
    ) -> None:
        for key, values in regional_energy_sea.items():
            for leg, value in enumerate(values):
                self._regional_energy_sea[key][leg][idx:] = value

    def set_energy_conservation_pi_sea(
        self, idx: int, energy_id: EnergyDemandTypeID, leg: int, pi: float
    ) -> None:
        self._energy_conservation_pi_sea[energy_id][leg][idx] = pi

    def set_energy_conservation_pi_port(
        self, idx: int, energy_id: EnergyDemandTypeID, port: int, pi: float
    ) -> None:
        self._energy_conservation_pi_port[energy_id][port][idx] = pi

    def set_energy_conservation_rhs_sea(
        self, idx: int, energy_id: EnergyDemandTypeID, leg: int, rhs: float
    ) -> None:
        self._energy_conservation_rhs_sea[energy_id][leg][idx] = rhs

    def set_energy_conservation_rhs_port(
        self, idx: int, energy_id: EnergyDemandTypeID, port: int, rhs: float
    ) -> None:
        self._energy_conservation_rhs_port[energy_id][port][idx] = rhs

    def set_energy_conservation_sarhslow_sea(
        self, idx: int, energy_id: EnergyDemandTypeID, leg: int, sarhslow: float
    ) -> None:
        self._energy_conservation_sarhslow_sea[energy_id][leg][idx] = sarhslow

    def set_energy_conservation_sarhslow_port(
        self, idx: int, energy_id: EnergyDemandTypeID, port: int, sarhslow: float
    ) -> None:
        self._energy_conservation_sarhslow_port[energy_id][port][idx] = sarhslow

    def set_energy_conservation_sarhsup_sea(
        self, idx: int, energy_id: EnergyDemandTypeID, leg: int, sarhsup: float
    ) -> None:
        self._energy_conservation_sarhsup_sea[energy_id][leg][idx] = sarhsup

    def set_energy_conservation_sarhsup_port(
        self, idx: int, energy_id: EnergyDemandTypeID, port: int, sarhsup: float
    ) -> None:
        self._energy_conservation_sarhsup_port[energy_id][port][idx] = sarhsup

    def add_bunker_mass_expected(
        self, port_name: str, fuel_name: str, mass: float
    ) -> None:
        self._bunker_mass_expected[(port_name, fuel_name)] += mass

    def add_bunker_mass_existing(
        self, port_name: str, fuel_name: str, mass: float
    ) -> None:
        self._bunker_mass_existing[(port_name, fuel_name)] += mass

    def add_spend_energy(self, converter_name: str, spend: float) -> None:
        self._spend_energy.setdefault(converter_name, 0.0)
        self._spend_energy[converter_name] += spend

    def set_fair_share_fuel_existing(
        self, port_name: str, fuel_name: str, fair_share: float
    ) -> None:
        self._fair_share_fuel_existing[(port_name, fuel_name)] = fair_share

    def set_fair_share_fuel_expected(
        self, idx: int, port_name: str, fuel_name: str, fair_share: FloatLike
    ) -> None:
        self._fair_share_fuel_expected[(port_name, fuel_name)][idx:] = fair_share

    def add_total_energy(self, idx: int, energy: float) -> None:
        self._total_energy[idx] += energy

    def add_fuel_expenses(self, idx: int, expenses: float) -> None:
        self._fuel_expenses[idx] += expenses

    def add_policy_expenses(self, idx: int, expenses: float) -> None:
        self._policy_expenses[idx] += expenses

    def add_policy_expenses_path(self, idx: int, expenses: FloatLike) -> None:
        self._policy_expenses[idx:] += expenses

    def set_shore_power_capacity(self, idx: int, value: float) -> None:
        self._shore_power_capacity[idx:] = value

    def get_shore_power_capacity(self, idx: int) -> float:
        capacity: float = self._shore_power_capacity[idx]
        return capacity

    def set_fuel_cost_flow(self, cost_flow: FloatArray) -> None:
        self._fuel_cost_flow = cost_flow

    def set_asset_charter_npv(self, idx: int, asset_charter_npv: float) -> None:
        self._asset_charter_npv[idx] = asset_charter_npv

    def set_capex_npv(self, idx: int, capex_npv: float) -> None:
        self._capex_npv[idx] = capex_npv

    def set_asset_charter_rate(self, idx: int, asset_charter_rate: float) -> None:
        self._asset_charter_rate[idx] = asset_charter_rate

    def set_freight_rate(self, idx: int, freight_rate: float) -> None:
        self._freight_rate[idx] = freight_rate

    def set_technology_charter_rate(
        self, idx: int, technology_charter_rate: float
    ) -> None:
        self._technology_charter_rate[idx] = technology_charter_rate

    def set_tied_capital(self, idx: int, tied_capital: FloatArray) -> None:
        self._tied_capital[idx] = tied_capital

    def get_voyages(self, idx: Index = np.s_[:]) -> FloatLike:
        return self._voyages[idx]

    def get_cargo_miles(self, idx: Index = np.s_[:]) -> FloatLike:
        return self._cargo_miles[idx]

    def get_cargo_miles_per_leg(self, idx: Index = np.s_[:]) -> list[FloatLike]:
        return slice_list(self._cargo_miles_leg, idx)

    def get_cargo_miles_per_leg_nominal(self, idx: Index = np.s_[:]) -> list[FloatLike]:
        return slice_list(self._cargo_miles_leg_nominal, idx)

    def get_speed_mean(self) -> float:
        return self._speed_mean

    def get_speeds(self, idx: Index = np.s_[:]) -> list[FloatLike]:
        return slice_list(self._speeds, idx)

    def get_time_sea(self, idx: Index) -> list[FloatLike]:
        return slice_list(self._time_sea, idx)

    def get_time_port(self, idx: Index) -> list[FloatLike]:
        return slice_list(self._time_port, idx)

    def get_raw_energy_sea(
        self, idx: Index = np.s_[:]
    ) -> dict[EnergyDemandTypeID, list[FloatLike]]:
        return slice_dict_list(self._raw_energy_sea, idx)

    def get_raw_energy_port(
        self, idx: Index = np.s_[:]
    ) -> dict[EnergyDemandTypeID, list[FloatLike]]:
        return slice_dict_list(self._raw_energy_port, idx)

    def get_operational_energy_sea(
        self, idx: Index = np.s_[:]
    ) -> dict[EnergyDemandTypeID, list[FloatLike]]:
        return slice_dict_list(self._operational_energy_sea, idx)

    def get_operational_energy_port(
        self, idx: Index = np.s_[:]
    ) -> dict[EnergyDemandTypeID, list[FloatLike]]:
        return slice_dict_list(self._operational_energy_port, idx)

    def get_energy_sea(
        self, idx: Index = np.s_[:]
    ) -> dict[EnergyDemandTypeID, list[FloatLike]]:
        return slice_dict_list(self._energy_sea, idx)

    def get_energy_port(
        self, idx: Index = np.s_[:]
    ) -> dict[EnergyDemandTypeID, list[FloatLike]]:
        return slice_dict_list(self._energy_port, idx)

    def get_regional_operational_energy_sea(
        self, idx: Index = np.s_[:]
    ) -> dict[EnergyDemandTypeID, list[FloatLike]]:
        return slice_dict_list(self._regional_operational_energy_sea, idx)

    def get_regional_energy_sea(
        self, idx: Index = np.s_[:]
    ) -> dict[EnergyDemandTypeID, list[FloatLike]]:
        return slice_dict_list(self._regional_energy_sea, idx)

    def get_total_demand(self, idx: Index = np.s_[:]) -> FloatLike:
        energies = [
            energy[idx]
            for area in (self._energy_sea, self._energy_port)
            for step in area.values()
            for energy in step
        ]

        # a route always has at least one leg and one port and the energy dicts are
        # keyed by a fixed enum, so the list is never empty
        total: FloatLike = np.add.reduce(energies)
        return total

    def get_energy_saving_sea(
        self, idx: int
    ) -> dict[EnergyDemandTypeID, list[FloatArray]]:
        return {
            energy_id: [
                1.0 - divide_nonzero(energy[idx], raw_energy[idx], default=1.0)
                for (energy, raw_energy) in zip(
                    self._energy_sea[energy_id],
                    self._raw_energy_sea[energy_id],
                    strict=True,
                )
            ]
            for energy_id in self._energy_sea
        }

    def get_energy_saving_port(
        self, idx: int
    ) -> dict[EnergyDemandTypeID, list[FloatArray]]:
        return {
            energy_id: [
                1.0 - divide_nonzero(energy[idx], raw_energy[idx], default=1.0)
                for (energy, raw_energy) in zip(
                    self._energy_port[energy_id],
                    self._raw_energy_port[energy_id],
                    strict=True,
                )
            ]
            for energy_id in self._energy_port
        }

    def get_energy_conservation_pi_sea(
        self,
    ) -> dict[EnergyDemandTypeID, list[FloatArray]]:
        return self._energy_conservation_pi_sea

    def get_energy_conservation_pi_port(
        self,
    ) -> dict[EnergyDemandTypeID, list[FloatArray]]:
        return self._energy_conservation_pi_port

    def get_energy_conservation_rhs_sea(
        self,
    ) -> dict[EnergyDemandTypeID, list[FloatArray]]:
        return self._energy_conservation_rhs_sea

    def get_energy_conservation_rhs_port(
        self,
    ) -> dict[EnergyDemandTypeID, list[FloatArray]]:
        return self._energy_conservation_rhs_port

    def get_energy_conservation_sarhslow_sea(
        self,
    ) -> dict[EnergyDemandTypeID, list[FloatArray]]:
        return self._energy_conservation_sarhslow_sea

    def get_energy_conservation_sarhslow_port(
        self,
    ) -> dict[EnergyDemandTypeID, list[FloatArray]]:
        return self._energy_conservation_sarhslow_port

    def get_energy_conservation_sarhsup_sea(
        self,
    ) -> dict[EnergyDemandTypeID, list[FloatArray]]:
        return self._energy_conservation_sarhsup_sea

    def get_energy_conservation_sarhsup_port(
        self,
    ) -> dict[EnergyDemandTypeID, list[FloatArray]]:
        return self._energy_conservation_sarhsup_port

    def get_belief_pi_sea_technology(
        self,
    ) -> dict[EnergyDemandTypeID, list[FloatArray]]:
        return self._belief_pi_sea_technology

    def get_belief_pi_port_technology(
        self,
    ) -> dict[EnergyDemandTypeID, list[FloatArray]]:
        return self._belief_pi_port_technology

    def get_belief_pi_sea_speed(self) -> dict[EnergyDemandTypeID, list[FloatArray]]:
        return self._belief_pi_sea_speed

    def get_belief_pi_port_speed(self) -> dict[EnergyDemandTypeID, list[FloatArray]]:
        return self._belief_pi_port_speed

    def get_bunker_mass_expected(self, port_name: str, fuel_name: str) -> float:
        return self._bunker_mass_expected[(port_name, fuel_name)]

    def get_bunker_mass_existing(self, port_name: str, fuel_name: str) -> float:
        return self._bunker_mass_existing[(port_name, fuel_name)]

    def get_spend_energy(self, converter_name: str) -> float:
        if converter_name in self._spend_energy:
            return self._spend_energy[converter_name]
        else:
            return 0.0

    def get_fair_share_fuel_existing(self, port_name: str, fuel_name: str) -> float:
        return self._fair_share_fuel_existing[(port_name, fuel_name)]

    def get_fair_share_fuels_existing(self) -> dict[tuple[str, str], float]:
        return self._fair_share_fuel_existing

    def get_fair_share_fuel_expected(
        self, port_name: str, fuel_name: str, idx: Index = np.s_[:]
    ) -> FloatLike:
        return self._fair_share_fuel_expected[(port_name, fuel_name)][idx]

    def get_total_energy(self, idx: Index = np.s_[:]) -> FloatLike:
        return self._total_energy[idx]

    def get_total_fuel_expenses(self, idx: Index = np.s_[:]) -> FloatLike:
        return self._fuel_expenses[idx] + self._policy_expenses[idx]

    def get_fuel_cost_flow(self) -> FloatArray:
        return self._fuel_cost_flow

    def get_asset_charter_npv(self, idx: int) -> float:
        npv: float = self._asset_charter_npv[idx]
        return npv

    def get_capex_npv(self, idx: int) -> float:
        npv: float = self._capex_npv[idx]
        return npv

    def get_asset_charter_rate(self, idx: Index) -> FloatLike:
        return self._asset_charter_rate[idx]

    def get_freight_rate(self, idx: int) -> float:
        rate: float = self._freight_rate[idx]
        return rate

    def get_technology_charter_rate(self, idx: int) -> float:
        rate: float = self._technology_charter_rate[idx]
        return rate

    def get_tied_capital(self, idx: SupportsIndex) -> FloatArray:
        return self._tied_capital[idx]
