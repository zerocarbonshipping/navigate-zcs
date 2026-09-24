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

        self._length: int = 0

    def _initialize_expectation(self, length: int) -> None:
        self._length = length

    def get_shape(self, start: int = 0) -> tuple[int]:
        return (self._length - start,)

    def _default_float(self, default: float | None = None) -> float:

        default_float = 0.0 if default is None else default

        return default_float

    def _default_array(self, default: float | None = None) -> FloatArray:

        if default is None:
            default_array = np.zeros(self.get_shape())
        else:
            default_array = np.full(self.get_shape(), default, dtype=np.float64)

        return default_array

    def _default_2d_array(self, n: int, default: float | None = None) -> FloatArray:
        shape = (n, self._length)

        if default is None:
            default_2d_array = np.zeros(shape)
        else:
            default_2d_array = np.full(shape, default, dtype=np.float64)

        return default_2d_array

    def _default_list_array(
        self, n: int, default: float | None = None
    ) -> list[FloatArray]:
        return [self._default_array(default) for _ in range(n)]

    def _default_dict_float[K](
        self, keys: Iterable[K], default: float | None = None
    ) -> dict[K, float]:
        return {key: self._default_float(default) for key in keys}

    def _default_dict_array[K](
        self, keys: Iterable[K], default: float | None = None
    ) -> dict[K, FloatArray]:
        return {key: self._default_array(default) for key in keys}

    def _default_tuple_dict_float(
        self, keys1: Iterable[str], keys2: Iterable[str], default: float | None = None
    ) -> dict[tuple[str, str], float]:
        return self._default_dict_float(itertools.product(keys1, keys2), default)

    def _default_tuple_dict_array(
        self, keys1: Iterable[str], keys2: Iterable[str], default: float | None = None
    ) -> dict[tuple[str, str], FloatArray]:
        return self._default_dict_array(itertools.product(keys1, keys2), default)

    def _default_dict_list_array[K](
        self, keys: Iterable[K], length: int, default: float | None = None
    ) -> dict[K, list[FloatArray]]:
        return {key: self._default_list_array(length, default) for key in keys}

    def _reset_dict_float[K](self, dict_: dict[K, float]) -> None:
        for key in dict_:
            dict_[key] = self._default_float()

    def _reset_dict_array_partial[K](
        self, dict_: dict[K, FloatArray], idx: int
    ) -> None:
        s = np.s_[idx:]
        for array in dict_.values():
            array[s] = self._default_array()[s]
