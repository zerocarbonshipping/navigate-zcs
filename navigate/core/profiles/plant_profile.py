# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.initial_values import EMPTY_NAN
from navigate.core.profiles._emission_base_profile import _EmissionBaseProfile
from navigate.util import multiply_dicts

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.util.types_ import FloatArray


class PlantProfile(_EmissionBaseProfile):
    def __init__(self):
        super().__init__()

        # constants
        self._lower_heating_value: float = 0.0  # lower heating value of fuel

        # costs
        self._investment_cost: np.ndarray = (
            EMPTY_NAN  # expected cost at time of investment, USD/ton
        )
        self._instantaneous_cost: np.ndarray = EMPTY_NAN  # instantaneous cost, USD/ton

        # emissions
        self._investment_wtt: dict[
            str, np.ndarray
        ] = {}  # expected WTT at time of investment, ton emission/ton fuel
        self._instantaneous_wtt: dict[
            str, np.ndarray
        ] = {}  # instantaneous WTT at a given time, ton emission/ton fuel

    def initialize(
        self,
        timeline: np.ndarray,
        fuel: Fuel,
        emissions: dict[str, Emission],
        emissions_lifetime: float,
    ) -> None:
        """
        Initialize the plant profile's storage arrays and lookups.

        Parameters
        ----------
        timeline : np.ndarray
            Simulation timeline in years.
        fuel : Fuel
            The fuel produced by the plant.
        emissions : dict[Emission]
            All emissions in the simulation.
        emissions_lifetime : float
            GWP lifetime.
        """
        self._initialize_base(timeline)

        self._investment_cost = self._default_array(default=np.nan)
        self._instantaneous_cost = self._default_array(default=np.nan)

        self._investment_wtt = self._default_dict(emissions, default=np.nan)
        self._instantaneous_wtt = self._default_dict(emissions, default=np.nan)

        self._lower_heating_value = fuel.lower_heating_value.get()

        self._initialize_global_warming_potential(emissions, emissions_lifetime)

    def _intensity_equivalent(
        self, wtt: dict[str, FloatArray]
    ) -> dict[str, FloatArray]:
        equivalent = multiply_dicts(wtt, self._global_warming_potential)
        return {
            emission_name: self._convert_to_intensity(value, self._lower_heating_value)
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
        return self._investment_cost / self._lower_heating_value

    def get_instantaneous_intensity_cost(self) -> FloatArray:
        return self._instantaneous_cost / self._lower_heating_value

    def get_instantaneous_cost(self) -> FloatArray:
        return self._instantaneous_cost

    def get_equivalent_investment_wtt(self) -> dict[str, FloatArray]:
        return multiply_dicts(self._investment_wtt, self._global_warming_potential)

    def get_total_equivalent_investment_wtt(self) -> FloatArray:
        return self._sum_values(self.get_equivalent_investment_wtt())

    def get_intensity_equivalent_investment_wtt(self) -> dict[str, FloatArray]:
        return self._intensity_equivalent(self._investment_wtt)

    def get_intensity_total_equivalent_investment_wtt(self) -> FloatArray:
        return self._sum_values(self.get_intensity_equivalent_investment_wtt())

    def get_equivalent_instantaneous_wtt(self) -> dict[str, FloatArray]:
        return multiply_dicts(self._instantaneous_wtt, self._global_warming_potential)

    def get_total_equivalent_instantaneous_wtt(self) -> FloatArray:
        return self._sum_values(self.get_equivalent_instantaneous_wtt())

    def get_intensity_equivalent_instantaneous_wtt(self) -> dict[str, FloatArray]:
        return self._intensity_equivalent(self._instantaneous_wtt)

    def get_intensity_total_equivalent_instantaneous_wtt(self) -> FloatArray:
        return self._sum_values(self.get_intensity_equivalent_instantaneous_wtt())
