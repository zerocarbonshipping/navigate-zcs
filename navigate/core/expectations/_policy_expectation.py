# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Iterable

import numpy as np

from navigate.core.expectations._expectation import _Expectation


class _PolicyExpectation(_Expectation):
    def __init__(self):
        super().__init__()

        self._global_warming_potential: dict[str, float] = {}     # dict[emission_name: float], global warming potential

        # for levy the key is:       (port_name, fuel_name, emission_name)
        # for regulation the key is: (vessel_name, fuel_name, emission_name)
        self._expected_WTT: dict[tuple[str, ...], np.ndarray] = {}
        self._existing_WTT: dict[tuple[str, ...], np.ndarray] = {}

        # for levy the key is:       (vessel_name, fuel_name, emission_name)
        # for regulation the key is: (converter_name, fuel_name, emission_name)
        self._TTW_consumption: dict[tuple[str, ...], np.ndarray] = {}
        self._TTW_slip: dict[tuple[str, ...], np.ndarray] = {}

        # for levy the key is:       (vessel_name, port_name, fuel_name)
        # for regulation the key is: (vessel_name, converter_name, fuel_name)
        self._expected_coefficient: dict[tuple[str, ...], np.ndarray] = {}
        self._existing_coefficient: dict[tuple[str, ...], np.ndarray] = {}

    def _initialize_policy_expectation(self, emission_names: Iterable[str]) -> None:

        self._global_warming_potential = self._default_dict_float(emission_names)

    def set_global_warming_potential(self, emission_name: str, global_warming_potential: float) -> None:
        self._global_warming_potential[emission_name] = global_warming_potential

    def set_expected_WTT(self, idx: int, key: tuple[str, ...], WTT: float | np.ndarray) -> None:
        self._expected_WTT.setdefault(key, self._default_array())
        self._expected_WTT[key][idx:] = WTT

    def set_existing_WTT(self, idx: int, key: tuple[str, ...], WTT: float | np.ndarray) -> None:
        self._existing_WTT.setdefault(key, self._default_array())
        self._existing_WTT[key][idx:] = WTT

    def set_TTW_consumption(self, idx: int, key: tuple[str, ...], TTW: float | np.ndarray) -> None:
        self._TTW_consumption.setdefault(key, self._default_array())
        self._TTW_consumption[key][idx:] = TTW

    def set_TTW_slip(self, idx: int, key: tuple[str, ...], TTW: float | np.ndarray) -> None:
        self._TTW_slip.setdefault(key, self._default_array())
        self._TTW_slip[key][idx:] = TTW

    def set_expected_coefficient(self, idx: int, key: tuple[str, ...], coefficient: float | np.ndarray) -> None:
        self._expected_coefficient.setdefault(key, self._default_array())
        self._expected_coefficient[key][idx:] = coefficient

    def set_existing_coefficient(self, idx: int, key: tuple[str, ...], coefficient: float | np.ndarray) -> None:
        self._existing_coefficient.setdefault(key, self._default_array())
        self._existing_coefficient[key][idx:] = coefficient

    def get_global_warming_potential(self, emission_name: str) -> float:
        return self._global_warming_potential[emission_name]

    def get_expected_WTT(self, key: tuple[str, ...], idx: int) -> float:

        if key in self._expected_WTT:
            return self._expected_WTT[key][idx]
        else:
            return 0.

    def get_existing_WTT(self, key: tuple[str, ...], idx: int) -> float:

        if key in self._existing_WTT:
            return self._existing_WTT[key][idx]
        else:
            return 0.

    def get_TTW_consumption(self, key: tuple[str, ...], idx: int) -> float:

        if key in self._TTW_consumption:
            return self._TTW_consumption[key][idx]
        else:
            return 0.

    def get_TTW_slip(self, key: tuple[str, ...], idx: int) -> float:

        if key in self._TTW_slip:
            return self._TTW_slip[key][idx]
        else:
            return 0.

    def get_expected_coefficient(self, key: tuple[str, ...], idx: int) -> float:

        if key in self._expected_coefficient:
            return self._expected_coefficient[key][idx]
        else:
            return 0.

    def get_existing_coefficient(self, key: tuple[str, ...], idx: int) -> float:

        if key in self._existing_coefficient:
            return self._existing_coefficient[key][idx]
        else:
            return 0.
