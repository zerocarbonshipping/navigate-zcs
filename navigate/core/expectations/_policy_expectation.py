# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The emission-coefficient storage shared by the levy and regulation expectations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.expectations._expectation import _Expectation

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.util.types_ import FloatArray, FloatLike, Index


class _PolicyExpectation(_Expectation):
    """Well-to-tank, tank-to-wake and combined emission coefficients of a policy."""

    def __init__(self) -> None:
        super().__init__()

        self._global_warming_potential: dict[str, float] = {}

        # for levy the key is:       (port_name, fuel_name, emission_name)
        # for regulation the key is: (vessel_name, fuel_name, emission_name)
        self._expected_wtt: dict[tuple[str, ...], FloatArray] = {}
        self._existing_wtt: dict[tuple[str, ...], FloatArray] = {}

        # for levy the key is:       (vessel_name, fuel_name, emission_name)
        # for regulation the key is: (converter_name, fuel_name, emission_name)
        self._ttw_consumption: dict[tuple[str, ...], FloatArray] = {}
        self._ttw_slip: dict[tuple[str, ...], FloatArray] = {}

        # for levy the key is:       (vessel_name, port_name, fuel_name)
        # for regulation the key is: (vessel_name, converter_name, fuel_name)
        self._expected_coefficient: dict[tuple[str, ...], FloatArray] = {}
        self._existing_coefficient: dict[tuple[str, ...], FloatArray] = {}

    def _initialize_policy_expectation(self, emission_names: Iterable[str]) -> None:

        self._global_warming_potential = self._default_dict_float(emission_names)

    def set_global_warming_potential(
        self, emission_name: str, global_warming_potential: float
    ) -> None:
        self._global_warming_potential[emission_name] = global_warming_potential

    def set_expected_wtt(self, idx: int, key: tuple[str, ...], wtt: FloatLike) -> None:
        self._expected_wtt.setdefault(key, self._default_array())
        self._expected_wtt[key][idx:] = wtt

    def set_existing_wtt(self, idx: int, key: tuple[str, ...], wtt: FloatLike) -> None:
        self._existing_wtt.setdefault(key, self._default_array())
        self._existing_wtt[key][idx:] = wtt

    def set_ttw_consumption(
        self, idx: int, key: tuple[str, ...], ttw: FloatLike
    ) -> None:
        self._ttw_consumption.setdefault(key, self._default_array())
        self._ttw_consumption[key][idx:] = ttw

    def set_ttw_slip(self, idx: int, key: tuple[str, ...], ttw: FloatLike) -> None:
        self._ttw_slip.setdefault(key, self._default_array())
        self._ttw_slip[key][idx:] = ttw

    def set_expected_coefficient(
        self, idx: int, key: tuple[str, ...], coefficient: FloatLike
    ) -> None:
        self._expected_coefficient.setdefault(key, self._default_array())
        self._expected_coefficient[key][idx:] = coefficient

    def set_existing_coefficient(
        self, idx: int, key: tuple[str, ...], coefficient: FloatLike
    ) -> None:
        self._existing_coefficient.setdefault(key, self._default_array())
        self._existing_coefficient[key][idx:] = coefficient

    def get_global_warming_potential(self, emission_name: str) -> float:
        return self._global_warming_potential[emission_name]

    def get_expected_wtt(self, key: tuple[str, ...], idx: Index) -> FloatLike:

        if key in self._expected_wtt:
            expected_wtt: FloatLike = self._expected_wtt[key][idx]
        else:
            expected_wtt = 0.0

        return expected_wtt

    def get_existing_wtt(self, key: tuple[str, ...], idx: Index) -> FloatLike:

        if key in self._existing_wtt:
            existing_wtt: FloatLike = self._existing_wtt[key][idx]
        else:
            existing_wtt = 0.0

        return existing_wtt

    def get_ttw_consumption(self, key: tuple[str, ...], idx: Index) -> FloatLike:

        if key in self._ttw_consumption:
            ttw_consumption: FloatLike = self._ttw_consumption[key][idx]
        else:
            ttw_consumption = 0.0

        return ttw_consumption

    def get_ttw_slip(self, key: tuple[str, ...], idx: Index) -> FloatLike:

        ttw_slip = self._ttw_slip[key][idx] if key in self._ttw_slip else 0.0

        return ttw_slip

    def get_expected_coefficient(self, key: tuple[str, ...], idx: int) -> float:

        if key in self._expected_coefficient:
            coefficient: float = self._expected_coefficient[key][idx]
        else:
            coefficient = 0.0

        return coefficient

    def get_existing_coefficient(self, key: tuple[str, ...], idx: int) -> float:

        if key in self._existing_coefficient:
            coefficient: float = self._existing_coefficient[key][idx]
        else:
            coefficient = 0.0

        return coefficient
