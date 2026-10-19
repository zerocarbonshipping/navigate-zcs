# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Write the full results of a run to one Parquet file.

The file holds every result of the global profile and of each node profile, one
row per series and date, and nothing but the profiles: the metadata only says
which schema, Navigate version and deck wrote it, the unit of each result, and
the run's fuel and emission constants the results were converted with.
Values are as the profiles hold them, except that the counts a result keeps per
time step are written per year, as their units say, and a value that is
not set or not finite is written missing. Lantern reads it; any Parquet reader
can. The layout is described in docs/reference_manual/results_file.md and
versioned by SCHEMA_VERSION.
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

from navigate.core.profiles import per_step_results, result_names, result_units
from navigate.util import TOLERANCE, dates_to_years, step_lengths

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from navigate.core.profiles._base_profile import _BaseProfile
    from navigate.core.simulation_results import SimulationResults

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 2
METADATA_KEY = b"navigate"

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
    """One timeline of one profile result, with its place in the file."""

    kind: str
    node: str
    attribute: str
    key1: str | None
    key2: str | None
    values: np.ndarray


def write_results(results: SimulationResults, path: Path, deck_name: str) -> Path:
    """
    Write every profile result of a finished run to a Parquet file.

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
    days = results.dateline.astype("datetime64[D]")
    dates = pa.array(days, type=pa.date32())
    series = list(_series(results, step_lengths(dates_to_years(results.dateline))))
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
            from_pandas=True,  # NaN is written missing
        ),
    }
    table = pa.table(columns, schema=SCHEMA)

    return table.replace_schema_metadata(
        {METADATA_KEY: json.dumps(_metadata(results, deck_name)).encode()}
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


def _series(results: SimulationResults, step_years: np.ndarray) -> Iterator[Series]:
    """
    Yield every series of every profile result that is not negligible throughout.

    Parameters
    ----------
    results
        Results of the finished run.
    step_years
        Length of each time step, years, to turn per-step counts into rates.

    Yields
    ------
    Series
        Each timeline, in profile and result order.
    """
    for kind, node, profile in _profiles(results):
        per_step = per_step_results(type(profile))

        for attribute, value in _results(kind, node, profile):
            items = value.items() if isinstance(value, dict) else [(None, value)]

            for key, values in items:
                floats = np.asarray(values, dtype=np.float64)

                if attribute in per_step:
                    floats = floats / step_years

                # an infinite value, e.g. a limit without bound, is not a result
                floats = np.where(np.isinf(floats), np.nan, floats)

                # a series negligible or missing throughout carries no result
                if not np.any(np.abs(np.nan_to_num(floats)) >= TOLERANCE):
                    continue

                key1, key2 = key if isinstance(key, tuple) else (key, None)
                yield Series(kind, node, attribute, _label(key1), _label(key2), floats)


def _results(kind: str, node: str, profile: _BaseProfile) -> Iterator[tuple[str, Any]]:
    """Yield each result of a profile by name, logging and skipping one that fails."""
    for name in sorted(result_names(type(profile))):
        try:
            value = getattr(profile, name)

        except Exception as e:
            logger.error("Results: skipping '%s' of %s '%s': %s", name, kind, node, e)
            continue

        yield name, value


def _label(key: str | Enum | None) -> str | None:
    if key is None:
        return None

    return key.name if isinstance(key, Enum) else str(key)


def _metadata(results: SimulationResults, deck_name: str) -> dict[str, Any]:
    """
    Describe the run: schema, provenance, units and the run's constants.

    Parameters
    ----------
    results
        Results of the finished run, whose profiles name the units and hold the
        constants.
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
        "units": _units(results),
        "constants": _constants(results),
        "plant_fuel": {
            plant.name: plant.fuel.name for plant in results.nodes.plants.values()
        },
    }


def _units(results: SimulationResults) -> dict[str, str]:
    """Map every result of the run's profiles to its unit, sorted by name."""
    units: dict[str, str] = {}

    for _, _, profile in _profiles(results):
        units |= result_units(type(profile))

    return dict(sorted(units.items()))


def _constants(results: SimulationResults) -> dict[str, Any]:
    """Give the fuel and emission constants the run converted its results with."""
    context = results.profile.context

    return {
        "lower_heating_value": context.lower_heating_value,
        "fuel_type": {
            fuel_name: fuel_type.name
            for fuel_name, fuel_type in context.fuel_type.items()
        },
        "liquid_market_fuels": sorted(context.liquid_market_fuels),
        "global_warming_potential": context.global_warming_potential,
        "emissions_lifetime": results.general_nodes.model_definition.emissions_lifetime,
    }


def _navigate_version() -> str:
    try:
        return version("navigate-zcs")

    except PackageNotFoundError:
        return "unknown"
