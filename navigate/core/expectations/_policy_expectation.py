# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The emission-factor storage shared by the levy and regulation expectations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.expectations._expectation import _Expectation

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.util.types_ import FloatArray, FloatLike, Index


class _PolicyExpectation(_Expectation):
    """Global warming potentials and WTT and TTW emission factors of a policy."""

    def __init__(self) -> None:
        super().__init__()

        self._global_warming_potential: dict[str, float]

        # levy key:       (port_name, fuel_name, emission_name)
        # regulation key: (vessel_name, fuel_name, emission_name)
        self._wtt: dict[tuple[str, ...], FloatArray] = {}

        # levy key:       (vessel_name, fuel_name, emission_name)
        # regulation key: (vessel_name, converter_name, fuel_name, emission_name)
        self._ttw_consumption: dict[tuple[str, ...], FloatArray] = {}
        self._ttw_slip: dict[tuple[str, ...], FloatArray] = {}

    def _initialize_policy_expectation(self, emission_names: Iterable[str]) -> None:

        self._global_warming_potential = self._default_dict_float(emission_names)

    def set_global_warming_potential(
        self, emission_name: str, global_warming_potential: float
    ) -> None:
        self._global_warming_potential[emission_name] = global_warming_potential

    def set_wtt(self, idx: int, key: tuple[str, ...], wtt: FloatLike) -> None:
        self._wtt.setdefault(key, self._default_array())
        self._wtt[key][idx:] = wtt

    def set_ttw_consumption(
        self, idx: int, key: tuple[str, ...], ttw: FloatLike
    ) -> None:
        self._ttw_consumption.setdefault(key, self._default_array())
        self._ttw_consumption[key][idx:] = ttw

    def set_ttw_slip(self, idx: int, key: tuple[str, ...], ttw: FloatLike) -> None:
        self._ttw_slip.setdefault(key, self._default_array())
        self._ttw_slip[key][idx:] = ttw

    def get_global_warming_potential(self, emission_name: str) -> float:
        return self._global_warming_potential[emission_name]

    def get_wtt(self, key: tuple[str, ...], idx: Index) -> FloatLike:

        if key in self._wtt:
            return self._wtt[key][idx]

        return 0.0

    def get_ttw_consumption(self, key: tuple[str, ...], idx: Index) -> FloatLike:

        if key in self._ttw_consumption:
            return self._ttw_consumption[key][idx]

        return 0.0

    def get_ttw_slip(self, key: tuple[str, ...], idx: Index) -> FloatLike:

        if key in self._ttw_slip:
            return self._ttw_slip[key][idx]

        return 0.0
