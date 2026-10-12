# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Cached runs of the combination decks.

`run_combination` writes a combination deck (helpers/combinations.py) into a
temporary directory, runs it, checks the universal invariants and caches the
results per module, so a test can read the run of another combination as its
reference without running it twice.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from helpers.combinations import COMBINATIONS, write_combination
from helpers.simulation import check_invariants, run_simulation

if TYPE_CHECKING:
    from collections.abc import Callable

    from helpers.combinations import DeckFamily, Layer
    from navigate.core import SimulationResults


def _cached_runner(
    tmp_path_factory: pytest.TempPathFactory, family: DeckFamily
) -> Callable[..., SimulationResults]:
    """Return a function that runs the family's base plus layers, once each."""
    runs: dict[
        tuple[tuple[str, tuple[tuple[str, str], ...]], ...], SimulationResults
    ] = {}

    def run(*layers: Layer) -> SimulationResults:
        key = tuple(
            (name, tuple(sorted((k, str(v)) for k, v in values.items())))
            for name, values in layers
        )
        if key in runs:
            return runs[key]

        deck_dir = tmp_path_factory.mktemp(family.directory.name)
        write_combination(deck_dir, family, *layers)
        results = run_simulation(deck_dir)
        check_invariants(results)
        runs[key] = results
        return results

    return run


@pytest.fixture(scope="module")
def run_combination(
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[..., SimulationResults]:
    """Run the combination base deck plus the given template layers, once per module."""
    return _cached_runner(tmp_path_factory, COMBINATIONS)
