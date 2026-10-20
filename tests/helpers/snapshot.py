# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Flatten a run's results into named arrays, and compare two such snapshots.

A snapshot holds every profile result: the global profile's and each node
profile's, one array per result, or per key for a result that is a mapping. It
is what the determinism test compares between two runs and what
tests/compare_results.py compares between two checkouts, so no deck needs a
report to be compared. It reads the results as the
profile fields navigate.core.profiles.result_names names where the installed
Navigate has it, and through the profile getters of an older checkout
otherwise, under the same names.
"""

from __future__ import annotations

import enum
import inspect
from functools import partial
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from navigate.core import SimulationResults

type Snapshot = dict[str, np.ndarray]

# Tolerances for comparing runs across installs. A maintenance change may
# reorder floating-point arithmetic, and LPs and cancellations amplify a
# last-digit change, most visibly in cells that are zero up to rounding. rtol
# bounds the relative drift, atol the near-zero cells; 1e-5 is negligible in
# every unit a profile carries - vessels, MW, USD, tonnes and fractions.
ROUNDING_RTOL = 1e-8
ROUNDING_ATOL = 1e-5

# The global profile's wall-clock timings, which differ between any two runs.
_TIMING_SUFFIX = "_time"

# per differing key, the cells a diff names before summarizing the rest
_CELLS_SHOWN = 3

_SEPARATOR = "/"


def _label(key: object) -> str:
    """Spell one key of a result's mapping as part of a snapshot name."""
    if isinstance(key, tuple):
        return "|".join(_label(part) for part in key)
    if isinstance(key, enum.Enum):
        return key.name
    return str(key)


def _getters(profile: object) -> list[str]:
    """Name the profile's public getters that take no argument."""
    names = []
    for name, member in inspect.getmembers(type(profile), inspect.isfunction):
        if not name.startswith("get_") or name.endswith(_TIMING_SUFFIX):
            continue
        parameters = list(inspect.signature(member).parameters.values())[1:]
        if all(p.default is not inspect.Parameter.empty for p in parameters):
            names.append(name)
    return names


def _readers(profile: Any) -> dict[str, Callable[[], object]]:
    """Map each result name of the profile to a reader of the result."""
    try:
        from navigate.core.profiles import result_names
    except ImportError:
        # an older checkout reads every result through a getter
        return {
            getter.removeprefix("get_"): getattr(profile, getter)
            for getter in _getters(profile)
        }

    return {
        name: partial(getattr, profile, name)
        for name in sorted(result_names(type(profile)))
        if not name.endswith(_TIMING_SUFFIX)
    }


def _add_profile(snap: Snapshot, prefix: str, profile: object) -> None:
    """Add every result of one profile under `prefix`."""
    for result, read in _readers(profile).items():
        value = read()
        name = f"{prefix}{_SEPARATOR}{result}"
        if isinstance(value, dict):
            for key, array in value.items():
                snap[f"{name}{_SEPARATOR}{_label(key)}"] = np.asarray(array)
        else:
            snap[name] = np.asarray(value)


def snapshot(results: SimulationResults) -> Snapshot:
    """
    Collect every profile result of a finished run.

    Parameters
    ----------
    results
        The run to snapshot.

    Returns
    -------
    Snapshot :
        One array per name ``<group>/<node>/<result>[/<key>]``; the global
        profile's names start with ``global``.
    """
    snap: Snapshot = {}
    _add_profile(snap, "global", results.profile)
    for group, nodes in vars(results.nodes).items():
        for name, node in nodes.items():
            profile = getattr(node, "profile", None)
            if profile is not None:
                _add_profile(snap, f"{group}{_SEPARATOR}{name}", profile)
    return snap


def _cell_diff(name: str, expected: np.ndarray, actual: np.ndarray) -> str:
    """Describe the differing cells of one array that kept its shape."""
    both_nan = np.isnan(expected) & np.isnan(actual)
    delta = np.where(both_nan, 0.0, np.abs(actual - expected))
    delta = np.where(np.isnan(delta), np.inf, delta)
    worst = np.argsort(delta, axis=None)[::-1][:_CELLS_SHOWN]
    cells = ", ".join(
        f"{[int(j) for j in np.unravel_index(i, expected.shape)]}: "
        f"{float(expected.flat[i])!r} -> {float(actual.flat[i])!r}"
        for i in worst
        if delta.flat[i] > 0.0
    )
    return f"{name}: max |delta| {delta.max():.3g}; {cells}"


def diff(
    expected: Snapshot,
    actual: Snapshot,
    rtol: float = 0.0,
    atol: float = 0.0,
) -> list[str]:
    """
    List the differences between two snapshots, empty when they agree.

    Parameters
    ----------
    expected, actual
        The snapshots to compare.
    rtol, atol
        A cell agrees when ``abs(actual - expected) <= atol + rtol *
        abs(expected)``; NaN agrees with NaN. Exact by default.

    Returns
    -------
    list[str] :
        One line per name present in only one snapshot, per array whose shape
        changed and per array with a cell outside the tolerance.
    """
    lines = [f"{name}: missing" for name in sorted(expected.keys() - actual.keys())]
    lines += [f"{name}: new" for name in sorted(actual.keys() - expected.keys())]
    for name in sorted(expected.keys() & actual.keys()):
        old, new = expected[name], actual[name]
        if old.shape != new.shape:
            lines.append(f"{name}: shape {old.shape} -> {new.shape}")
        elif old.dtype.kind in "fc":
            if not np.allclose(new, old, rtol=rtol, atol=atol, equal_nan=True):
                lines.append(_cell_diff(name, old, new))
        elif not np.array_equal(new, old):
            lines.append(f"{name}: values differ")
    return lines


def save(path: Path, snap: Snapshot) -> None:
    """Write a snapshot to a compressed ``.npz`` file."""
    np.savez_compressed(path, **snap)


def load(path: Path) -> Snapshot:
    """Read a snapshot written by `save`."""
    with np.load(path) as data:
        return {name: data[name] for name in data.files}
