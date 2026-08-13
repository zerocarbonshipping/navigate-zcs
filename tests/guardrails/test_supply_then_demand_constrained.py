# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Guardrail: supply-constrained, then demand-constrained scenario.

Like supply_constrained, but the Producer's development limit is raised so
supply catches up with demand roughly halfway through the simulation. After
catch-up the Producer must leave its constraint and track demand with a
slight surplus — continuously, not as an over/under-supply oscillation. The
intent prose and the diagnostic list for failures live in
simulations/supply_then_demand_constrained/BEHAVIOR.md.
"""
from pathlib import Path

import numpy as np
import pytest

from navigate.testing.simulation import EPS_DEVELOPMENT_REL, assertable_end, check_invariants, run_simulation

SIMULATIONS_DIR = Path(__file__).resolve().parent / "simulations"

FUEL = "ammonia_electro"

# First step at which development leaves the constraint. A fixed index from
# the deck tuning run (2026-08, MaximumDevelopment = 8), not auto-detected:
# crossing detection on LP output would need its own tolerance and could
# silently drift with unrelated model changes.
CATCHUP_STEP = 11

# Band on the deliverable-supply surplus (capacity x uptime, minus
# consumption), normalized by TOTAL fleet fuel demand so the early small
# alternative-fuel volumes cannot inflate the ratio. The surplus exists to
# absorb demand jumps within one time step (newbuilds and fuel conversions,
# ~4%/year fleet replenishment) without triggering short-term shortages and
# regulatory non-compliance, so it is measured on what plants can actually
# deliver — deliberately independent of the nameplate-vs-uptime distinction.
# The band values are proposed, not yet domain-owner signed off — see
# BEHAVIOR.md, Threshold ownership.
MIN_SURPLUS = 0.02
MAX_SURPLUS = 0.12


@pytest.fixture(scope="module")
def manager():
    return run_simulation(SIMULATIONS_DIR / "supply_then_demand_constrained")


@pytest.fixture(scope="module")
def producer(manager):
    return manager.nodes.producers["epc_europe"]


@pytest.fixture(scope="module")
def post_window(manager, producer):
    """Post-catch-up steps, with the same tail exclusion as
    supply_constrained (see BEHAVIOR.md, Known limitations)."""
    end = assertable_end(manager, producer)
    # > +1 because test_surplus_band additionally skips the catch-up step
    assert end > CATCHUP_STEP + 1, \
        "Post-catch-up window is empty — re-derive CATCHUP_STEP from a tuning run"
    return slice(CATCHUP_STEP, end)


@pytest.fixture(scope="module")
def deliverable(producer):
    """Deliverable e-ammonia supply: capacity x uptime per plant increment."""
    return producer.profile.get_production_energy(FUEL)


@pytest.mark.slow
class TestSupplyThenDemandConstrained:

    def test_invariants(self, manager):
        check_invariants(manager)

    def test_supply_limited_before_catchup(self, producer):
        development = producer.profile.get_development()
        maximum = producer.profile.get_maximum_development()

        pinned = slice(1, CATCHUP_STEP)
        assert np.all(np.abs(development[pinned] - maximum[pinned])
                      <= EPS_DEVELOPMENT_REL * maximum[pinned])

    def test_leaves_constraint_after_catchup(self, producer, post_window):
        development = producer.profile.get_development()
        maximum = producer.profile.get_maximum_development()

        assert np.all(development[post_window]
                      < maximum[post_window] * (1. - EPS_DEVELOPMENT_REL))

    def test_no_supply_squeeze(self, manager, deliverable, post_window):
        consumption = manager.profile.get_consumed_energy(FUEL)

        assert np.all(deliverable[post_window] >= consumption[post_window] * (1. - 1e-6))

    def test_surplus_band(self, manager, deliverable, post_window):
        consumption = manager.profile.get_consumed_energy(FUEL)
        total = manager.profile.get_total_consumed_energy()

        # the catch-up step itself is transitional: the surplus builds up
        # from zero while development leaves the constraint
        post = slice(post_window.start + 1, post_window.stop)

        surplus = (deliverable[post] - consumption[post]) / total[post]
        assert np.all(surplus >= MIN_SURPLUS)
        assert np.all(surplus <= MAX_SURPLUS)
