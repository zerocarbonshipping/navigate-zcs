# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Vessel node, read by the fleet, the bunkering LP and policy."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np

from navigate.core.enum_ import PORT_ENERGY_DEMANDS, EnergyDemandID, FuelTypeID
from navigate.core.expectations._expectation import _Expectation
from navigate.util import slice_dict_list, slice_list

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping, Sequence

    from navigate.core.nodes.route import Route
    from navigate.util.types_ import FloatArray, FloatLike, Index


class VesselExpectation(_Expectation):
    """Voyage, energy, bunkering and investment paths of a single vessel."""

    def __init__(self) -> None:
        super().__init__()

        self._voyages: FloatArray

        self._cargo_miles: FloatArray
        self._cargo_miles_leg: list[FloatArray]
        self._cargo_miles_leg_nominal: list[FloatArray]

        self._speed_mean: float
        self._speed_anchor_reference: float
        self._speed_anchor_optimal: float
        self._speeds_condition: list[FloatArray]

        self._time_sea_condition: list[FloatArray]
        self._time_port: list[FloatArray]

        # energies, at sea per condition and per leg, in port per stop
        self._raw_energy_sea_condition: dict[EnergyDemandID, list[FloatArray]]
        self._raw_energy_port: dict[EnergyDemandID, list[FloatArray]]

        self._operational_energy_sea_condition: dict[EnergyDemandID, list[FloatArray]]
        self._operational_energy_sea_leg: dict[EnergyDemandID, list[FloatArray]]
        self._operational_energy_port: dict[EnergyDemandID, list[FloatArray]]

        self._operational_saving_fraction_sea: dict[EnergyDemandID, float]
        self._operational_saving_fraction_port: dict[EnergyDemandID, float]

        self._energy_sea_condition: dict[EnergyDemandID, list[FloatArray]]
        self._energy_sea_leg: dict[EnergyDemandID, list[FloatArray]]
        self._energy_port: dict[EnergyDemandID, list[FloatArray]]

        # energy conservation, at sea per leg, in port per stop
        self._energy_conservation_pi_sea: dict[EnergyDemandID, list[FloatArray]]
        self._energy_conservation_pi_port: dict[EnergyDemandID, list[FloatArray]]
        self._energy_conservation_rhs_sea: dict[EnergyDemandID, list[FloatArray]]
        self._energy_conservation_rhs_port: dict[EnergyDemandID, list[FloatArray]]

        # beliefs: smoothed shadow prices, the technology belief over the newbuild and
        # retrofit decision horizon, the speed belief faster to match speed management
        self._belief_pi_sea_technology: dict[EnergyDemandID, list[FloatArray]]
        self._belief_pi_port_technology: dict[EnergyDemandID, list[FloatArray]]
        self._belief_pi_sea_speed: dict[EnergyDemandID, list[FloatArray]]
        self._belief_pi_port_speed: dict[EnergyDemandID, list[FloatArray]]

        # effective lower heating value per converter and fuel
        self._effective_lhv: dict[tuple[str, str], float]

        # TTW emissions per converter, fuel and emission, in ton emission/ton fuel-in,
        # before GWP
        self._ttw_consumption: dict[tuple[str, str, str], float]
        self._ttw_slip: dict[tuple[str, str, str], float]

        # the vessel's means over its converters: the effective lower heating value per
        # fuel, and the TTW emissions per fuel and emission
        self._mean_effective_lhv: dict[str, float]
        self._mean_ttw_consumption: dict[tuple[str, str], float]
        self._mean_ttw_slip: dict[tuple[str, str], float]

        self._bunker_mass_expected: dict[tuple[str, str], FloatArray]
        self._bunker_mass_existing: dict[tuple[str, str], float]
        self._spend_energy: dict[str, float]

        # potential fuel-type demand at each port of the route
        self._potential_fuel_type_demand: dict[tuple[str, FuelTypeID], FloatArray]

        # fair-share fuel supply, and the existing bunkering's allocation of it
        self._fair_share_fuel_existing: dict[tuple[str, str], float]
        self._fair_share_fuel_expected: dict[tuple[str, str], FloatArray]
        self._allocation_fuel_existing: dict[tuple[str, str], float]

        # bunker results (expected bunkering)
        self._total_energy: FloatArray
        self._fuel_expenses: FloatArray

        # policy expenses (expected bunkering): the remedial expenses of each expected
        # LP, and the net flexibility expenses valued at the smoothed flexibility cost
        self._remedial_expenses: FloatArray
        self._flexibility_expenses: FloatArray

        self._shore_power_capacity: FloatArray
        self._shore_power_limit_port: list[FloatArray]

        self._fuel_cost_flow: FloatArray

        self._asset_charter_npv: FloatArray
        self._capex_npv: FloatArray
        self._asset_charter_rate: FloatArray
        self._freight_rate: FloatArray
        self._technology_charter_rate: FloatArray
        self._tied_capital: list[FloatArray]

    def initialize(
        self,
        length: int,
        route: Route,
        fuel_names: Collection[str],
        usable_fuel_names: Collection[str],
        fuels_per_converter: Mapping[str, Collection[str]],
        emission_names: Collection[str],
    ) -> None:
        self._initialize_expectation(length)

        port_names = [port.name for port in route.ports]
        condition_count = len(route.get_conditions())
        leg_count = len(route.get_legs())
        port_count = len(route.ports)

        self._voyages = self._default_array()

        self._cargo_miles = self._default_array()
        self._cargo_miles_leg = self._default_list_array(leg_count)
        self._cargo_miles_leg_nominal = self._default_list_array(leg_count)

        self._speed_mean = np.nan
        self._speed_anchor_reference = np.nan
        self._speed_anchor_optimal = np.nan
        self._speeds_condition = self._default_list_array(condition_count)

        self._time_sea_condition = self._default_list_array(condition_count)
        self._time_port = self._default_list_array(port_count)

        self._raw_energy_sea_condition = self._default_dict_list_array(
            EnergyDemandID, condition_count
        )
        self._raw_energy_port = self._default_dict_list_array(
            PORT_ENERGY_DEMANDS, port_count
        )

        self._operational_energy_sea_condition = self._default_dict_list_array(
            EnergyDemandID, condition_count
        )
        self._operational_energy_sea_leg = self._default_dict_list_array(
            EnergyDemandID, leg_count
        )
        self._operational_energy_port = self._default_dict_list_array(
            PORT_ENERGY_DEMANDS, port_count
        )

        self._operational_saving_fraction_sea = self._default_dict_float(EnergyDemandID)
        self._operational_saving_fraction_port = self._default_dict_float(
            PORT_ENERGY_DEMANDS
        )

        self._energy_sea_condition = self._default_dict_list_array(
            EnergyDemandID, condition_count
        )
        self._energy_sea_leg = self._default_dict_list_array(EnergyDemandID, leg_count)
        self._energy_port = self._default_dict_list_array(
            PORT_ENERGY_DEMANDS, port_count
        )

        self._energy_conservation_pi_sea = self._default_dict_list_array(
            EnergyDemandID, leg_count
        )
        self._energy_conservation_pi_port = self._default_dict_list_array(
            PORT_ENERGY_DEMANDS, port_count
        )
        self._energy_conservation_rhs_sea = self._default_dict_list_array(
            EnergyDemandID, leg_count
        )
        self._energy_conservation_rhs_port = self._default_dict_list_array(
            PORT_ENERGY_DEMANDS, port_count
        )

        # beliefs: NaN until the first update, as a dual is legitimately zero wherever
        # its constraint does not bind, so zero cannot mark "no prior"
        self._belief_pi_sea_technology = self._default_dict_list_array(
            EnergyDemandID, leg_count, default=np.nan
        )
        self._belief_pi_port_technology = self._default_dict_list_array(
            PORT_ENERGY_DEMANDS, port_count, default=np.nan
        )
        self._belief_pi_sea_speed = self._default_dict_list_array(
            EnergyDemandID, leg_count, default=np.nan
        )
        self._belief_pi_port_speed = self._default_dict_list_array(
            PORT_ENERGY_DEMANDS, port_count, default=np.nan
        )

        # the keys are each converter with each fuel it burns, and for the TTW each
        # emission too; all values are NaN until the first step sets them
        lhv_keys: list[tuple[str, str]] = []
        ttw_keys: list[tuple[str, str, str]] = []
        for converter_name, burned in fuels_per_converter.items():
            for fuel_name in burned:
                lhv_keys.append((converter_name, fuel_name))
                for emission_name in emission_names:
                    ttw_keys.append((converter_name, fuel_name, emission_name))

        self._effective_lhv = self._default_dict_float(lhv_keys, default=np.nan)
        self._ttw_consumption = self._default_dict_float(ttw_keys, default=np.nan)
        self._ttw_slip = self._default_dict_float(ttw_keys, default=np.nan)

        # the means are keyed by every usable fuel, burned on board or only stored
        self._mean_effective_lhv = self._default_dict_float(
            usable_fuel_names, default=np.nan
        )
        self._mean_ttw_consumption = self._default_tuple_dict_float(
            usable_fuel_names, emission_names, default=np.nan
        )
        self._mean_ttw_slip = self._default_tuple_dict_float(
            usable_fuel_names, emission_names, default=np.nan
        )

        # bunker masses and spend energy: the masses set the inertia floors, the
        # expected ones also the fleet's fuel demand
        self._bunker_mass_expected = self._default_tuple_dict_array(
            port_names, fuel_names
        )
        self._bunker_mass_existing = self._default_tuple_dict_float(
            port_names, fuel_names
        )
        self._spend_energy = self._default_dict_float(fuels_per_converter)

        self._potential_fuel_type_demand = self._default_tuple_dict_array(
            port_names, FuelTypeID
        )

        self._fair_share_fuel_existing = self._default_tuple_dict_float(
            port_names, fuel_names
        )
        self._fair_share_fuel_expected = self._default_tuple_dict_array(
            port_names, fuel_names
        )
        self._allocation_fuel_existing = self._default_tuple_dict_float(
            port_names, fuel_names
        )

        self._total_energy = self._default_array()
        self._fuel_expenses = self._default_array()

        self._remedial_expenses = self._default_array()
        self._flexibility_expenses = self._default_array()

        self._shore_power_capacity = self._default_array()
        self._shore_power_limit_port = self._default_list_array(port_count)

        self._fuel_cost_flow = self._default_array()

        self._asset_charter_npv = self._default_array()
        self._capex_npv = self._default_array()
        self._asset_charter_rate = self._default_array()
        self._freight_rate = self._default_array()
        self._technology_charter_rate = self._default_array()
        self._tied_capital = self._default_list_array(self._length)

    def reset_expected_bunkering(self) -> None:
        self._reset_dict_array(self._bunker_mass_expected)

        self._total_energy = self._default_array()
        self._fuel_expenses = self._default_array()
        self._remedial_expenses = self._default_array()
        self._flexibility_expenses = self._default_array()

    def reset_bunker_mass_existing(self) -> None:
        self._reset_dict_float(self._bunker_mass_existing)

    def reset_spend_energy(self) -> None:
        self._reset_dict_float(self._spend_energy)

    def reset_allocation_fuel_existing(self) -> None:
        self._reset_dict_float(self._allocation_fuel_existing)

    def set_voyages(self, idx: int, voyages: float) -> None:
        self._voyages[idx:] = voyages

    def set_cargo_miles(self, idx: int, cargo_miles: float) -> None:
        self._cargo_miles[idx:] = cargo_miles

    def set_cargo_miles_leg(self, idx: int, cargo_miles: Iterable[float]) -> None:
        _set_forward(self._cargo_miles_leg, idx, cargo_miles)

    def set_cargo_miles_leg_nominal(
        self, idx: int, cargo_miles: Iterable[float]
    ) -> None:
        _set_forward(self._cargo_miles_leg_nominal, idx, cargo_miles)

    def set_speed_mean(self, speed: float) -> None:
        self._speed_mean = speed

    def set_speed_anchor_reference(self, speed: float) -> None:
        self._speed_anchor_reference = speed

    def set_speed_anchor_optimal(self, speed: float) -> None:
        self._speed_anchor_optimal = speed

    def set_speeds_condition(self, idx: int, speeds: Iterable[float]) -> None:
        for i, speed in enumerate(speeds):
            self._speeds_condition[i][idx] = speed

    def set_time_sea_condition(self, idx: int, times: Iterable[float]) -> None:
        _set_forward(self._time_sea_condition, idx, times)

    def set_time_port(self, idx: int, times: Iterable[float]) -> None:
        _set_forward(self._time_port, idx, times)

    def set_raw_energy_sea_condition(
        self, idx: int, energy: Mapping[EnergyDemandID, Iterable[float]]
    ) -> None:
        _set_forward_per_key(self._raw_energy_sea_condition, idx, energy)

    def set_raw_energy_port(
        self, idx: int, energy: Mapping[EnergyDemandID, Iterable[float]]
    ) -> None:
        _set_forward_per_key(self._raw_energy_port, idx, energy)

    def set_operational_energy_sea_condition(
        self, idx: int, energy: Mapping[EnergyDemandID, Iterable[float]]
    ) -> None:
        _set_forward_per_key(self._operational_energy_sea_condition, idx, energy)

    def set_operational_energy_sea_leg(
        self, idx: int, energy: Mapping[EnergyDemandID, Iterable[FloatLike]]
    ) -> None:
        _set_forward_per_key(self._operational_energy_sea_leg, idx, energy)

    def set_operational_energy_port(
        self, idx: int, energy: Mapping[EnergyDemandID, Iterable[float]]
    ) -> None:
        _set_forward_per_key(self._operational_energy_port, idx, energy)

    def set_operational_saving_fraction_sea(
        self, fractions: Mapping[EnergyDemandID, float]
    ) -> None:
        self._operational_saving_fraction_sea.update(fractions)

    def set_operational_saving_fraction_port(
        self, fractions: Mapping[EnergyDemandID, float]
    ) -> None:
        self._operational_saving_fraction_port.update(fractions)

    def set_energy_sea_condition(
        self, idx: int, energy: Mapping[EnergyDemandID, Iterable[float]]
    ) -> None:
        _set_forward_per_key(self._energy_sea_condition, idx, energy)

    def set_energy_sea_leg(
        self, idx: int, energy: Mapping[EnergyDemandID, Iterable[FloatLike]]
    ) -> None:
        _set_forward_per_key(self._energy_sea_leg, idx, energy)

    def set_energy_port(
        self, idx: int, energy: Mapping[EnergyDemandID, Iterable[float]]
    ) -> None:
        _set_forward_per_key(self._energy_port, idx, energy)

    def set_energy_conservation_pi_sea(
        self, energy_id: EnergyDemandID, leg: int, idx: int, pi: float
    ) -> None:
        self._energy_conservation_pi_sea[energy_id][leg][idx] = pi

    def set_energy_conservation_pi_port(
        self, energy_id: EnergyDemandID, port: int, idx: int, pi: float
    ) -> None:
        self._energy_conservation_pi_port[energy_id][port][idx] = pi

    def set_energy_conservation_rhs_sea(
        self, energy_id: EnergyDemandID, leg: int, idx: int, rhs: float
    ) -> None:
        self._energy_conservation_rhs_sea[energy_id][leg][idx] = rhs

    def set_energy_conservation_rhs_port(
        self, energy_id: EnergyDemandID, port: int, idx: int, rhs: float
    ) -> None:
        self._energy_conservation_rhs_port[energy_id][port][idx] = rhs

    def set_effective_lhv(
        self, converter_name: str, fuel_name: str, lhv: float
    ) -> None:
        self._effective_lhv[converter_name, fuel_name] = lhv

    def set_ttw_consumption(
        self, converter_name: str, fuel_name: str, emission_name: str, ttw: float
    ) -> None:
        self._ttw_consumption[converter_name, fuel_name, emission_name] = ttw

    def set_ttw_slip(
        self, converter_name: str, fuel_name: str, emission_name: str, ttw: float
    ) -> None:
        self._ttw_slip[converter_name, fuel_name, emission_name] = ttw

    def set_mean_effective_lhv(self, fuel_name: str, lhv: float) -> None:
        self._mean_effective_lhv[fuel_name] = lhv

    def set_mean_ttw_consumption(
        self, fuel_name: str, emission_name: str, ttw: float
    ) -> None:
        self._mean_ttw_consumption[fuel_name, emission_name] = ttw

    def set_mean_ttw_slip(self, fuel_name: str, emission_name: str, ttw: float) -> None:
        self._mean_ttw_slip[fuel_name, emission_name] = ttw

    def add_bunker_mass_expected(
        self, port_name: str, fuel_name: str, idx: int, mass: float
    ) -> None:
        self._bunker_mass_expected[port_name, fuel_name][idx] += mass

    def add_bunker_mass_existing(
        self, port_name: str, fuel_name: str, mass: float
    ) -> None:
        self._bunker_mass_existing[port_name, fuel_name] += mass

    def add_spend_energy(self, converter_name: str, energy: float) -> None:
        self._spend_energy[converter_name] += energy

    def set_potential_fuel_type_demand(
        self, idx: int, demand: Mapping[tuple[str, FuelTypeID], FloatLike]
    ) -> None:
        for key, value in demand.items():
            self._potential_fuel_type_demand[key][idx:] = value

    def set_fair_share_fuel_existing(
        self, port_name: str, fuel_name: str, share: float
    ) -> None:
        self._fair_share_fuel_existing[port_name, fuel_name] = share

    def set_fair_share_fuel_expected(
        self, port_name: str, fuel_name: str, idx: int, share: FloatArray
    ) -> None:
        self._fair_share_fuel_expected[port_name, fuel_name][idx:] = share

    def set_allocation_fuel_existing(
        self, port_name: str, fuel_name: str, allocation: float
    ) -> None:
        self._allocation_fuel_existing[port_name, fuel_name] = allocation

    def add_total_energy(self, idx: int, energy: float) -> None:
        self._total_energy[idx] += energy

    def add_fuel_expenses(self, idx: int, expenses: float) -> None:
        self._fuel_expenses[idx] += expenses

    def add_remedial_expenses(self, idx: int, expenses: float) -> None:
        self._remedial_expenses[idx] += expenses

    def add_flexibility_expenses(self, idx: int, expenses: FloatArray) -> None:
        self._flexibility_expenses[idx:] += expenses

    def set_shore_power_capacity(self, idx: int, capacity: float) -> None:
        self._shore_power_capacity[idx:] = capacity

    def set_shore_power_limit_port(
        self, idx: int, limits: Iterable[FloatArray]
    ) -> None:
        _set_forward(self._shore_power_limit_port, idx, limits)

    def set_fuel_cost_flow(self, flow: FloatArray) -> None:
        self._fuel_cost_flow = flow

    def set_asset_charter_npv(self, idx: int, npv: float) -> None:
        self._asset_charter_npv[idx] = npv

    def set_capex_npv(self, idx: int, npv: float) -> None:
        self._capex_npv[idx] = npv

    def set_asset_charter_rate(self, idx: int, rate: float) -> None:
        self._asset_charter_rate[idx] = rate

    def set_freight_rate(self, idx: int, rate: float) -> None:
        self._freight_rate[idx] = rate

    def set_technology_charter_rate(self, idx: int, rate: float) -> None:
        self._technology_charter_rate[idx] = rate

    def set_tied_capital(self, idx: int, capital: FloatArray) -> None:
        self._tied_capital[idx] = capital

    def get_voyages(self, idx: int) -> float:
        voyages: float = self._voyages[idx]
        return voyages

    @overload
    def get_cargo_miles(self, idx: int) -> float: ...

    @overload
    def get_cargo_miles(self, idx: slice = ...) -> FloatArray: ...

    def get_cargo_miles(self, idx: Index = np.s_[:]) -> FloatLike:
        return self._cargo_miles[idx]

    def get_cargo_miles_leg(self, idx: slice) -> list[FloatArray]:
        return slice_list(self._cargo_miles_leg, idx)

    def get_cargo_miles_leg_nominal(self, idx: slice) -> list[FloatArray]:
        return slice_list(self._cargo_miles_leg_nominal, idx)

    def get_speed_mean(self) -> float:
        return self._speed_mean

    def get_speed_anchor_reference(self) -> float:
        return self._speed_anchor_reference

    def get_speed_anchor_optimal(self) -> float:
        return self._speed_anchor_optimal

    def get_speeds_condition(self, idx: int) -> list[float]:
        return slice_list(self._speeds_condition, idx)

    @overload
    def get_time_sea_condition(self, idx: int) -> list[float]: ...

    @overload
    def get_time_sea_condition(self, idx: slice) -> list[FloatArray]: ...

    def get_time_sea_condition(self, idx: Index) -> Sequence[FloatLike]:
        return slice_list(self._time_sea_condition, idx)

    @overload
    def get_time_port(self, idx: int) -> list[float]: ...

    @overload
    def get_time_port(self, idx: slice) -> list[FloatArray]: ...

    def get_time_port(self, idx: Index) -> Sequence[FloatLike]:
        return slice_list(self._time_port, idx)

    def get_raw_energy_sea_condition(
        self, idx: int
    ) -> dict[EnergyDemandID, list[float]]:
        return slice_dict_list(self._raw_energy_sea_condition, idx)

    def get_raw_energy_port(self, idx: int) -> dict[EnergyDemandID, list[float]]:
        return slice_dict_list(self._raw_energy_port, idx)

    @overload
    def get_operational_energy_sea_condition(
        self, idx: int
    ) -> dict[EnergyDemandID, list[float]]: ...

    @overload
    def get_operational_energy_sea_condition(
        self, idx: slice
    ) -> dict[EnergyDemandID, list[FloatArray]]: ...

    def get_operational_energy_sea_condition(
        self, idx: Index
    ) -> Mapping[EnergyDemandID, Sequence[FloatLike]]:
        return slice_dict_list(self._operational_energy_sea_condition, idx)

    def get_operational_energy_sea_leg(
        self, idx: slice
    ) -> dict[EnergyDemandID, list[FloatArray]]:
        return slice_dict_list(self._operational_energy_sea_leg, idx)

    @overload
    def get_operational_energy_port(
        self, idx: int
    ) -> dict[EnergyDemandID, list[float]]: ...

    @overload
    def get_operational_energy_port(
        self, idx: slice
    ) -> dict[EnergyDemandID, list[FloatArray]]: ...

    def get_operational_energy_port(
        self, idx: Index
    ) -> Mapping[EnergyDemandID, Sequence[FloatLike]]:
        return slice_dict_list(self._operational_energy_port, idx)

    def get_operational_saving_fraction_sea(self) -> dict[EnergyDemandID, float]:
        return self._operational_saving_fraction_sea

    def get_operational_saving_fraction_port(self) -> dict[EnergyDemandID, float]:
        return self._operational_saving_fraction_port

    def get_energy_sea_condition(self, idx: int) -> dict[EnergyDemandID, list[float]]:
        return slice_dict_list(self._energy_sea_condition, idx)

    def get_energy_sea_leg(self, idx: int) -> dict[EnergyDemandID, list[float]]:
        return slice_dict_list(self._energy_sea_leg, idx)

    @overload
    def get_energy_port(self, idx: int) -> dict[EnergyDemandID, list[float]]: ...

    @overload
    def get_energy_port(self, idx: slice) -> dict[EnergyDemandID, list[FloatArray]]: ...

    def get_energy_port(
        self, idx: Index
    ) -> Mapping[EnergyDemandID, Sequence[FloatLike]]:
        return slice_dict_list(self._energy_port, idx)

    def get_energy_conservation_pi_sea(self) -> dict[EnergyDemandID, list[FloatArray]]:
        return self._energy_conservation_pi_sea

    def get_energy_conservation_pi_port(self) -> dict[EnergyDemandID, list[FloatArray]]:
        return self._energy_conservation_pi_port

    def get_energy_conservation_rhs_sea(self) -> dict[EnergyDemandID, list[FloatArray]]:
        return self._energy_conservation_rhs_sea

    def get_energy_conservation_rhs_port(
        self,
    ) -> dict[EnergyDemandID, list[FloatArray]]:
        return self._energy_conservation_rhs_port

    def get_belief_pi_sea_technology(self) -> dict[EnergyDemandID, list[FloatArray]]:
        return self._belief_pi_sea_technology

    def get_belief_pi_port_technology(self) -> dict[EnergyDemandID, list[FloatArray]]:
        return self._belief_pi_port_technology

    def get_belief_pi_sea_speed(self) -> dict[EnergyDemandID, list[FloatArray]]:
        return self._belief_pi_sea_speed

    def get_belief_pi_port_speed(self) -> dict[EnergyDemandID, list[FloatArray]]:
        return self._belief_pi_port_speed

    def get_effective_lhv(self, converter_name: str, fuel_name: str) -> float:
        return self._effective_lhv[converter_name, fuel_name]

    def get_ttw_consumption(
        self, converter_name: str, fuel_name: str, emission_name: str
    ) -> float:
        return self._ttw_consumption[converter_name, fuel_name, emission_name]

    def get_ttw_slip(
        self, converter_name: str, fuel_name: str, emission_name: str
    ) -> float:
        return self._ttw_slip[converter_name, fuel_name, emission_name]

    def get_mean_effective_lhv(self, fuel_name: str) -> float:
        return self._mean_effective_lhv[fuel_name]

    def get_mean_ttw_consumption(self, fuel_name: str, emission_name: str) -> float:
        return self._mean_ttw_consumption[fuel_name, emission_name]

    def get_mean_ttw_slip(self, fuel_name: str, emission_name: str) -> float:
        return self._mean_ttw_slip[fuel_name, emission_name]

    @overload
    def get_bunker_mass_expected(
        self, port_name: str, fuel_name: str, idx: int
    ) -> float: ...

    @overload
    def get_bunker_mass_expected(
        self, port_name: str, fuel_name: str, idx: slice
    ) -> FloatArray: ...

    def get_bunker_mass_expected(
        self, port_name: str, fuel_name: str, idx: Index
    ) -> FloatLike:
        return self._bunker_mass_expected[port_name, fuel_name][idx]

    def get_bunker_mass_existing(self, port_name: str, fuel_name: str) -> float:
        return self._bunker_mass_existing[port_name, fuel_name]

    def get_spend_energy(self, converter_name: str) -> float:
        return self._spend_energy[converter_name]

    @overload
    def get_potential_fuel_type_demand(
        self, port_name: str, fuel_type: FuelTypeID, idx: int
    ) -> float: ...

    @overload
    def get_potential_fuel_type_demand(
        self, port_name: str, fuel_type: FuelTypeID, idx: slice
    ) -> FloatArray: ...

    def get_potential_fuel_type_demand(
        self, port_name: str, fuel_type: FuelTypeID, idx: Index
    ) -> FloatLike:
        return self._potential_fuel_type_demand[port_name, fuel_type][idx]

    def get_fair_share_fuel_existing(self, port_name: str, fuel_name: str) -> float:
        return self._fair_share_fuel_existing[port_name, fuel_name]

    def get_fair_share_fuel_expected(
        self, port_name: str, fuel_name: str, idx: int
    ) -> float:
        share: float = self._fair_share_fuel_expected[port_name, fuel_name][idx]
        return share

    def get_allocation_fuel_existing(self, port_name: str, fuel_name: str) -> float:
        return self._allocation_fuel_existing[port_name, fuel_name]

    def get_total_energy(self, idx: int) -> float:
        energy: float = self._total_energy[idx]
        return energy

    @overload
    def get_fuel_expenses(self, idx: int) -> float: ...

    @overload
    def get_fuel_expenses(self, idx: slice) -> FloatArray: ...

    def get_fuel_expenses(self, idx: Index) -> FloatLike:
        return self._fuel_expenses[idx]

    @overload
    def get_remedial_expenses(self, idx: int) -> float: ...

    @overload
    def get_remedial_expenses(self, idx: slice) -> FloatArray: ...

    def get_remedial_expenses(self, idx: Index) -> FloatLike:
        return self._remedial_expenses[idx]

    @overload
    def get_flexibility_expenses(self, idx: int) -> float: ...

    @overload
    def get_flexibility_expenses(self, idx: slice) -> FloatArray: ...

    def get_flexibility_expenses(self, idx: Index) -> FloatLike:
        return self._flexibility_expenses[idx]

    def get_shore_power_capacity(self, idx: slice) -> FloatArray:
        return self._shore_power_capacity[idx]

    def get_shore_power_limit_port(self, idx: int) -> list[float]:
        return slice_list(self._shore_power_limit_port, idx)

    def get_fuel_cost_flow(self) -> FloatArray:
        return self._fuel_cost_flow

    def get_asset_charter_npv(self, idx: int) -> float:
        npv: float = self._asset_charter_npv[idx]
        return npv

    def get_capex_npv(self, idx: int) -> float:
        npv: float = self._capex_npv[idx]
        return npv

    def get_asset_charter_rate(self, idx: int) -> float:
        rate: float = self._asset_charter_rate[idx]
        return rate

    def get_freight_rate(self, idx: int) -> float:
        rate: float = self._freight_rate[idx]
        return rate

    def get_technology_charter_rate(self, idx: int) -> float:
        rate: float = self._technology_charter_rate[idx]
        return rate

    def get_tied_capital(self, idx: int) -> FloatArray:
        return self._tied_capital[idx]


def _set_forward(
    paths: list[FloatArray], idx: int, values: Iterable[FloatLike]
) -> None:
    for i, value in enumerate(values):
        paths[i][idx:] = value


def _set_forward_per_key[K](
    paths: dict[K, list[FloatArray]], idx: int, values: Mapping[K, Iterable[FloatLike]]
) -> None:
    for key, value in values.items():
        _set_forward(paths[key], idx, value)
