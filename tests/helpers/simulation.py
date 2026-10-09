# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Shared helpers for test suites that run full simulations in-process.

Used by tests/end_to_end, so every deck runs through the same runner and
universal invariants.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import numpy as np

from navigate.__main__ import ASSUMPTIONS_ENV_VAR
from navigate.simulation import SimulationManager
from navigate.util import YEAR

REPO_ROOT = Path(__file__).resolve().parents[2]


def default_assumptions_dir() -> Path:
    """
    Resolve the assumptions directory the way the CLI does.

    Checks the environment variable first, falling back to the repository checkout
    containing this test tree.

    Returns
    -------
    Path to the assumptions directory.
    """
    env = os.environ.get(ASSUMPTIONS_ENV_VAR)
    if env:
        return Path(env)
    return REPO_ROOT / "assumptions"


def run_simulation(sim_dir: Path, data_dir: Path | None = None) -> SimulationManager:
    """
    Parse and run the deck '<sim_dir>/<sim_dir.name>.nav'.

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

    manager = SimulationManager(
        nav_file, data_dir=data_dir or default_assumptions_dir()
    )
    manager.run()

    return manager


def clear_output_dir(output_dir: Path) -> None:
    """
    Delete a deck's report output directory before a run.

    Only the coming run's files then exist: stale files from earlier runs
    (including the report writer's locked-file retry names) must never reach
    a consumer of the output.

    Parameters
    ----------
    output_dir
        The deck's report output directory.
    """
    shutil.rmtree(output_dir, ignore_errors=True)


def check_invariants(manager: SimulationManager) -> None:
    """
    Verify universal invariants that must hold for every completed simulation.

    Parameters
    ----------
    manager
        Manager of a completed run.
    """
    dateline = manager.dateline
    timeline = manager.timeline
    assert dateline is not None
    assert len(dateline) >= 2
    assert len(timeline) == len(dateline)
    assert np.all(np.diff(timeline) > 0), "Timeline is not strictly increasing"
    assert not np.any(np.isnan(timeline))
    assert not np.any(np.isinf(timeline))

    fleets = manager.nodes.fleets
    assert len(fleets) > 0, "No fleets defined"
    total_vessels = sum(len(f.vessels) for f in fleets.values())
    assert total_vessels > 0, "No vessels in any fleet"

    for fuel_name, energy in manager.profile.get_consumed_energy().items():
        assert not np.any(np.isnan(energy)), f"NaN consumed energy for '{fuel_name}'"
        assert not np.any(np.isinf(energy)), (
            f"Infinite consumed energy for '{fuel_name}'"
        )
        assert np.all(energy >= -1e-9), f"Negative consumed energy for '{fuel_name}'"

    # development is recorded per time step while MaximumDevelopment is a
    # nominal per-year rate, so the cap must be scaled by each step's actual
    # length (no development is recorded at the first step)
    step_years = np.ones(len(timeline))
    step_years[1:] = np.diff(timeline) / YEAR

    for producer_name, producer in manager.nodes.producers.items():
        development = producer.profile.get_development()
        maximum = producer.profile.get_maximum_development()
        assert not np.any(np.isnan(development)), (
            f"NaN development for '{producer_name}'"
        )
        assert np.all(development >= -1e-9), (
            f"Negative development for '{producer_name}'"
        )
        assert np.all(development <= maximum * step_years * (1.0 + 1e-6) + 1e-9), (
            f"Development exceeds MaximumDevelopment for '{producer_name}'"
        )
