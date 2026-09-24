# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""PlantProfile, the output storage the Plant node reports its results from."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.initial_values import EMPTY_NAN
from navigate.core.profiles._fuel_emission_profile import _FuelEmissionProfile

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.util.types_ import FloatArray


class PlantProfile(_FuelEmissionProfile):
    """Production cost and well-to-tank emissions of the fuel one plant makes."""

    def __init__(self) -> None:
        super().__init__()

        # constants
        self._fuel_name: str = ""  # name of the fuel the plant produces

        # cost of the fuel produced, USD/ton
        self._investment_cost: FloatArray = EMPTY_NAN  # expected at investment
        self._instantaneous_cost: FloatArray = EMPTY_NAN  # at the current time

        # well-to-tank emissions, ton emission/ton fuel
        self._investment_wtt: dict[str, FloatArray] = {}  # expected at investment
        self._instantaneous_wtt: dict[str, FloatArray] = {}  # at the current time

    def initialize(
        self,
        timeline: FloatArray,
        emissions: dict[str, Emission],
        fuels: dict[str, Fuel],
        fuel_name: str,
        emissions_lifetime: float,
    ) -> None:
        """
        Initialize the plant profile's storage arrays and lookups.

        Parameters
        ----------
        timeline
            Simulation timeline, in years.
        emissions
            All emissions in the simulation.
        fuels
            All fuels in the simulation.
        fuel_name
            Name of the fuel the plant produces.
        emissions_lifetime
            Lifetime the global warming potentials are read at, in years.
        """
        self._initialize_base(timeline)
        self._initialize_fuel_base(fuels)
        self._initialize_fuel_emission(emissions, emissions_lifetime)

        self._investment_cost = self._default_array(default=np.nan)
        self._instantaneous_cost = self._default_array(default=np.nan)

        self._investment_wtt = self._default_dict(emissions, default=np.nan)
        self._instantaneous_wtt = self._default_dict(emissions, default=np.nan)

        self._fuel_name = fuel_name

    def _intensity_equivalent(
        self, wtt: dict[str, FloatArray]
    ) -> dict[str, FloatArray]:
        equivalent = self._equivalent_by_emission(wtt)
        return {
            emission_name: self._convert_to_intensity(
                value, self._lower_heating_value[self._fuel_name]
            )
            for emission_name, value in equivalent.items()
        }

    def set_investment_cost(self, idx: int, investment_cost: float) -> None:
        self._investment_cost[idx] = investment_cost

    def set_instantaneous_cost(self, idx: int, instantaneous_cost: float) -> None:
        self._instantaneous_cost[idx] = instantaneous_cost

    def set_investment_wtt(
        self, idx: int, emission_name: str, investment_wtt: float
    ) -> None:
        self._investment_wtt[emission_name][idx] = investment_wtt

    def set_instantaneous_wtt(
        self, idx: int, emission_name: str, instantaneous_wtt: float
    ) -> None:
        self._instantaneous_wtt[emission_name][idx] = instantaneous_wtt

    def get_investment_cost(self) -> FloatArray:
        return self._investment_cost

    def get_investment_intensity_cost(self) -> FloatArray:
        return self._investment_cost / self._lower_heating_value[self._fuel_name]

    def get_instantaneous_intensity_cost(self) -> FloatArray:
        return self._instantaneous_cost / self._lower_heating_value[self._fuel_name]

    def get_instantaneous_cost(self) -> FloatArray:
        return self._instantaneous_cost

    def get_equivalent_investment_wtt(self) -> dict[str, FloatArray]:
        return self._equivalent_by_emission(self._investment_wtt)

    def get_total_equivalent_investment_wtt(self) -> FloatArray:
        return self._sum_values(self.get_equivalent_investment_wtt())

    def get_intensity_equivalent_investment_wtt(self) -> dict[str, FloatArray]:
        return self._intensity_equivalent(self._investment_wtt)

    def get_intensity_total_equivalent_investment_wtt(self) -> FloatArray:
        return self._sum_values(self.get_intensity_equivalent_investment_wtt())

    def get_equivalent_instantaneous_wtt(self) -> dict[str, FloatArray]:
        return self._equivalent_by_emission(self._instantaneous_wtt)

    def get_total_equivalent_instantaneous_wtt(self) -> FloatArray:
        return self._sum_values(self.get_equivalent_instantaneous_wtt())

    def get_intensity_equivalent_instantaneous_wtt(self) -> dict[str, FloatArray]:
        return self._intensity_equivalent(self._instantaneous_wtt)

    def get_intensity_total_equivalent_instantaneous_wtt(self) -> FloatArray:
        return self._sum_values(self.get_intensity_equivalent_instantaneous_wtt())
