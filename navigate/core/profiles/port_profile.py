# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.profiles._fuel_infrastructure_profile import (
    _FuelInfrastructureProfile,
)

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.util.types_ import BoolArray, FloatArray


class PortProfile(_FuelInfrastructureProfile):
    def __init__(self):
        super().__init__()

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
        self._initialize_fuel_emission(emissions, emissions_lifetime)
        self._initialize_fuel_infrastructure(fuels)

        self._bunkering_allowed = self._default_bool_dict(fuels, default=False)

        self._bunker_price = self._default_dict(fuels)
        self._bunker_wtt = self._default_tuple_dict(fuels, emissions)

    def _to_heating_value_intensity(
        self, emissions: dict[tuple[str, str], FloatArray]
    ) -> dict[tuple[str, str], FloatArray]:
        return {
            (fuel_name, emission_name): self._convert_to_intensity(
                emission, self._lower_heating_value[fuel_name]
            )
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

    def get_bunkering_allowed(self) -> dict[str, BoolArray]:
        return dict(self._bunkering_allowed)

    def get_bunker_price(self) -> dict[str, FloatArray]:
        return dict(self._bunker_price)

    def get_bunker_intensity_price(self) -> dict[str, FloatArray]:
        return {
            fuel_name: price / self._lower_heating_value[fuel_name]
            for fuel_name, price in self._bunker_price.items()
        }

    def get_bunker_wtt(self) -> dict[tuple[str, str], FloatArray]:
        return dict(self._bunker_wtt)

    def get_equivalent_bunker_wtt(self) -> dict[tuple[str, str], FloatArray]:
        return self._equivalent(self._bunker_wtt)

    def get_total_equivalent_bunker_wtt(self) -> FloatArray:
        return self._sum_values(self.get_equivalent_bunker_wtt())

    def get_bunker_intensity_wtt(self) -> dict[tuple[str, str], FloatArray]:
        return self._to_heating_value_intensity(self._bunker_wtt)

    def get_bunker_intensity_equivalent_wtt(
        self,
    ) -> dict[tuple[str, str], FloatArray]:
        return self._to_heating_value_intensity(self.get_equivalent_bunker_wtt())

    def get_bunker_intensity_total_equivalent_wtt(self) -> dict[str, FloatArray]:
        equivalent = self.get_equivalent_bunker_wtt()
        return {
            fuel_name: self._convert_to_intensity(
                np.add.reduce(
                    [
                        equivalent[(fuel_name, emission_name)]
                        for emission_name in self._global_warming_potential
                    ]
                ),
                self._lower_heating_value[fuel_name],
            )
            for fuel_name in self._lower_heating_value
        }
