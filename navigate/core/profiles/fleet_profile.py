# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import FuelTypeID
from navigate.core.initial_values import EMPTY_FLOAT, EMPTY_NAN
from navigate.core.profiles._vessel_aggregate_profile import _VesselAggregateProfile

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel

from navigate.util import divide_nonzero, extract_from_dict, extract_from_tuple_dict


class FleetProfile(_VesselAggregateProfile):
    def __init__(self):
        super().__init__()

        self._trade: np.ndarray = EMPTY_FLOAT
        self._cargo_miles: np.ndarray = EMPTY_FLOAT    # transport work performed, cargo-miles/year

        self._existing_vessels: dict[str, np.ndarray] = {}
        self._scrap: dict[str, np.ndarray] = {}
        self._newbuilds: dict[str, np.ndarray] = {}
        self._fuel_conversions: dict[tuple[str, str], np.ndarray] = {}
        self._technology_uptake: dict[tuple[str, str], np.ndarray] = {}
        self._newbuild_technology_uptake: dict[tuple[str, str], np.ndarray] = {}
        self._retrofit_technology_uptake: dict[tuple[str, str], np.ndarray] = {}

        self._fuel_type_supply: dict[FuelTypeID, np.ndarray] = {}

        # speed
        self._reference_speed: np.ndarray = EMPTY_NAN   # average reference speed, knots
        self._minimum_speed: np.ndarray = EMPTY_NAN     # average minimum possible speed, knots
        self._maximum_speed: np.ndarray = EMPTY_NAN     # average maximum possible speed, knots
        self._actual_speed: np.ndarray = EMPTY_NAN      # average actual speed, knots
        self._optimal_speed: np.ndarray = EMPTY_NAN     # average optimal speed, knots
        self._lowest_speed: np.ndarray = EMPTY_NAN      # lowest actual speed, knots
        self._highest_speed: np.ndarray = EMPTY_NAN     # highest actual speed, knots

        self._instantaneous_freight_rate: np.ndarray = EMPTY_NAN   # USD/cargo-mile

    def initialize(self, timeline: np.ndarray,
                   vessel_names: list[str], technology_names: list[str],
                   fuels: dict[str, Fuel], emissions: dict[str, Emission], emissions_lifetime: float,
                   regulation_names: list[str] = (), levy_names: list[str] = ()) -> None:
        """
        Parameters
        ----------
        timeline :
            Simulation timeline in years.
        vessel_names :
            List of vessel names.
        technology_names :
            List of technology names.
        fuels :
            All fuels in the simulation.
        emissions :
            All emissions in the simulation.
        emissions_lifetime :
            Emissions lifetime used for calculating GWP.
        """

        self._initialize_base(timeline)
        self._initialize_fuel_base(fuels)
        self._initialize_fuel_consumer(fuels, emissions, emissions_lifetime, regulation_names, levy_names)
        self._initialize_vessel_aggregate()

        self._trade = self._default_array()
        self._cargo_miles = self._default_array()

        for vessel_name in vessel_names:

            self._existing_vessels[vessel_name] = self._default_array()
            self._scrap[vessel_name] = self._default_array()
            self._newbuilds[vessel_name] = self._default_array()

        self._fuel_conversions = self._default_tuple_dict(vessel_names, vessel_names)

        self._technology_uptake = self._default_tuple_dict(vessel_names, technology_names)
        self._newbuild_technology_uptake = self._default_tuple_dict(vessel_names, technology_names)
        self._retrofit_technology_uptake = self._default_tuple_dict(vessel_names, technology_names)

        self._fuel_type_supply = self._default_dict(FuelTypeID)

        self._reference_speed = self._default_array(default=np.nan)
        self._minimum_speed = self._default_array(default=np.nan)
        self._maximum_speed = self._default_array(default=np.nan)
        self._actual_speed = self._default_array(default=np.nan)
        self._optimal_speed = self._default_array(default=np.nan)
        self._lowest_speed = self._default_array(default=np.nan)
        self._highest_speed = self._default_array(default=np.nan)

        self._instantaneous_freight_rate = self._default_array(default=np.nan)

    def set_trade(self, idx: int, trade: float) -> None:
        self._trade[idx] = trade

    def set_cargo_miles(self, idx: int, cargo_miles: float) -> None:
        self._cargo_miles[idx] = cargo_miles

    def set_existing_vessels(self, idx: int, vessel_name: str, existing_vessels: float) -> None:
        self._existing_vessels[vessel_name][idx] = existing_vessels

    def add_scrap(self, vessel_name: str, idx: int, scrap: float) -> None:
        self._scrap[vessel_name][idx] += scrap

    def add_newbuilds(self, vessel_name: str, idx: int, newbuilds: float) -> None:
        self._newbuilds[vessel_name][idx] += newbuilds

    def add_fuel_conversions(self, vessel_name_from: str, vessel_name_to: str, idx: int, conversions: float) -> None:
        self._fuel_conversions[(vessel_name_from, vessel_name_to)][idx] += conversions

    def set_technology_uptake(self, vessel_name: str, technology_name: str, idx: int, uptake: float) -> None:
        self._technology_uptake[(vessel_name, technology_name)][idx] = uptake

    def set_newbuild_technology_uptake(self, vessel_name: str, technology_name: str, idx: int, uptake: float) -> None:
        self._newbuild_technology_uptake[(vessel_name, technology_name)][idx] = uptake

    def set_retrofit_technology_uptake(self, vessel_name: str, technology_name: str, idx: int, uptake: float) -> None:
        self._retrofit_technology_uptake[(vessel_name, technology_name)][idx] = uptake

    def add_fuel_type_supply(self, fuel_type: FuelTypeID, supply: float, idx: int | slice = np.s_[:]) -> None:
        self._fuel_type_supply[fuel_type][idx] += supply

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

    def set_instantaneous_freight_rate(self, idx: int, instantaneous_freight_rate: float) -> None:
        self._instantaneous_freight_rate[idx] = instantaneous_freight_rate

    def get_trade(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._trade[idx]

    def get_cargo_miles(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._cargo_miles[idx]

    def get_existing_vessels(
            self, vessel_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._existing_vessels, vessel_name, idx)

    def get_scrap(
            self, vessel_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._scrap, vessel_name, idx)

    def get_newbuilds(
            self, vessel_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._newbuilds, vessel_name, idx)

    def get_fuel_conversions(
            self, vessel_name_to: str | None = None,
            vessel_name_from: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        return extract_from_tuple_dict(self._fuel_conversions, vessel_name_to, vessel_name_from, idx)

    def get_technology_uptake(
            self, vessel_name: str | None = None,
            technology_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        return extract_from_tuple_dict(self._technology_uptake, vessel_name, technology_name, idx)

    def get_fleet_technology_uptake(
            self, technology_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        """
        Fleet-wide technology uptake: per-vessel uptake shares averaged with
        the existing vessel counts as weights (0 where the fleet is empty).

        Parameters
        ----------
        technology_name
            Technology to extract; all technologies as a dict when None.
        idx
            Time-step index or slice.
        """
        if technology_name is None:
            technology_names = dict.fromkeys(name for _, name in self._technology_uptake)
            return {name: self.get_fleet_technology_uptake(name, idx) for name in technology_names}

        shares = extract_from_tuple_dict(self._technology_uptake, key2=technology_name, idx=idx)
        if not shares:
            # no vessels carry the technology: zero uptake, timeline-shaped
            return np.zeros_like(self._trade[idx])

        values = np.array([shares[vessel_name] for vessel_name in shares])
        weights = np.array([self._existing_vessels[vessel_name][idx] for vessel_name in shares])

        return divide_nonzero((values * weights).sum(axis=0), weights.sum(axis=0))

    def get_newbuild_technology_uptake(
            self, vessel_name: str | None = None,
            technology_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        return extract_from_tuple_dict(self._newbuild_technology_uptake, vessel_name, technology_name, idx)

    def get_retrofit_technology_uptake(
            self, vessel_name: str | None = None,
            technology_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        return extract_from_tuple_dict(self._retrofit_technology_uptake, vessel_name, technology_name, idx)

    def get_fuel_type_supply(
            self, fuel_type: FuelTypeID | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[FuelTypeID, np.ndarray]:
        return extract_from_dict(self._fuel_type_supply, fuel_type, idx)

    def get_reference_speed(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._reference_speed[idx]

    def get_minimum_speed(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._minimum_speed[idx]

    def get_maximum_speed(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._maximum_speed[idx]

    def get_actual_speed(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._actual_speed[idx]

    def get_optimal_speed(self) -> np.ndarray:
        return self._optimal_speed

    def get_lowest_speed(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._lowest_speed[idx]

    def get_highest_speed(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._highest_speed[idx]

    def get_instantaneous_freight_rate(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._instantaneous_freight_rate[idx]
