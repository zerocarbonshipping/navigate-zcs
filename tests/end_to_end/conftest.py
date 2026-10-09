# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Deck assembly for the combination tests.

A combination deck is the committed base in simulations/combinations/0_includes
plus any template includes from simulations/combinations, whose %name% values
are filled in per combination; with none, it is the base deck itself.
`run_combination` writes that deck into a temporary directory, runs it, checks
the universal invariants and caches the manager per module, so a test can read
the run of another combination as its reference without running it twice.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from helpers.simulation import check_invariants, run_simulation

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from navigate.simulation import SimulationManager

COMBINATIONS_DIR = Path(__file__).resolve().parent / "simulations" / "combinations"
BASE_INCLUDES = ("model.inc", "fuels_ports.inc", "fleet.inc")
TIMELINE_INCLUDE = "timeline.inc"

# the DSL's template value; a comment may name one without it being filled in
_TEMPLATE = re.compile(r"%[a-z_]+%")

type Layer = tuple[str, Mapping[str, object]]


def fill_template(name: str, values: Mapping[str, object]) -> str:
    """Return the template include `name` with each %key% replaced by its value."""
    text = (COMBINATIONS_DIR / name).read_text()
    for key, value in values.items():
        placeholder = f"%{key}%"
        assert placeholder in text, f"{name} has no {placeholder}"
        text = text.replace(placeholder, str(value))
    unfilled = [
        line for line in text.splitlines() if _TEMPLATE.search(line.split("#")[0])
    ]
    assert not unfilled, f"{name} has unfilled template values: {unfilled}"
    return text


@pytest.fixture(scope="module")
def run_combination(
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[..., SimulationManager]:
    """Run the base deck plus the given template layers, once per module."""
    runs: dict[
        tuple[tuple[str, tuple[tuple[str, str], ...]], ...], SimulationManager
    ] = {}

    def run(*layers: Layer) -> SimulationManager:
        key = tuple(
            (name, tuple(sorted((k, str(v)) for k, v in values.items())))
            for name, values in layers
        )
        if key in runs:
            return runs[key]

        deck_dir = tmp_path_factory.mktemp("combination")
        base = COMBINATIONS_DIR / "0_includes"

        define = [f'\tInclude "{base / name}"' for name in BASE_INCLUDES]
        for name, values in layers:
            (deck_dir / name).write_text(fill_template(name, values))
            define.append(f'\tInclude "{name}"')

        (deck_dir / f"{deck_dir.name}.nav").write_text(
            "DEFINE {\n"
            + "\n".join(define)
            + "\n}\n\nEVENTS {\n"
            + f'\tInclude "{base / TIMELINE_INCLUDE}"\n'
            + "}\n"
        )

        manager = run_simulation(deck_dir)
        check_invariants(manager)
        runs[key] = manager
        return manager

    return run
