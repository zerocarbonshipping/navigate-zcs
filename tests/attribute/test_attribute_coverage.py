# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Attribute coverage tests: run simulations that touch every attribute and command.

These tests verify that every attribute registered in _attributes.py and every
command registered in _commands.py can be parsed and executed through the full
simulation pipeline.  The .nav/.inc files exercise both DEFINE (NAV) and EVENTS
(EVENTS) sections so that SECTION_BOTH attributes are set at startup and updated at
runtime.
"""
from pathlib import Path

import pytest

from helpers.simulation import check_invariants, run_simulation

SIMULATIONS_DIR = Path(__file__).resolve().parent / "simulations"


@pytest.mark.slow
class TestAttributeCoverage:
    """Full-pipeline test: every attribute and command parses and executes."""

    @pytest.fixture(scope="class")
    def manager(self):
        return run_simulation(SIMULATIONS_DIR / "attribute_coverage")

    def test_completes_without_error(self, manager):
        """The simulation runs to completion."""
        assert manager is not None

    def test_invariants(self, manager):
        check_invariants(manager)

    def test_has_expected_time_steps(self, manager):
        """Timeline should have at least 9 yearly steps."""
        assert len(manager.get_dateline()) >= 9

    def test_two_fleets(self, manager):
        assert len(manager.nodes.fleets) >= 2

    def test_four_vessel_types(self, manager):
        total = sum(len(f.get_vessels()) for f in manager.nodes.fleets.values())
        assert total >= 4
