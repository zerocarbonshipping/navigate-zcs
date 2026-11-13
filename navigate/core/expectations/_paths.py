# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Lists and dicts of paths, read and written at a time index through ``at``.

``paths.at[idx]`` gives the value of every path at a step, ``paths.at[idx:]`` every
path from a step on, and assigning to either writes the paths in the same shape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

from navigate.util.types_ import FloatArray

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from navigate.util.types_ import FloatLike, Index, Step, Steps


class PathList(list[FloatArray]):
    """Paths in a fixed order, such as one per leg of a route."""

    @property
    def at(self) -> _ListAt:
        return _ListAt(self)


class PathDict[K](dict[K, FloatArray]):
    """Paths by key."""

    @property
    def at(self) -> _DictAt[K]:
        return _DictAt(self)


class PathListDict[K](dict[K, PathList]):
    """Lists of paths by key."""

    @property
    def at(self) -> _ListDictAt[K]:
        return _ListDictAt(self)


class _ListAt:
    def __init__(self, paths: PathList) -> None:
        self._paths = paths

    @overload
    def __getitem__(self, idx: Step) -> list[float]: ...

    @overload
    def __getitem__(self, idx: Steps) -> list[FloatArray]: ...

    def __getitem__(self, idx: Index) -> Sequence[FloatLike]:
        return [path[idx] for path in self._paths]

    def __setitem__(self, idx: Index, values: Iterable[FloatLike]) -> None:
        for i, value in enumerate(values):
            self._paths[i][idx] = value


class _DictAt[K]:
    def __init__(self, paths: PathDict[K]) -> None:
        self._paths = paths

    @overload
    def __getitem__(self, idx: Step) -> dict[K, float]: ...

    @overload
    def __getitem__(self, idx: Steps) -> dict[K, FloatArray]: ...

    def __getitem__(self, idx: Index) -> Mapping[K, FloatLike]:
        return {key: path[idx] for key, path in self._paths.items()}

    def __setitem__(self, idx: Index, values: Mapping[K, FloatLike]) -> None:
        for key, value in values.items():
            self._paths[key][idx] = value


class _ListDictAt[K]:
    def __init__(self, paths: PathListDict[K]) -> None:
        self._paths = paths

    @overload
    def __getitem__(self, idx: Step) -> dict[K, list[float]]: ...

    @overload
    def __getitem__(self, idx: Steps) -> dict[K, list[FloatArray]]: ...

    def __getitem__(self, idx: Index) -> Mapping[K, Sequence[FloatLike]]:
        return {key: paths.at[idx] for key, paths in self._paths.items()}

    def __setitem__(self, idx: Index, values: Mapping[K, Iterable[FloatLike]]) -> None:
        for key, value in values.items():
            self._paths[key].at[idx] = value
