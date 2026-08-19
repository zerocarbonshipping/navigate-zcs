# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.misc import EMPTY_NAN
from navigate.core.profiles._base_profile import _BaseProfile
from navigate.util import divide_nonzero

if TYPE_CHECKING:
    from navigate.fuel import Emission, Fuel


class PlantProfile(_BaseProfile):
    def __init__(self):
        super().__init__()

        # constants
        self._GWP: dict[str, float] = {}                      # global warming potential of emission
        self._lower_heating_value: float = 0.0                  # lower heating value of fuel

        # costs
        self._investment_cost: np.ndarray = EMPTY_NAN        # expected cost at time of investment, USD/ton
        self._instantaneous_cost: np.ndarray = EMPTY_NAN     # instantaneous cost, USD/ton

        # emissions
        self._investment_WTT: dict[str, np.ndarray] = {}       # expected WTT at time of investment, ton emission/ton fuel
        self._instantaneous_WTT: dict[str, np.ndarray] = {}    # instantaneous WTT at a given time, ton emission/ton fuel

    def initialize(self, timeline: np.ndarray, fuel: Fuel, emissions: dict[str, Emission],
                   emissions_lifetime: float) -> None:
        """

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

        self._investment_WTT = self._default_dict(emissions, default=np.nan)
        self._instantaneous_WTT = self._default_dict(emissions, default=np.nan)

        self._lower_heating_value = fuel.lower_heating_value.get()

        for emission_name, emission in emissions.items():
            self._GWP[emission_name] = emission.global_warming_potential.get(emissions_lifetime)

    @staticmethod
    def _convert_to_intensity(emission: np.ndarray, energy: np.ndarray) -> np.ndarray:
        # emissions are converted from ton to g (10^6)
        # and energy is converted from GJ to MJ (10^3),
        # so dividing by 10^3
        return divide_nonzero(emission, (energy / 1e3))

    def _get_intensity_equivalent(self, data: dict[str, np.ndarray], emission_name: str | None = None,
                                  idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        if emission_name is not None:
            return self._convert_to_intensity(self._extract_multiply_dict(data, self._GWP, key=emission_name, idx=idx),
                                              self._lower_heating_value)
        return {key: self._get_intensity_equivalent(data, key, idx) for key in data}

    def set_investment_cost(self, idx: int, investment_cost: float) -> None:
        self._investment_cost[idx] = investment_cost

    def set_instantaneous_cost(self, idx: int, instantaneous_cost: float) -> None:
        self._instantaneous_cost[idx] = instantaneous_cost

    def set_investment_WTT(self, idx: int, emission_name: str, investment_WTT: float) -> None:
        self._investment_WTT[emission_name][idx] = investment_WTT

    def set_instantaneous_WTT(self, idx: int, emission_name: str, instantaneous_WTT: float) -> None:
        self._instantaneous_WTT[emission_name][idx] = instantaneous_WTT

    def get_investment_cost(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._investment_cost[idx]

    def get_investment_intensity_cost(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._investment_cost[idx] / self._lower_heating_value

    def get_instantaneous_intensity_cost(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._instantaneous_cost[idx] / self._lower_heating_value

    def get_instantaneous_cost(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._instantaneous_cost[idx]

    def get_equivalent_investment_WTT(self, emission_name: str | None = None,
                                      idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._extract_multiply_dict(self._investment_WTT, self._GWP, key=emission_name, idx=idx)

    def get_total_equivalent_investment_WTT(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._get_total_method(self.get_equivalent_investment_WTT, idx)

    def get_intensity_equivalent_investment_WTT(self, emission_name: str | None = None,
                                                idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._get_intensity_equivalent(self._investment_WTT, emission_name, idx)

    def get_intensity_total_equivalent_investment_WTT(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._get_total_method(self.get_intensity_equivalent_investment_WTT, idx)

    def get_equivalent_instantaneous_WTT(self, emission_name: str | None = None,
                                         idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._extract_multiply_dict(self._instantaneous_WTT, self._GWP, key=emission_name, idx=idx)

    def get_total_equivalent_instantaneous_WTT(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._get_total_method(self.get_equivalent_instantaneous_WTT, idx)

    def get_intensity_equivalent_instantaneous_WTT(self, emission_name: str | None = None,
                                                   idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        return self._get_intensity_equivalent(self._instantaneous_WTT, emission_name, idx)

    def get_intensity_total_equivalent_instantaneous_WTT(self, idx: int | slice = np.s_[:]) -> np.ndarray:
        return self._get_total_method(self.get_intensity_equivalent_instantaneous_WTT, idx)
