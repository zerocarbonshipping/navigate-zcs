# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.profiles._infrastructure_aggregate_profile import _InfrastructureAggregateProfile
from navigate.util import extract_from_dict, extract_from_tuple_dict

if TYPE_CHECKING:
    from navigate.fuel import Emission, Fuel


class PortProfile(_InfrastructureAggregateProfile):
    def __init__(self):
        super().__init__()

        # constants
        self._GWP: dict[str, float] = {}

        # bunkering
        self._bunkering_allowed: dict[str, np.ndarray] = {}    # bool, is bunkering allowed

        # results
        self._bunker_price: dict[str, np.ndarray] = {}      # fuel price paid for bunkering
        self._bunker_WTT: dict[tuple[str, str], np.ndarray] = {}  # WTT emissions from fuel

    def initialize(self, timeline: np.ndarray, emissions: dict[str, Emission],
                   fuels: dict[str, Fuel], emissions_lifetime: float) -> None:
        """

        Parameters
        ----------
        timeline : np.ndarray
            Simulation timeline in years.
        emissions : dict[Emission]
            All emissions in the model.
        fuels : dict[Fuel]
            All fuels in the simulation.
        emissions_lifetime : float
            GWP lifetime.
        """

        self._initialize_base(timeline)
        self._initialize_fuel_base(fuels)
        self._initialize_fuel_infrastructure(fuels)
        self._initialize_infrastructure_aggregate()

        self._bunkering_allowed = self._default_dict(fuels, default=False)

        self._bunker_price = self._default_dict(fuels)
        self._bunker_WTT = self._default_tuple_dict(fuels, emissions)

        for emission_name, emission in emissions.items():
            self._GWP[emission_name] = emission.global_warming_potential.get(emissions_lifetime)

    def _to_price_intensity(self, method: Callable, fuel_name: str | None = None,
                            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        if fuel_name is not None:

            if fuel_name in self._lower_heating_value:
                return method(fuel_name, idx) / self._lower_heating_value[fuel_name]
            else:
                return self._default_array(default=np.nan)[idx]

        else:

            return {fuel_name: self._to_price_intensity(method, fuel_name, idx)
                    for fuel_name in self._bunkering_allowed}

    def _to_emission_intensity(self, method: Callable, fuel_name: str | None = None,
                               emission_name: str | None = None,
                               idx: int | slice = np.s_[:]) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        if fuel_name is not None:

            if fuel_name in self._lower_heating_value:
                # emissions are converted from ton to g (10^6)
                # and energy is converted from GJ to MJ (10^3),
                # so dividing by 10^3
                return method(fuel_name, emission_name, idx) / (self._lower_heating_value[fuel_name] / 1e3)
            else:
                return self._default_array(default=np.nan)[idx]

        else:
            return {(fuel_name, emission_name): self._to_emission_intensity(method, fuel_name, emission_name, idx)
                    for fuel_name in self._bunkering_allowed for emission_name in self._GWP}

    def _to_emission_intensity_total(self, method: Callable, fuel_name: str | None = None,
                                     idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        if fuel_name is not None:

            if fuel_name in self._lower_heating_value:
                # emissions are converted from ton to g (10^6)
                # and energy is converted from GJ to MJ (10^3),
                # so dividing by 10^3
                return method(fuel_name, idx) / (self._lower_heating_value[fuel_name] / 1e3)
            else:
                return self._default_array(default=np.nan)[idx]

        else:

            return {fuel_name: self._to_emission_intensity_total(method, fuel_name, idx)
                    for fuel_name in self._bunkering_allowed}

    def set_bunker_price(self, idx: int, fuel_name: str, price: float) -> None:
        self._bunker_price[fuel_name][idx] = price

    def set_bunker_WTT(self, idx: int, fuel_name: str, emission_name: str, WTT: float) -> None:
        self._bunker_WTT[(fuel_name, emission_name)][idx] = WTT

    def set_bunkering_allowed(self, idx: int, fuel_name: str, available: bool) -> None:
        self._bunkering_allowed[fuel_name][idx] = available

    def get_bunkering_allowed(
            self, fuel_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._bunkering_allowed, fuel_name, idx)

    def get_bunker_price(self, fuel_name: str | None = None, idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._bunker_price, fuel_name, idx)

    def get_bunker_intensity_price(
            self, fuel_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._to_price_intensity(self.get_bunker_price, fuel_name, idx)

    def get_bunker_WTT(
            self, fuel_name: str | None = None,
            emission_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        return extract_from_tuple_dict(self._bunker_WTT, key1=fuel_name, key2=emission_name, idx=idx)

    def get_equivalent_bunker_WTT(
            self, fuel_name: str | None = None,
            emission_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        if emission_name is not None:
            return extract_from_tuple_dict(self._bunker_WTT, key1=fuel_name, key2=emission_name, idx=idx,
                                           transform=lambda x: x * self._GWP[emission_name])
        if fuel_name is not None:
            return {(fuel_name, en): self.get_equivalent_bunker_WTT(fuel_name, en, idx)
                    for en in self._GWP}
        return {key: self.get_equivalent_bunker_WTT(*key, idx) for key in self._bunker_WTT}

    def get_total_equivalent_bunker_WTT(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._get_total_method(self.get_equivalent_bunker_WTT, idx)

    def get_bunker_intensity_WTT(
            self, fuel_name: str | None = None,
            emission_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        return self._to_emission_intensity(self.get_bunker_WTT, fuel_name, emission_name, idx)

    def get_bunker_intensity_equivalent_WTT(
            self, fuel_name: str | None = None,
            emission_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        return self._to_emission_intensity(self.get_equivalent_bunker_WTT, fuel_name, emission_name, idx)

    def get_bunker_intensity_total_equivalent_WTT(
            self, fuel_name: str | None = None,
            idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        if fuel_name is not None:
            equiv = self.get_equivalent_bunker_WTT(fuel_name=fuel_name, idx=idx)
            total = np.add.reduce(list(equiv.values()))
            if fuel_name in self._lower_heating_value:
                return total / (self._lower_heating_value[fuel_name] / 1e3)
            return self._default_array(default=np.nan)[idx]
        return {fn: self.get_bunker_intensity_total_equivalent_WTT(fn, idx)
                for fn in self._bunkering_allowed}
