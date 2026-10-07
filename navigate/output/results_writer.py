# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Write the full results of a run to one Parquet file.

The file holds every public profile reader of the global profile and of each node
profile, one row per series and date, and nothing but the profiles: the metadata
only says which schema, Navigate version and deck wrote it, and the unit of each
reader. Lantern reads it; any Parquet reader can. The layout is described in
docs/reference_manual/results_file.md and versioned by SCHEMA_VERSION.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from enum import Enum
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any, NamedTuple

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from navigate.output._result_units import UNITS

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from navigate.core.profiles._base_profile import _BaseProfile
    from navigate.core.simulation_results import SimulationResults

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
METADATA_KEY = b"navigate"
READER_PREFIXES = ("get_", "is_", "has_", "cost_is_")

GLOBAL_KIND = "global"

# Parquet dictionary-encodes the repeated labels on disk by itself
SCHEMA = pa.schema(
    [
        ("kind", pa.string()),
        ("node", pa.string()),
        ("attribute", pa.string()),
        ("key1", pa.string()),
        ("key2", pa.string()),
        ("date", pa.date32()),
        ("value", pa.float64()),
    ]
)


class Series(NamedTuple):
    """One timeline of one profile reader, with its place in the file."""

    kind: str
    node: str
    attribute: str
    key1: str | None
    key2: str | None
    values: np.ndarray


def write_results(results: SimulationResults, path: Path, deck_name: str) -> Path:
    """
    Write every profile reader of a finished run to a Parquet file.

    Parameters
    ----------
    results
        Results of the finished run.
    path
        File to write; its directory is created when missing.
    deck_name
        Name of the simulation deck, stored in the file metadata.

    Returns
    -------
    Path
        The file written.
    """
    table = results_table(results, deck_name)

    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, compression="zstd")

    logger.info("Results written to '%s'.", path)

    return path


def results_table(results: SimulationResults, deck_name: str) -> pa.Table:
    """
    Build the results table of a run, metadata included.

    Parameters
    ----------
    results
        Results of the finished run.
    deck_name
        Name of the simulation deck, stored in the table metadata.

    Returns
    -------
    pa.Table
        One row per series and date, in SCHEMA.
    """
    dates = pa.array(results.dateline.astype("datetime64[D]"), type=pa.date32())
    series = list(_series(results))
    steps = len(dates)

    columns = {
        name: np.repeat(
            np.array([getattr(s, name) for s in series], dtype=object), steps
        )
        for name in ("kind", "node", "attribute", "key1", "key2")
    }
    columns |= {
        "date": pa.concat_arrays([dates] * len(series)) if series else dates[:0],
        "value": pa.array(
            np.concatenate([s.values for s in series]) if series else [],
            type=pa.float64(),
        ),
    }
    table = pa.table(columns, schema=SCHEMA)

    return table.replace_schema_metadata(
        {METADATA_KEY: json.dumps(_metadata(deck_name)).encode()}
    )


def _profiles(results: SimulationResults) -> Iterator[tuple[str, str, _BaseProfile]]:
    """
    Walk the global profile and every node profile of the run.

    Parameters
    ----------
    results
        Results of the finished run.

    Yields
    ------
    tuple[str, str, _BaseProfile]
        Node kind, node name ("" for the global profile) and profile.
    """
    yield GLOBAL_KIND, "", results.profile

    for node in results.nodes.all_nodes():
        if hasattr(node, "profile"):
            yield node.type.lower(), node.name, node.profile


def _series(results: SimulationResults) -> Iterator[Series]:
    """
    Yield every series of every profile reader that is not zero or missing throughout.

    Parameters
    ----------
    results
        Results of the finished run.

    Yields
    ------
    Series
        Each timeline, in profile and reader order.
    """
    for kind, node, profile in _profiles(results):
        for attribute, value in _readers(kind, node, profile):
            items = value.items() if isinstance(value, dict) else [(None, value)]

            for key, values in items:
                floats = np.asarray(values, dtype=np.float64)

                # a series zero or missing throughout carries no result
                if not np.any(np.nan_to_num(floats)):
                    continue

                key1, key2 = key if isinstance(key, tuple) else (key, None)
                yield Series(kind, node, attribute, _label(key1), _label(key2), floats)


def _readers(kind: str, node: str, profile: _BaseProfile) -> Iterator[tuple[str, Any]]:
    """
    Call each public reader of a profile, skipping one that fails.

    Parameters
    ----------
    kind
        Node kind, used in log messages.
    node
        Node name, used in log messages.
    profile
        Profile to read.

    Yields
    ------
    tuple[str, Any]
        Attribute name (reader name without get_) and the reader's result.
    """
    for name in sorted(dir(type(profile))):
        if not name.startswith(READER_PREFIXES):
            continue

        try:
            value = getattr(profile, name)()

        except Exception as e:
            logger.error("Results: skipping '%s' of %s '%s': %s", name, kind, node, e)
            continue

        yield name.removeprefix("get_"), value


def _label(key: str | Enum | None) -> str | None:
    if key is None:
        return None

    return key.name if isinstance(key, Enum) else str(key)


def _metadata(deck_name: str) -> dict[str, Any]:
    """
    Describe the run: schema, provenance and the unit of each reader.

    Parameters
    ----------
    deck_name
        Name of the simulation deck.

    Returns
    -------
    dict[str, Any]
        JSON-serializable metadata.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "navigate_version": _navigate_version(),
        "deck": deck_name,
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "units": dict(UNITS),
    }


def _navigate_version() -> str:
    try:
        return version("navigate-zcs")

    except PackageNotFoundError:
        return "unknown"
