# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import EnergyDemandTypeID, EnergyDemandTypePortID
from navigate.core.expectations._expectation import _Expectation
from navigate.core.misc import EMPTY_FLOAT
from navigate.util import (
    divide_nonzero,
    extract_from_dict_list,
    extract_from_tuple_dict,
    slice_list,
)

if TYPE_CHECKING:
    from navigate.fuel import Fuel
    from navigate.route.route import Route


class VesselExpectation(_Expectation):
    def __init__(self):
        super().__init__()

        # voyage
        self._voyages: np.ndarray = EMPTY_FLOAT               # number of voyages per year

        # cargo
        self._cargo_miles: np.ndarray = EMPTY_FLOAT           # amount of cargo miles delivered per year
        self._cargo_miles_leg: list[np.ndarray] = []           # list[np.ndarray] cargo miles delivered per leg
        self._cargo_miles_leg_nominal: list[np.ndarray] = []   # list[np.ndarray] nominal cargo miles delivered per leg

        # speeds
        self._speed_mean: float = np.nan                   # speed management mean speed (excluding weighting), knots
        self._speed_anchor_reference: float = np.nan       # initial route reference mean speed for anchoring, knots
        self._speed_anchor_optimal: float = np.nan         # initial modelled optimal mean speed for anchoring, knots
        self._speeds: list[np.ndarray] = []                # list[leg_idx: float], expected speed per leg, knots
        self._distances: list[np.ndarray] = []             # list[leg_idx: float] expected distances per leg, nautical miles

        # durations
        self._time_sea: list[np.ndarray] = []              # list[leg_idx: np.ndarray], time spent at sea, days
        self._time_port: list[np.ndarray] = []             # list[port_idx: np.ndarray], time spent in port, days

        # Energies
        self._raw_energy_sea: dict[EnergyDemandTypeID, list[np.ndarray]] = {}
        self._raw_energy_port: dict[EnergyDemandTypeID, list[np.ndarray]] = {}

        self._operational_energy_sea: dict[EnergyDemandTypeID, list[np.ndarray]] = {}
        self._operational_energy_port: dict[EnergyDemandTypeID, list[np.ndarray]] = {}

        self._operational_saving_fraction_sea: dict[EnergyDemandTypeID, float] = {d: 0. for d in EnergyDemandTypeID}
        self._operational_saving_fraction_port: dict[EnergyDemandTypeID, float] = {d: 0. for d in EnergyDemandTypePortID}

        self._energy_sea: dict[EnergyDemandTypeID, list[np.ndarray]] = {}
        self._energy_port: dict[EnergyDemandTypeID, list[np.ndarray]] = {}

        self._regional_raw_energy_sea: dict[EnergyDemandTypeID, list[np.ndarray]] = {}
        self._regional_operational_energy_sea: dict[EnergyDemandTypeID, list[np.ndarray]] = {}
        self._regional_energy_sea: dict[EnergyDemandTypeID, list[np.ndarray]] = {}

        # Constraint Attributes
        self._energy_conservation_pi_sea: dict[EnergyDemandTypeID, list[np.ndarray]] = {}
        self._energy_conservation_pi_port: dict[EnergyDemandTypeID, list[np.ndarray]] = {}
        self._energy_conservation_rhs_sea: dict[EnergyDemandTypeID, list[np.ndarray]] = {}
        self._energy_conservation_rhs_port: dict[EnergyDemandTypeID, list[np.ndarray]] = {}
        self._energy_conservation_sarhslow_sea: dict[EnergyDemandTypeID, list[np.ndarray]] = {}
        self._energy_conservation_sarhslow_port: dict[EnergyDemandTypeID, list[np.ndarray]] = {}
        self._energy_conservation_sarhsup_sea: dict[EnergyDemandTypeID, list[np.ndarray]] = {}
        self._energy_conservation_sarhsup_port: dict[EnergyDemandTypeID, list[np.ndarray]] = {}

        # per-leg, per-energy-type smoothed shadow-price beliefs (same shape as the raw pi
        # dicts above). Tech-horizon belief is amortised over the decision horizon used by
        # newbuild/retrofit NPVs; speed-horizon belief is faster, matched to the timescale of
        # operational speed management.
        self._belief_pi_sea_technology: dict[EnergyDemandTypeID, list[np.ndarray]] = {}
        self._belief_pi_port_technology: dict[EnergyDemandTypePortID, list[np.ndarray]] = {}
        self._belief_pi_sea_speed: dict[EnergyDemandTypeID, list[np.ndarray]] = {}
        self._belief_pi_port_speed: dict[EnergyDemandTypePortID, list[np.ndarray]] = {}

        # bunkering/spend
        self._bunker_mass_expected: dict[tuple[str, str], float] = {}     # amount of fuel bunkered, tons
        self._bunker_mass_existing: dict[tuple[str, str], float] = {}     # amount of fuel bunkered, tons
        self._spend_energy: dict[str, float] = {}             # dict[converter_name: float], amount of fuel bunkered/spend, GJ

        # fair-share fuel supply
        self._fair_share_fuel_existing: dict[tuple[str, str], float] = {}       # fair-share for bunkering
        self._fair_share_fuel_expected: dict[tuple[str, str], np.ndarray] = {}  # fair-share for bunkering

        # bunker results (expected bunkering)
        self._total_energy: np.ndarray = EMPTY_FLOAT       # total energy
        self._fuel_expenses: np.ndarray = EMPTY_FLOAT      # fuel expenses
        self._policy_expenses: np.ndarray = EMPTY_FLOAT    # policy expenses (remedial, flexible, surplus, levy)

        # shore power
        self._shore_power_capacity: np.ndarray = EMPTY_FLOAT      # MW, uptake-weighted average

        # costs
        self._fuel_cost_flow: np.ndarray = EMPTY_FLOAT            # future fuel cost, USD/year

        # investment metrics
        self._asset_charter_npv: np.ndarray = EMPTY_FLOAT             # charter NPV, USD
        self._capex_npv: np.ndarray = EMPTY_FLOAT                     # summed ship CAPEX NPV, USD
        self._asset_charter_rate: np.ndarray = EMPTY_FLOAT            # charter rate, USD/year
        self._freight_rate: np.ndarray = EMPTY_FLOAT                  # freight rate, USD/year
        self._technology_charter_rate: np.ndarray = EMPTY_FLOAT       # fleet-average technology charge, USD/year
        self._tied_capital: list[np.ndarray | None] = []               # list[time_step: np.ndarray], USD

    def initialize(self, length: int, route: Route, fuels: dict[str, Fuel]) -> None:
        self._initialize_expectation(length)

        port_names = [port.get_name() for port in route.ports]
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
        self._distances = self._default_list_array(n_leg)

        # durations
        self._time_sea = self._default_list_array(n_leg)
        self._time_port = self._default_list_array(n_port)

        # energy demand
        self._raw_energy_sea = self._default_dict_list_array(EnergyDemandTypeID, n_leg)
        self._raw_energy_port = self._default_dict_list_array(EnergyDemandTypePortID, n_port)
        self._operational_energy_sea = self._default_dict_list_array(EnergyDemandTypeID, n_leg)
        self._operational_energy_port = self._default_dict_list_array(EnergyDemandTypePortID, n_port)
        self._energy_sea = self._default_dict_list_array(EnergyDemandTypeID, n_leg)
        self._energy_port = self._default_dict_list_array(EnergyDemandTypePortID, n_port)
        self._regional_raw_energy_sea = self._default_dict_list_array(EnergyDemandTypeID, n_leg_regional)
        self._regional_operational_energy_sea = self._default_dict_list_array(EnergyDemandTypeID, n_leg_regional)
        self._regional_energy_sea = self._default_dict_list_array(EnergyDemandTypeID, n_leg_regional)

        # energy conservation
        self._energy_conservation_pi_sea = self._default_dict_list_array(EnergyDemandTypeID, n_leg_regional)
        self._energy_conservation_pi_port = self._default_dict_list_array(EnergyDemandTypePortID, n_port)
        self._energy_conservation_rhs_sea = self._default_dict_list_array(EnergyDemandTypeID, n_leg_regional)
        self._energy_conservation_rhs_port = self._default_dict_list_array(EnergyDemandTypePortID, n_port)
        self._energy_conservation_sarhslow_sea = self._default_dict_list_array(EnergyDemandTypeID, n_leg_regional)
        self._energy_conservation_sarhslow_port = self._default_dict_list_array(EnergyDemandTypePortID, n_port)
        self._energy_conservation_sarhsup_sea = self._default_dict_list_array(EnergyDemandTypeID, n_leg_regional)
        self._energy_conservation_sarhsup_port = self._default_dict_list_array(EnergyDemandTypePortID, n_port)

        # per-leg shadow-price belief paths (same shape as the raw pi dicts)
        self._belief_pi_sea_technology = self._default_dict_list_array(EnergyDemandTypeID, n_leg_regional)
        self._belief_pi_port_technology = self._default_dict_list_array(EnergyDemandTypePortID, n_port)
        self._belief_pi_sea_speed = self._default_dict_list_array(EnergyDemandTypeID, n_leg_regional)
        self._belief_pi_port_speed = self._default_dict_list_array(EnergyDemandTypePortID, n_port)

        # bunkering saved for inertia
        self._bunker_mass_expected = self._default_tuple_dict_float(port_names, fuels)
        self._bunker_mass_existing = self._default_tuple_dict_float(port_names, fuels)

        # fair-share
        self._fair_share_fuel_existing = self._default_tuple_dict_float(port_names, fuels)
        self._fair_share_fuel_expected = self._default_tuple_dict_array(port_names, fuels)

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
        self._tied_capital = [None] * length

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

    def set_voyages(self, idx: int, voyages: float | np.ndarray) -> None:
        self._voyages[idx:] = voyages

    def set_cargo_miles(self, idx: int, cargo_miles: float | np.ndarray) -> None:
        self._cargo_miles[idx:] = cargo_miles

    def set_cargo_miles_per_leg(self, idx: int, cargo_miles_leg: list) -> None:
        for i, cargo_miles in enumerate(cargo_miles_leg):
            self._cargo_miles_leg[i][idx:] = cargo_miles

    def set_cargo_miles_per_leg_nominal(self, idx: int, cargo_miles_leg_nominal: list) -> None:
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

    def set_speeds(self, idx: int, speeds: list) -> None:
        for i, speed in enumerate(speeds):
            self._speeds[i][idx] = speed

    def set_distances(self, idx: int, distances: list) -> None:
        for i, distance in enumerate(distances):
            self._distances[i][idx:] = distance

    def set_time_sea(self, idx: int, time_sea: list) -> None:
        for i, time in enumerate(time_sea):
            self._time_sea[i][idx:] = time

    def set_time_port(self, idx: int, time_port: list) -> None:
        for i, time in enumerate(time_port):
            self._time_port[i][idx:] = time

    def set_raw_energy_sea(self, idx: int, raw_energy_sea: dict[EnergyDemandTypeID, list]) -> None:
        for key, values in raw_energy_sea.items():
            for leg, value in enumerate(values):
                self._raw_energy_sea[key][leg][idx:] = value

    def set_raw_energy_port(self, idx: int, raw_energy_port: dict[EnergyDemandTypeID, list]) -> None:
        for key, values in raw_energy_port.items():
            for port, value in enumerate(values):
                self._raw_energy_port[key][port][idx:] = value

    def set_operational_energy_sea(self, idx: int, operational_energy_sea: dict[EnergyDemandTypeID, list]) -> None:
        for key, values in operational_energy_sea.items():
            for leg, value in enumerate(values):
                self._operational_energy_sea[key][leg][idx:] = value

    def set_operational_energy_port(self, idx: int, operational_energy_port: dict[EnergyDemandTypeID, list]) -> None:
        for key, values in operational_energy_port.items():
            for port, value in enumerate(values):
                self._operational_energy_port[key][port][idx:] = value

    def set_operational_saving_fraction_sea(self, saving_dict: dict[EnergyDemandTypeID, float]) -> None:
        self._operational_saving_fraction_sea.update(saving_dict)

    def set_operational_saving_fraction_port(self, saving_dict: dict[EnergyDemandTypeID, float]) -> None:
        self._operational_saving_fraction_port.update(saving_dict)

    def get_operational_saving_fraction_sea(self) -> dict[EnergyDemandTypeID, float]:
        return self._operational_saving_fraction_sea

    def get_operational_saving_fraction_port(self) -> dict[EnergyDemandTypeID, float]:
        return self._operational_saving_fraction_port

    def set_energy_sea(self, idx: int, energy_sea: dict[EnergyDemandTypeID, list]) -> None:
        for key, values in energy_sea.items():
            for leg, value in enumerate(values):
                self._energy_sea[key][leg][idx:] = value

    def set_energy_port(self, idx: int, energy_port: dict[EnergyDemandTypeID, list]) -> None:
        for key, values in energy_port.items():
            for leg, value in enumerate(values):
                self._energy_port[key][leg][idx:] = value

    def set_regional_raw_energy_sea(self, idx: int, regional_energy_port: dict[EnergyDemandTypeID, list]) -> None:
        for key, values in regional_energy_port.items():
            for leg, value in enumerate(values):
                self._regional_raw_energy_sea[key][leg][idx:] = value

    def set_regional_operational_energy_sea(
            self, idx: int,
            regional_operational_energy_sea: dict[EnergyDemandTypeID, list]) -> None:
        for key, values in regional_operational_energy_sea.items():
            for leg, value in enumerate(values):
                self._regional_operational_energy_sea[key][leg][idx:] = value

    def set_regional_energy_sea(self, idx: int, regional_energy_sea: dict[EnergyDemandTypeID, list]) -> None:
        for key, values in regional_energy_sea.items():
            for leg, value in enumerate(values):
                self._regional_energy_sea[key][leg][idx:] = value

    def set_energy_conservation_pi_sea(self, idx: int, energy_id: EnergyDemandTypeID, leg: int, pi: float) -> None:
        self._energy_conservation_pi_sea[energy_id][leg][idx] = pi

    def set_energy_conservation_pi_port(self, idx: int, energy_id: EnergyDemandTypeID, port: int, pi: float) -> None:
        self._energy_conservation_pi_port[energy_id][port][idx] = pi

    def set_energy_conservation_rhs_sea(self, idx: int, energy_id: EnergyDemandTypeID, leg: int, rhs: float) -> None:
        self._energy_conservation_rhs_sea[energy_id][leg][idx] = rhs

    def set_energy_conservation_rhs_port(self, idx: int, energy_id: EnergyDemandTypeID, port: int, rhs: float) -> None:
        self._energy_conservation_rhs_port[energy_id][port][idx] = rhs

    def set_energy_conservation_sarhslow_sea(self, idx: int, energy_id: EnergyDemandTypeID, leg: int, sarhslow: float) -> None:
        self._energy_conservation_sarhslow_sea[energy_id][leg][idx] = sarhslow

    def set_energy_conservation_sarhslow_port(
            self, idx: int, energy_id: EnergyDemandTypeID,
            port: int, sarhslow: float) -> None:
        self._energy_conservation_sarhslow_port[energy_id][port][idx] = sarhslow

    def set_energy_conservation_sarhsup_sea(self, idx: int, energy_id: EnergyDemandTypeID, leg: int, sarhsup: float) -> None:
        self._energy_conservation_sarhsup_sea[energy_id][leg][idx] = sarhsup

    def set_energy_conservation_sarhsup_port(
            self, idx: int, energy_id: EnergyDemandTypeID,
            port: int, sarhsup: float) -> None:
        self._energy_conservation_sarhsup_port[energy_id][port][idx] = sarhsup

    def add_bunker_mass_expected(self, port_name: str, fuel_name: str, mass: float) -> None:
        self._bunker_mass_expected[(port_name, fuel_name)] += mass

    def add_bunker_mass_existing(self, port_name: str, fuel_name: str, mass: float) -> None:
        self._bunker_mass_existing[(port_name, fuel_name)] += mass

    def add_spend_energy(self, converter_name: str, spend: float) -> None:
        self._spend_energy.setdefault(converter_name, 0.)
        self._spend_energy[converter_name] += spend

    def set_fair_share_fuel_existing(self, port_name: str, fuel_name: str, fair_share: float) -> None:
        self._fair_share_fuel_existing[(port_name, fuel_name)] = fair_share

    def set_fair_share_fuel_expected(self, idx: int, port_name: str, fuel_name: str, fair_share: np.ndarray) -> None:
        self._fair_share_fuel_expected[(port_name, fuel_name)][idx:] = fair_share

    def add_total_energy(self, idx: int, energy: float) -> None:
        self._total_energy[idx] += energy

    def add_fuel_expenses(self, idx: int, expenses: float) -> None:
        self._fuel_expenses[idx] += expenses

    def add_policy_expenses(self, idx: int, expenses: float) -> None:
        self._policy_expenses[idx] += expenses

    def add_policy_expenses_path(self, idx: int, expenses: np.ndarray) -> None:
        self._policy_expenses[idx:] += expenses

    def set_shore_power_capacity(self, idx: int, value: float) -> None:
        self._shore_power_capacity[idx:] = value

    def get_shore_power_capacity(self, idx: int) -> float:
        return self._shore_power_capacity[idx]

    def set_fuel_cost_flow(self, cost_flow: np.ndarray) -> None:
        self._fuel_cost_flow = cost_flow

    def set_asset_charter_npv(self, idx: int, asset_charter_npv: float) -> None:
        self._asset_charter_npv[idx] = asset_charter_npv

    def set_capex_npv(self, idx: int, capex_npv: float) -> None:
        self._capex_npv[idx] = capex_npv

    def set_asset_charter_rate(self, idx: int, asset_charter_rate: float) -> None:
        self._asset_charter_rate[idx] = asset_charter_rate

    def set_freight_rate(self, idx: int, freight_rate: float) -> None:
        self._freight_rate[idx] = freight_rate

    def set_technology_charter_rate(self, idx: int, technology_charter_rate: float) -> None:
        self._technology_charter_rate[idx] = technology_charter_rate

    def set_tied_capital(self, idx: int, tied_capital: np.ndarray) -> None:
        self._tied_capital[idx] = tied_capital

    def get_voyages(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._voyages[idx]

    def get_cargo_miles(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._cargo_miles[idx]

    def get_cargo_miles_per_leg(self, idx: int | slice = np.s_[:]) -> list[np.ndarray]:
        return slice_list(self._cargo_miles_leg, idx)

    def get_cargo_miles_per_leg_nominal(self, idx: int | slice = np.s_[:]) -> list[np.ndarray]:
        return slice_list(self._cargo_miles_leg_nominal, idx)

    def get_speed_mean(self) -> float:
        return self._speed_mean

    def get_speeds(self, idx: int | slice = np.s_[:]) -> list[np.ndarray]:
        return slice_list(self._speeds, idx)

    def get_distances(self, idx: int | slice = np.s_[:]) -> list[np.ndarray]:
        return slice_list(self._distances, idx)

    def get_time_sea(self, idx: int | slice) -> list[np.ndarray]:
        return slice_list(self._time_sea, idx)

    def get_time_port(self, idx: int | slice) -> list[np.ndarray]:
        return slice_list(self._time_port, idx)

    def get_raw_energy_sea(self, energy_type_id: EnergyDemandTypeID | None = None,
                           idx: int | slice = np.s_[:]) -> dict[EnergyDemandTypeID, list] | list:
        return extract_from_dict_list(self._raw_energy_sea, energy_type_id, idx)

    def get_raw_energy_port(self, energy_type_id: EnergyDemandTypeID | None = None,
                            idx: int | slice = np.s_[:]) -> dict[EnergyDemandTypeID, list] | list:
        return extract_from_dict_list(self._raw_energy_port, energy_type_id, idx)

    def get_raw_energy_per_leg(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return np.sum([np.array(slice_list(legs, idx)) for legs in self._raw_energy_sea.values()], axis=0)

    def get_raw_energy_per_port(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return np.sum([np.array(slice_list(ports, idx)) for ports in self._raw_energy_port.values()], axis=0)

    def get_operational_energy_sea(self, energy_type_id: EnergyDemandTypeID | None = None,
                                   idx: int | slice = np.s_[:]) -> dict[EnergyDemandTypeID, list] | list:
        return extract_from_dict_list(self._operational_energy_sea, energy_type_id, idx)

    def get_operational_energy_port(self, energy_type_id: EnergyDemandTypeID | None = None,
                                    idx: int | slice = np.s_[:]) -> dict[EnergyDemandTypeID, list] | list:
        return extract_from_dict_list(self._operational_energy_port, energy_type_id, idx)

    def get_operational_energy_per_leg(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return np.sum([np.array(slice_list(legs, idx)) for legs in self._operational_energy_sea.values()], axis=0)

    def get_operational_energy_per_port(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return np.sum([np.array(slice_list(ports, idx)) for ports in self._operational_energy_port.values()], axis=0)

    def get_energy_sea(self, energy_type_id: EnergyDemandTypeID | None = None,
                       idx: int | slice = np.s_[:]) -> dict[EnergyDemandTypeID, list] | list:
        return extract_from_dict_list(self._energy_sea, energy_type_id, idx)

    def get_energy_port(self, energy_type_id: EnergyDemandTypeID | None = None,
                        idx: int | slice = np.s_[:]) -> dict[EnergyDemandTypeID, list] | list:
        return extract_from_dict_list(self._energy_port, energy_type_id, idx)

    def get_regional_raw_energy_sea(self, energy_type_id: EnergyDemandTypeID | None = None,
                                    idx: int | slice = np.s_[:]) -> dict[EnergyDemandTypeID, list] | list:
        return extract_from_dict_list(self._regional_raw_energy_sea, energy_type_id, idx)

    def get_regional_operational_energy_sea(self, energy_type_id: EnergyDemandTypeID | None = None,
                                            idx: int | slice = np.s_[:]) -> dict[EnergyDemandTypeID, list] | list:
        return extract_from_dict_list(self._regional_operational_energy_sea, energy_type_id, idx)

    def get_regional_energy_sea(self, energy_type_id: EnergyDemandTypeID | None = None,
                                idx: int | slice = np.s_[:]) -> dict[EnergyDemandTypeID, list] | list:
        return extract_from_dict_list(self._regional_energy_sea, energy_type_id, idx)

    def get_total_demand(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        energy_sea = self.get_energy_sea(idx=idx)
        energy_port = self.get_energy_port(idx=idx)
        energies = [energy
                    for area in (energy_sea, energy_port)
                    for step in area.values()
                    for energy in step]

        return np.sum(energies, axis=0)

    def get_energy_saving_sea(self, idx: int) -> dict[EnergyDemandTypeID, list]:
        return {energy_id: [1. - divide_nonzero(energy[idx], raw_energy[idx], default=1.)
                            for (energy, raw_energy) in zip(self._energy_sea[energy_id], self._raw_energy_sea[energy_id])]
                for energy_id in self._energy_sea.keys()}

    def get_energy_saving_port(self, idx: int) -> dict[EnergyDemandTypeID, list]:
        return {energy_id: [1. - divide_nonzero(energy[idx], raw_energy[idx], default=1.)
                            for (energy, raw_energy) in zip(self._energy_port[energy_id], self._raw_energy_port[energy_id])]
                for energy_id in self._energy_port.keys()}

    def get_operational_saving_sea(self, idx: int) -> dict[EnergyDemandTypeID, list]:
        return {energy_id: [1. - divide_nonzero(op[idx], raw[idx], default=1.)
                            for (op, raw) in zip(self._operational_energy_sea[energy_id],
                                                 self._raw_energy_sea[energy_id])]
                for energy_id in self._operational_energy_sea.keys()}

    def get_operational_saving_port(self, idx: int) -> dict[EnergyDemandTypeID, list]:
        return {energy_id: [1. - divide_nonzero(op[idx], raw[idx], default=1.)
                            for (op, raw) in zip(self._operational_energy_port[energy_id],
                                                 self._raw_energy_port[energy_id])]
                for energy_id in self._operational_energy_port.keys()}

    def get_energy_conservation_pi_sea(self) -> dict[EnergyDemandTypeID, list[np.ndarray]]:
        return self._energy_conservation_pi_sea

    def get_energy_conservation_pi_port(self) -> dict[EnergyDemandTypeID, list[np.ndarray]]:
        return self._energy_conservation_pi_port

    def get_energy_conservation_rhs_sea(self) -> dict[EnergyDemandTypeID, list[np.ndarray]]:
        return self._energy_conservation_rhs_sea

    def get_energy_conservation_rhs_port(self) -> dict[EnergyDemandTypeID, list[np.ndarray]]:
        return self._energy_conservation_rhs_port

    def get_energy_conservation_sarhslow_sea(self) -> dict[EnergyDemandTypeID, list[np.ndarray]]:
        return self._energy_conservation_sarhslow_sea

    def get_energy_conservation_sarhslow_port(self) -> dict[EnergyDemandTypeID, list[np.ndarray]]:
        return self._energy_conservation_sarhslow_port

    def get_energy_conservation_sarhsup_sea(self) -> dict[EnergyDemandTypeID, list[np.ndarray]]:
        return self._energy_conservation_sarhsup_sea

    def get_energy_conservation_sarhsup_port(self) -> dict[EnergyDemandTypeID, list[np.ndarray]]:
        return self._energy_conservation_sarhsup_port

    def get_belief_pi_sea_technology(self) -> dict[EnergyDemandTypeID, list[np.ndarray]]:
        return self._belief_pi_sea_technology

    def get_belief_pi_port_technology(self) -> dict[EnergyDemandTypePortID, list[np.ndarray]]:
        return self._belief_pi_port_technology

    def get_belief_pi_sea_speed(self) -> dict[EnergyDemandTypeID, list[np.ndarray]]:
        return self._belief_pi_sea_speed

    def get_belief_pi_port_speed(self) -> dict[EnergyDemandTypePortID, list[np.ndarray]]:
        return self._belief_pi_port_speed

    def get_bunker_mass_expected(self, port_name: str, fuel_name: str) -> float:
        return self._bunker_mass_expected[(port_name, fuel_name)]

    def get_bunker_mass_existing(self, port_name: str, fuel_name: str) -> float:
        return self._bunker_mass_existing[(port_name, fuel_name)]

    def get_spend_energy(self, converter_name: str) -> float:
        if converter_name in self._spend_energy:
            return self._spend_energy[converter_name]
        else:
            return 0.

    def get_fair_share_fuel_existing(
            self, port_name: str | None = None,
            fuel_name: str | None = None) -> float | dict[tuple[str, str], float]:
        return extract_from_tuple_dict(self._fair_share_fuel_existing, port_name, fuel_name)

    def get_fair_share_fuel_expected(self, port_name: str | None = None,
                                     fuel_name: str | None = None,
                                     idx: int | slice = np.s_[:]) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        return extract_from_tuple_dict(self._fair_share_fuel_expected, port_name, fuel_name, idx=idx)

    def get_total_energy(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._total_energy[idx]

    def get_total_fuel_expenses(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._fuel_expenses[idx] + self._policy_expenses[idx]

    def get_fuel_cost_flow(self) -> np.ndarray:
        return self._fuel_cost_flow

    def get_asset_charter_npv(self, idx: int) -> float:
        return self._asset_charter_npv[idx]

    def get_capex_npv(self, idx: int) -> float:
        return self._capex_npv[idx]

    def get_asset_charter_rate(self, idx: int) -> float:
        return self._asset_charter_rate[idx]

    def get_freight_rate(self, idx: int) -> float:
        return self._freight_rate[idx]

    def get_technology_charter_rate(self, idx: int) -> float:
        return self._technology_charter_rate[idx]

    def get_tied_capital(self, idx: int) -> np.ndarray | None:
        return self._tied_capital[idx]
