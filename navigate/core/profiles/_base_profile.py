# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import itertools
from collections.abc import Callable, Iterable

import numpy as np

from navigate.core.misc import EMPTY_FLOAT
from navigate.util import (
    add_dicts,
    divide_dicts,
    divide_nonzero,
    multiply_dicts,
    slice_dict,
)


class _BaseProfile:
    """
    This class is used exclusively for sub-classing.
    """
    def __init__(self):

        self._timeline: np.ndarray = EMPTY_FLOAT

    def _initialize_base(self, timeline: np.ndarray) -> None:
        self._timeline = timeline

    def get_length(self, idx: int | slice = np.s_[:]) -> int:
        return self._timeline[idx].size

    def get_shape(self, idx: int | slice = np.s_[:]) -> tuple[int, ...]:
        return self.get_length(idx),

    def _allocate_list(self) -> list[None]:
        return [None for _ in range(self.get_length())]

    def _default_array(self, default: float | bool | None = None,
                       idx: int | slice = np.s_[:]) -> np.ndarray:

        if default is None:
            return np.zeros(self.get_shape(idx))
        else:
            if isinstance(default, bool):
                dtype = bool
            else:
                dtype = np.float64

            return np.full(self.get_shape(idx), default, dtype=dtype)

    def _default_dict(self, keys: Iterable[str], default: float | bool | None = None,
                      idx: int | slice = np.s_[:]) -> dict[str, np.ndarray]:
        return {key: self._default_array(default, idx) for key in keys}

    def _default_tuple_dict(self, keys1: Iterable[str], keys2: Iterable[str],
                            default: float | bool | None = None,
                            idx: int | slice = np.s_[:]) -> dict[tuple[str, str], np.ndarray]:
        return self._default_dict(itertools.product(keys1, keys2), default, idx)

    def _reset_array(self, array: np.ndarray, idx: int, default: float | None = None) -> None:
        array[idx:] = self._default_array(default, np.s_[idx:])

    def _reset_dict(self, dict_: dict[str, np.ndarray], idx: int,
                    default: float | None = None) -> None:
        for array in dict_.values():
            array[idx:] = self._default_array(default, np.s_[idx:])

    def _reset_tuple_dict(self, dict_: dict[tuple[str, str], np.ndarray], idx: int,
                          default: float | None = None) -> None:
        self._reset_dict(dict_, idx, default)

    def _to_cumulative(self, value: np.ndarray) -> np.ndarray:
        return np.insert(np.cumsum(value[:-1] * np.diff(self._timeline)), 0, 0.)

    def _to_cumulative_dict(self, values: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        return {key: self._to_cumulative(value) for key, value in values.items()}

    def _to_cumulative_any(self, value: np.ndarray | dict[str, np.ndarray]) -> np.ndarray | dict[str, np.ndarray]:
        if isinstance(value, dict):
            return self._to_cumulative_dict(value)
        else:
            return self._to_cumulative(value)

    def _to_cumulative_fraction(self, numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
        return divide_nonzero(self._to_cumulative(numerator), self._to_cumulative(denominator))

    @staticmethod
    def _extract_add_dicts(dict1: dict[str, np.ndarray], *dicts: dict[str, np.ndarray],
                           key: str | None = None,
                           idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        if key is not None:
            return dict1[key][idx] + sum(d[key][idx] for d in dicts)
        else:
            return slice_dict(add_dicts(dict1, *dicts), idx)

    @staticmethod
    def _extract_multiply_dict(result: dict[str, np.ndarray], mult_dict: dict[str, float],
                               key: str | None = None,
                               idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        if key is not None:
            return result[key][idx] * mult_dict[key]
        else:
            return multiply_dicts(slice_dict(result, idx), mult_dict)

    @staticmethod
    def _extract_divide_dict(result: dict[str, np.ndarray], div_dict: dict[str, float],
                             key: str | None = None,
                             idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        if key is not None:
            return result[key][idx] / div_dict[key]
        else:
            return divide_dicts(slice_dict(result, idx), div_dict)

    @staticmethod
    def _extract_method_dict(method: Callable, result: dict[str, np.ndarray],
                             key: str | None = None,
                             idx: int | slice = np.s_[:]) -> np.ndarray | dict[str, np.ndarray]:
        if key is not None:
            return method(result[key], idx)
        else:
            return {key: method(result[key], idx) for key in result}

    @staticmethod
    def _extract_nested_dict(result: dict[str, dict[str, np.ndarray]],
                             key: str | None = None,
                             idx: int | slice = np.s_[:]) -> dict[str, np.ndarray] | dict[str, dict[str, np.ndarray]]:
        if key is not None:
            return slice_dict(result[key], idx)
        else:
            return {key: slice_dict(value, idx) for key, value in result.items()}

    @staticmethod
    def _extract_multiply_nested_dict(result: dict[str, dict[str, np.ndarray]],
                                      mult_dict: dict[str, float],
                                      key: str | None = None,
                                      idx: int | slice = np.s_[:]) -> dict[str, np.ndarray] | dict[str, dict[str, np.ndarray]]:
        if key:
            return multiply_dicts(slice_dict(result[key], idx), mult_dict)
        else:
            return {key: multiply_dicts(slice_dict(value, idx), mult_dict) for key, value in result.items()}

    @staticmethod
    def _get_total_method(method: Callable, idx: int | slice = np.s_[:]) -> np.ndarray:
        return np.add.reduce(list(method(idx=idx).values()))
