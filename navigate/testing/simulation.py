# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Shared helpers for test suites that run full simulations in-process.

Used by tests/attribute (attribute coverage) and tests/guardrails (behavior
guardrails); designed so a future regression suite can reuse the same runner
and universal invariants without duplication.
"""
import argparse
import os
from pathlib import Path

import numpy as np

from navigate.__main__ import ASSUMPTIONS_ENV_VAR
from navigate.manager import SimulationManager


def default_assumptions_dir() -> Path:
    """
    Resolves the assumptions directory like the CLI: environment variable
    first, falling back to the repository checkout next to the package.

    Returns
    -------
    Path to the assumptions directory.
    """

    env = os.environ.get(ASSUMPTIONS_ENV_VAR)
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "assumptions"


def make_args(data_dir: Path | None = None) -> argparse.Namespace:
    """
    Builds the CLI argument namespace expected by SimulationManager.read_deck.
    'solver' is left as None so a deck's BunkerOptions.Solver setting wins.

    Parameters
    ----------
    data_dir
        Assumptions directory; resolved via default_assumptions_dir if None.
    """

    return argparse.Namespace(
        data_dir=data_dir or default_assumptions_dir(),
        suppress_plots=True,
        export_assumptions=False,
        solver=None,
        log_level="WARNING",
        profile=False,
        replot=None,
        filename=None,
    )


def run_simulation(sim_dir: Path, data_dir: Path | None = None) -> SimulationManager:
    """
    Parses and runs the deck '<sim_dir>/<sim_dir.name>.nav'.

    Parameters
    ----------
    sim_dir
        Deck directory; must contain a .nav file named after the directory.
    data_dir
        Assumptions directory; resolved via default_assumptions_dir if None.

    Returns
    -------
    The manager after a completed run, exposing profiles and nodes.
    """

    nav_file = sim_dir / f"{sim_dir.name}.nav"
    assert nav_file.exists(), f"Missing {nav_file}"

    manager = SimulationManager()
    manager.read_deck(nav_file, make_args(data_dir))
    manager.run()

    return manager


def check_invariants(manager: SimulationManager) -> None:
    """
    Verifies universal invariants that must hold for every completed
    simulation.

    Parameters
    ----------
    manager
        Manager of a completed run.
    """

    dateline = manager.get_dateline()
    timeline = manager.get_timeline()
    assert dateline is not None
    assert len(dateline) >= 2
    assert len(timeline) == len(dateline)
    assert np.all(np.diff(timeline) > 0), "Timeline is not strictly increasing"
    assert not np.any(np.isnan(timeline))
    assert not np.any(np.isinf(timeline))

    fleets = manager.nodes.fleets
    assert len(fleets) > 0, "No fleets defined"
    total_vessels = sum(len(f.get_vessels()) for f in fleets.values())
    assert total_vessels > 0, "No vessels in any fleet"
