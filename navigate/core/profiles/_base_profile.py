# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""_BaseProfile, the timeline and the storage builders every profile inherits."""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.initial_values import EMPTY_FLOAT
from navigate.util import divide_nonzero

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.util.types_ import BoolArray, FloatArray, FloatLike


class _BaseProfile:
    """Timeline-sized storage allocation and the aggregations every profile shares."""

    def __init__(self) -> None:
        self._timeline: FloatArray = EMPTY_FLOAT

    def _initialize_base(self, timeline: FloatArray) -> None:
        self._timeline = timeline

    def _default_array(self, default: float | None = None) -> FloatArray:
        if default is None:
            default_array = np.zeros(self._timeline.shape)
        else:
            default_array = np.full(self._timeline.shape, default, dtype=np.float64)

        return default_array

    def _default_bool_array(self, default: bool) -> BoolArray:
        return np.full(self._timeline.shape, default, dtype=bool)

    def _default_dict[K](
        self, keys: Iterable[K], default: float | None = None
    ) -> dict[K, FloatArray]:
        return {key: self._default_array(default) for key in keys}

    def _default_bool_dict[K](
        self, keys: Iterable[K], default: bool
    ) -> dict[K, BoolArray]:
        return {key: self._default_bool_array(default) for key in keys}

    def _default_tuple_dict[K1, K2](
        self,
        keys1: Iterable[K1],
        keys2: Iterable[K2],
        default: float | None = None,
    ) -> dict[tuple[K1, K2], FloatArray]:
        return self._default_dict(itertools.product(keys1, keys2), default)

    def _default_nested_dict[K1, K2](
        self,
        keys1: Iterable[K1],
        keys2: Iterable[K2],
        default: float | None = None,
    ) -> dict[K1, dict[K2, FloatArray]]:
        return {key: self._default_dict(keys2, default) for key in keys1}

    def _to_cumulative(self, value: FloatArray) -> FloatArray:
        return np.insert(np.cumsum(value[:-1] * np.diff(self._timeline)), 0, 0.0)

    def _to_cumulative_dict[K](
        self, values: dict[K, FloatArray]
    ) -> dict[K, FloatArray]:
        return {key: self._to_cumulative(value) for key, value in values.items()}

    @staticmethod
    def _sum_values[K](values: dict[K, FloatArray]) -> FloatArray:
        # an empty dict sums to 0.0 rather than raising: a fuel- or policy-free
        # model produces one
        return np.add.reduce(list(values.values()))

    @staticmethod
    def _convert_to_intensity(emission: FloatArray, energy: FloatLike) -> FloatArray:
        # emissions are converted from ton to g (10^6) and energy from GJ to
        # MJ (10^3), so dividing by 10^3
        return divide_nonzero(emission, energy / 1e3)
