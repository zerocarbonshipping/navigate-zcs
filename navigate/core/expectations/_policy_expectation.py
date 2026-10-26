# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The emission-factor storage shared by the levy and regulation expectations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.expectations._expectation import _Expectation

if TYPE_CHECKING:
    from collections.abc import Collection

    from navigate.util.types_ import FloatArray, FloatLike, Index


class _PolicyExpectation[TtwKey: tuple[str, ...]](_Expectation):
    """Global warming potentials and WTT and TTW emission factors of a policy."""

    def __init__(self) -> None:
        super().__init__()

        self._global_warming_potential: dict[str, float]

        # keyed by (port_name, fuel_name, emission_name) under a levy and by
        # (vessel_name, fuel_name, emission_name) under a regulation
        self._wtt: dict[tuple[str, str, str], FloatArray] = {}

        # keyed by (vessel_name, fuel_name, emission_name) under a levy and by
        # (vessel_name, converter_name, fuel_name, emission_name) under a regulation
        self._ttw_consumption: dict[TtwKey, FloatArray] = {}
        self._ttw_slip: dict[TtwKey, FloatArray] = {}

    def _initialize_policy_expectation(self, emission_names: Collection[str]) -> None:
        self._global_warming_potential = self._default_dict_float(emission_names)

    def set_global_warming_potential(
        self, emission_name: str, potential: float
    ) -> None:
        self._global_warming_potential[emission_name] = potential

    def set_wtt(self, idx: int, key: tuple[str, str, str], wtt: FloatLike) -> None:
        self._wtt.setdefault(key, self._default_array())
        self._wtt[key][idx:] = wtt

    def set_ttw_consumption(self, idx: int, key: TtwKey, ttw: FloatLike) -> None:
        self._ttw_consumption.setdefault(key, self._default_array())
        self._ttw_consumption[key][idx:] = ttw

    def set_ttw_slip(self, idx: int, key: TtwKey, ttw: FloatLike) -> None:
        self._ttw_slip.setdefault(key, self._default_array())
        self._ttw_slip[key][idx:] = ttw

    def get_global_warming_potential(self, emission_name: str) -> float:
        return self._global_warming_potential[emission_name]

    def get_wtt(self, key: tuple[str, str, str], idx: Index) -> FloatLike:
        if key not in self._wtt:
            return 0.0

        return self._wtt[key][idx]

    def get_ttw_consumption(self, key: TtwKey, idx: Index) -> FloatLike:
        if key not in self._ttw_consumption:
            return 0.0

        return self._ttw_consumption[key][idx]

    def get_ttw_slip(self, key: TtwKey, idx: Index) -> FloatLike:
        if key not in self._ttw_slip:
            return 0.0

        return self._ttw_slip[key][idx]
