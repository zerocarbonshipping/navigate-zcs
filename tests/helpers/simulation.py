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
from navigate.core.misc import YEAR
from navigate.core.nodes.producer import Producer
from navigate.manager import SimulationManager

# Tolerance for comparing per-step producer development against the nominal
# per-year MaximumDevelopment in decks with yearly time steps: leap years
# deviate by up to 366/365.25 - 1 (about 0.21%). Property tests in decks
# with non-yearly steps need a rate-normalized comparison instead (as
# check_invariants does).
EPS_DEVELOPMENT_REL = 2.5e-3


def default_assumptions_dir() -> Path:
    """
    Resolves the assumptions directory like the CLI: environment variable
    first, falling back to the repository checkout containing this test tree.

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


def assertable_end(manager: SimulationManager, producer: Producer) -> int:
    """
    Last time-step index (exclusive) at which producer development is
    assertable: in the final LeadTime years the foresight window runs past
    the simulation end and the producer under-builds by construction.

    Parameters
    ----------
    manager
        Manager of a completed run.
    producer
        Producer whose first plant's LeadTime defines the excluded tail.

    Returns
    -------
    Exclusive end index, guaranteed within (0, len(timeline)].
    """

    timeline = manager.get_timeline()
    lead_time = int(round(producer.assets[0].lead_time.get(timeline[0])))
    end = len(timeline) - lead_time
    # guard against vacuously-true assertions on empty (or, with negative
    # indices, silently wrong) windows when a horizon shrinks or a default
    # lead time grows
    assert 0 < end <= len(timeline), \
        f"Assertable window is empty: {len(timeline)} steps, lead time {lead_time}"
    return end


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

    for fuel_name, energy in manager.profile.get_consumed_energy().items():
        assert not np.any(np.isnan(energy)), f"NaN consumed energy for '{fuel_name}'"
        assert not np.any(np.isinf(energy)), f"Infinite consumed energy for '{fuel_name}'"
        assert np.all(energy >= -1e-9), f"Negative consumed energy for '{fuel_name}'"

    # development is recorded per time step while MaximumDevelopment is a
    # nominal per-year rate, so the cap must be scaled by each step's actual
    # length (no development is recorded at the first step)
    step_years = np.ones(len(timeline))
    step_years[1:] = np.diff(timeline) / YEAR

    for producer_name, producer in manager.nodes.producers.items():
        development = producer.profile.get_development()
        maximum = producer.profile.get_maximum_development()
        assert not np.any(np.isnan(development)), f"NaN development for '{producer_name}'"
        assert np.all(development >= -1e-9), f"Negative development for '{producer_name}'"
        assert np.all(development <= maximum * step_years * (1. + 1e-6) + 1e-9), \
            f"Development exceeds MaximumDevelopment for '{producer_name}'"
