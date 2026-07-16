# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import itertools
from collections.abc import Iterable
from typing import Any

import numpy as np


class _Expectation:
    def __init__(self):

        self._length: int = 0

    def _initialize_expectation(self, length: int) -> None:
        self._length = length

    def get_length(self, idx: int | None = None) -> int:
        if idx is None:
            return self._length
        else:
            return self._length - idx

    def get_shape(self, idx: int | None = None) -> tuple[int, ...]:
        return self.get_length(idx),

    def _allocate_list(self) -> list[None]:
        return [None for _ in range(self._length)]

    def _default_float(self, default: float | None = None) -> float:

        if default is None:
            return 0.
        else:
            return default

    def _default_array(self, default: float | bool | None = None) -> np.ndarray:

        if default is None:
            return np.zeros(self.get_shape())
        else:
            if isinstance(default, bool):
                dtype = bool
            else:
                dtype = np.float64

            return np.full(self.get_shape(), default, dtype=dtype)

    def _default_2D_array(self, n: int, default: float | bool | None = None) -> np.ndarray:
        shape = (n, self._length)

        if default is None:
            return np.zeros(shape)
        else:
            if isinstance(default, bool):
                dtype = bool
            else:
                dtype = np.float64

            return np.full(shape, default, dtype=dtype)

    def _default_list_float(self, n: int, default: float | None = None) -> list[float]:
        return [self._default_float(default) for _ in range(n)]

    def _default_list_array(self, n: int, default: float | bool | None = None) -> list[np.ndarray]:
        return [self._default_array(default) for _ in range(n)]

    def _default_dict_float(self, keys: Iterable[Any], default: float | None = None) -> dict[Any, float]:
        return {key: self._default_float(default) for key in keys}

    def _default_dict_array(self, keys: Iterable[Any], default: float | bool | None = None) -> dict[Any, np.ndarray]:
        return {key: self._default_array(default) for key in keys}

    def _default_tuple_dict_float(self, keys1: Iterable[str], keys2: Iterable[str],
                                  default: float | None = None) -> dict[tuple[str, str], float]:
        return self._default_dict_float(itertools.product(keys1, keys2), default)

    def _default_tuple_dict_array(self, keys1: Iterable[str], keys2: Iterable[str],
                                  default: float | bool | None = None) -> dict[tuple[str, str], np.ndarray]:
        return self._default_dict_array(itertools.product(keys1, keys2), default)

    def _default_dict_list_array(self, keys: Iterable[Any], length: int,
                                 default: float | bool | None = None) -> dict[Any, list[np.ndarray]]:
        return {key: self._default_list_array(length, default) for key in keys}

    def _reset_array(self, array: np.ndarray, default: float | None = None) -> None:
        array[:] = self._default_array(default)

    def _reset_array_partial(self, array: np.ndarray, idx: int, default: float | None = None) -> None:
        array[idx:] = self._default_array(default)[np.s_[idx:]]

    def _reset_list_array(self, list_: list[np.ndarray], default: float | None = None) -> None:
        for array in list_:
            array[:] = self._default_array(default)

    def _reset_list_array_partial(self, list_: list[np.ndarray], idx: int, default: float | None = None) -> None:
        s = np.s_[idx:]
        for array in list_:
            array[s] = self._default_array(default)[s]

    def _reset_dict_float(self, dict_: dict[Any, float], default: float | None = None) -> None:
        for key in dict_:
            dict_[key] = self._default_float(default)

    def _reset_dict_array(self, dict_: dict[Any, np.ndarray], default: float | None = None) -> None:
        for array in dict_.values():
            array[:] = self._default_array(default)

    def _reset_dict_array_partial(self, dict_: dict[Any, np.ndarray], idx: int,
                                  default: float | None = None) -> None:
        s = np.s_[idx:]
        for array in dict_.values():
            array[s] = self._default_array(default)[s]
