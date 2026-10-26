# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The timeline-shaped storage allocators every expectation class inherits."""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.util.types_ import FloatArray


class _Expectation:
    """Timeline length and the default-valued storage an expectation allocates."""

    def __init__(self) -> None:
        self._length: int

    def _initialize_expectation(self, length: int) -> None:
        self._length = length

    def get_shape(self, start: int = 0) -> tuple[int]:
        return (self._length - start,)

    def _default_array(self, default: float = 0.0) -> FloatArray:
        return np.full(self.get_shape(), default, dtype=np.float64)

    def _default_2d_array(self, count: int, default: float = 0.0) -> FloatArray:
        return np.full((count, self._length), default, dtype=np.float64)

    def _default_list_array(self, count: int, default: float = 0.0) -> list[FloatArray]:
        return [self._default_array(default) for _ in range(count)]

    def _default_dict_float[K](
        self, keys: Iterable[K], default: float = 0.0
    ) -> dict[K, float]:
        return dict.fromkeys(keys, default)

    def _default_dict_array[K](
        self, keys: Iterable[K], default: float = 0.0
    ) -> dict[K, FloatArray]:
        return {key: self._default_array(default) for key in keys}

    def _default_tuple_dict_float[K1, K2](
        self, keys1: Iterable[K1], keys2: Iterable[K2], default: float = 0.0
    ) -> dict[tuple[K1, K2], float]:
        return self._default_dict_float(itertools.product(keys1, keys2), default)

    def _default_tuple_dict_array[K1, K2](
        self, keys1: Iterable[K1], keys2: Iterable[K2], default: float = 0.0
    ) -> dict[tuple[K1, K2], FloatArray]:
        return self._default_dict_array(itertools.product(keys1, keys2), default)

    def _default_dict_list_array[K](
        self, keys: Iterable[K], count: int, default: float = 0.0
    ) -> dict[K, list[FloatArray]]:
        return {key: self._default_list_array(count, default) for key in keys}

    def _reset_dict_float[K](self, dict_: dict[K, float]) -> None:
        for key in dict_:
            dict_[key] = 0.0

    def _reset_dict_array[K](self, dict_: dict[K, FloatArray]) -> None:
        for key in dict_:
            dict_[key] = self._default_array()

    def _reset_dict_array_partial[K](
        self, dict_: dict[K, FloatArray], idx: int
    ) -> None:
        forward = np.s_[idx:]
        for array in dict_.values():
            array[forward] = 0.0
