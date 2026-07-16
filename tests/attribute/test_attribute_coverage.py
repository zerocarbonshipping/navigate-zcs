# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Attribute coverage tests: run simulations that touch every attribute and command.

These tests verify that every attribute registered in _attributes.py and every
command registered in _commands.py can be parsed and executed through the full
simulation pipeline.  The .nav/.inc files exercise both DEFINE (NAV) and EVENTS
(EVENTS) sections so that SECTION_BOTH attributes are set at startup and updated at
runtime.
"""
import argparse
from pathlib import Path

import numpy as np
import pytest

from navigate.manager import SimulationManager

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ASSUMPTIONS_DIR = REPO_ROOT / "assumptions"
SIMULATIONS_DIR = Path(__file__).resolve().parent / "simulations"


def _make_args():
    return argparse.Namespace(
        data_dir=ASSUMPTIONS_DIR,
        suppress_plots=True,
        export_assumptions=False,
        solver=None,
        log_level="WARNING",
        profile=False,
        replot=None,
        filename=None,
    )


def _run_simulation(sim_name):
    """Parse and run a .nav simulation, returning the manager."""
    sim_dir = SIMULATIONS_DIR / sim_name
    nav_file = sim_dir / f"{sim_name}.nav"
    assert nav_file.exists(), f"Missing {nav_file}"

    manager = SimulationManager()
    manager.read_deck(nav_file, _make_args())
    manager.run()

    return manager


def _check_invariants(manager):
    """Verify structural invariants on a completed simulation."""
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


@pytest.mark.slow
class TestAttributeCoverage:
    """Full-pipeline test: every attribute and command parses and executes."""

    @pytest.fixture(scope="class")
    def manager(self):
        return _run_simulation("attribute_coverage")

    def test_completes_without_error(self, manager):
        """The simulation runs to completion."""
        assert manager is not None

    def test_invariants(self, manager):
        _check_invariants(manager)

    def test_has_expected_time_steps(self, manager):
        """Timeline should have at least 9 yearly steps."""
        assert len(manager.get_dateline()) >= 9

    def test_two_fleets(self, manager):
        assert len(manager.nodes.fleets) >= 2

    def test_four_vessel_types(self, manager):
        total = sum(len(f.get_vessels()) for f in manager.nodes.fleets.values())
        assert total >= 4
