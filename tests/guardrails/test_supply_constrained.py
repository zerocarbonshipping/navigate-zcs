# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Guardrail: continuously supply-constrained scenario.

A GHG-intensity regulation imposes alternative-fuel demand that the Producer
can never satisfy, so plant development must sit at MaximumDevelopment for
the whole assertable window. The domain contract lives in
simulations/supply_constrained/BEHAVIOR.md.
"""
from pathlib import Path

import numpy as np
import pytest

from helpers.simulation import EPS_DEVELOPMENT_REL, assertable_end, check_invariants, run_simulation

SIMULATIONS_DIR = Path(__file__).resolve().parent / "simulations"


@pytest.fixture(scope="module")
def manager():
    return run_simulation(SIMULATIONS_DIR / "supply_constrained")


@pytest.fixture(scope="module")
def producer(manager):
    return manager.nodes.producers["epc_europe"]


@pytest.fixture(scope="module")
def window(manager, producer):
    """Assertable steps: the first step only initializes expectations (no
    development decision is taken yet), and the final LeadTime years are
    excluded per assertable_end — a known, explicitly not-desired limitation
    (see BEHAVIOR.md); the exclusion is not an endorsement."""
    end = assertable_end(manager, producer)
    assert end > 1, "Assertable window is empty — the horizon is too short"
    return slice(1, end)


@pytest.mark.slow
class TestSupplyConstrained:

    def test_invariants(self, manager):
        check_invariants(manager)

    def test_development_pinned_to_constraint(self, producer, window):
        development = producer.profile.get_development()
        maximum = producer.profile.get_maximum_development()

        assert np.all(np.abs(development[window] - maximum[window])
                      <= EPS_DEVELOPMENT_REL * maximum[window])

    def test_demand_remains_unmet(self, manager, window):
        """Deck validity: the scenario must stay supply-constrained, which
        shows up as the fleet still paying remedial costs near the end."""
        regulation = manager.nodes.regulations["intensity_regulation"]
        remedial = regulation.profile.get_remedial_units()
        assert np.all(remedial[window] > 0.)
