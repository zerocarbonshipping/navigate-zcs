# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.profiles._infrastructure_aggregate_profile import (
    _InfrastructureAggregateProfile,
)
from navigate.util import extract_from_dict, extract_from_tuple_dict

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.util.types_ import FloatArray


class PortProfile(_InfrastructureAggregateProfile):
    def __init__(self):
        super().__init__()

        # constants
        self._global_warming_potential: dict[str, float] = {}

        # bunkering
        self._bunkering_allowed: dict[
            str, np.ndarray
        ] = {}  # bool, is bunkering allowed

        # results
        self._bunker_price: dict[str, np.ndarray] = {}  # fuel price paid for bunkering
        self._bunker_wtt: dict[
            tuple[str, str], np.ndarray
        ] = {}  # WTT emissions from fuel

    def initialize(
        self,
        timeline: np.ndarray,
        emissions: dict[str, Emission],
        fuels: dict[str, Fuel],
        emissions_lifetime: float,
    ) -> None:
        """
        Initialize the port profile's storage arrays and lookups.

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
        self._bunker_wtt = self._default_tuple_dict(fuels, emissions)

        for emission_name, emission in emissions.items():
            self._global_warming_potential[emission_name] = (
                emission.global_warming_potential.get(emissions_lifetime)
            )

    def _to_emission_intensity(
        self, emission: FloatArray, fuel_name: str
    ) -> FloatArray:
        # emissions are converted from ton to g (10^6) and energy from GJ to
        # MJ (10^3), so dividing by 10^3
        return emission / (self._lower_heating_value[fuel_name] / 1e3)

    def _to_intensity(
        self, emissions: dict[tuple[str, str], FloatArray]
    ) -> dict[tuple[str, str], FloatArray]:
        return {
            (fuel_name, emission_name): self._to_emission_intensity(emission, fuel_name)
            for (fuel_name, emission_name), emission in emissions.items()
        }

    def set_bunker_price(self, idx: int, fuel_name: str, price: float) -> None:
        self._bunker_price[fuel_name][idx] = price

    def set_bunker_wtt(
        self, idx: int, fuel_name: str, emission_name: str, wtt: float
    ) -> None:
        self._bunker_wtt[(fuel_name, emission_name)][idx] = wtt

    def set_bunkering_allowed(self, idx: int, fuel_name: str, available: bool) -> None:
        self._bunkering_allowed[fuel_name][idx] = available

    def get_bunkering_allowed(
        self, fuel_name: str | None = None, idx: int | slice = np.s_[:]
    ) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._bunkering_allowed, fuel_name, idx)

    def get_bunker_price(
        self, fuel_name: str | None = None, idx: int | slice = np.s_[:]
    ) -> np.ndarray | dict[str, np.ndarray]:
        return extract_from_dict(self._bunker_price, fuel_name, idx)

    def get_bunker_intensity_price(self) -> dict[str, FloatArray]:
        return {
            fuel_name: price / self._lower_heating_value[fuel_name]
            for fuel_name, price in self._bunker_price.items()
        }

    def get_bunker_wtt(
        self,
        fuel_name: str | None = None,
        emission_name: str | None = None,
        idx: int | slice = np.s_[:],
    ) -> np.ndarray | dict[tuple[str, str], np.ndarray]:
        return extract_from_tuple_dict(
            self._bunker_wtt, key1=fuel_name, key2=emission_name, idx=idx
        )

    def get_equivalent_bunker_wtt(self) -> dict[tuple[str, str], FloatArray]:
        return self._equivalent(self._bunker_wtt, self._global_warming_potential)

    def get_total_equivalent_bunker_wtt(
        self, idx: int | slice = np.s_[:]
    ) -> np.ndarray:
        return self._get_total_method(self.get_equivalent_bunker_wtt, idx)

    def get_bunker_intensity_wtt(self) -> dict[tuple[str, str], FloatArray]:
        return self._to_intensity(self._bunker_wtt)

    def get_bunker_intensity_equivalent_wtt(
        self,
    ) -> dict[tuple[str, str], FloatArray]:
        return self._to_intensity(self.get_equivalent_bunker_wtt())

    def get_bunker_intensity_total_equivalent_wtt(self) -> dict[str, FloatArray]:
        equivalent = self.get_equivalent_bunker_wtt()
        return {
            fuel_name: self._to_emission_intensity(
                np.add.reduce(
                    [
                        equivalent[(fuel_name, emission_name)]
                        for emission_name in self._global_warming_potential
                    ]
                ),
                fuel_name,
            )
            for fuel_name in self._lower_heating_value
        }
