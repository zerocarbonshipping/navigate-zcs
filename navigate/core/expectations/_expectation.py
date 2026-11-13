# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The storage every expectation class allocates: paths and plain values."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.expectations._paths import PathDict, PathList, PathListDict

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.util.types_ import FloatArray


class _Expectation:
    """The timeline's length and the storage an expectation allocates."""

    def __init__(self, length: int) -> None:
        self.length = length

    def _path(self, default: float = 0.0) -> FloatArray:
        return np.full(self.length, default, dtype=np.float64)

    def _paths[K](self, keys: Iterable[K], default: float = 0.0) -> PathDict[K]:
        return PathDict((key, self._path(default)) for key in keys)

    def _path_list(self, count: int, default: float = 0.0) -> PathList:
        return PathList(self._path(default) for _ in range(count))

    def _path_lists[K](
        self, keys: Iterable[K], count: int, default: float = 0.0
    ) -> PathListDict[K]:
        return PathListDict((key, self._path_list(count, default)) for key in keys)

    @staticmethod
    def _values[K](keys: Iterable[K], default: float = 0.0) -> dict[K, float]:
        return dict.fromkeys(keys, default)
