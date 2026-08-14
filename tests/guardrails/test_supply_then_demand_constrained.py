# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Guardrail: supply-constrained, then demand-constrained scenario.

Like supply_constrained, but the Producer's development limit is raised so
supply catches up with demand roughly halfway through the simulation. After
catch-up the Producer must leave its constraint and track demand with a
slight surplus — continuously, not as an over/under-supply oscillation. The
domain contract lives in
simulations/supply_then_demand_constrained/BEHAVIOR.md.
"""
from pathlib import Path

import numpy as np
import pytest

from navigate.testing.simulation import EPS_DEVELOPMENT_REL, assertable_end, check_invariants, run_simulation

SIMULATIONS_DIR = Path(__file__).resolve().parent / "simulations"

FUEL = "ammonia_electro"

# First step at which development leaves the constraint. A fixed index from
# the deck tuning run (MaximumDevelopment = 8), not auto-detected:
# crossing detection on LP output would need its own tolerance and could
# silently drift with unrelated model changes.
CATCHUP_STEP = 11

# Supply-constrained steps: development decisions start at step 1 (the first
# step only initializes expectations).
PRE_CATCHUP = slice(1, CATCHUP_STEP)

# Noise floor for asserting "no remedial units", relative to the remedial
# magnitude of the genuinely supply-constrained pre-catch-up phase: 1e-6 of
# that scale is far below any economically meaningful purchase while
# comfortably above LP float dust.
EPS_REMEDIAL_REL = 1e-6

# Band on the deliverable-supply surplus (capacity x uptime, minus
# consumption), normalized by total fleet fuel demand — see BEHAVIOR.md for
# the domain reasoning and the band's sign-off status.
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

        assert np.all(np.abs(development[PRE_CATCHUP] - maximum[PRE_CATCHUP])
                      <= EPS_DEVELOPMENT_REL * maximum[PRE_CATCHUP])

    def test_leaves_constraint_after_catchup(self, producer, post_window):
        development = producer.profile.get_development()
        maximum = producer.profile.get_maximum_development()

        assert np.all(development[post_window]
                      < maximum[post_window] * (1. - EPS_DEVELOPMENT_REL))

    def test_demand_met_after_catchup(self, manager, post_window):
        """Supply >= demand is not observable from consumption (the bunker LP
        caps consumption at available supply): a squeeze shows up as the
        regulation buying remedial units instead — see BEHAVIOR.md. After
        catch-up demand must be met, i.e. no remedial units."""
        regulation = manager.nodes.regulations["intensity_regulation"]
        remedial = regulation.profile.get_remedial_units()

        # deck validity: before catch-up the scenario is supply-constrained,
        # so remedial units are strictly positive
        pre_catchup = remedial[PRE_CATCHUP]
        assert np.all(pre_catchup > 0.)

        assert np.all(remedial[post_window] <= EPS_REMEDIAL_REL * pre_catchup.max())

    def test_surplus_band(self, manager, deliverable, post_window):
        consumption = manager.profile.get_consumed_energy(FUEL)
        total = manager.profile.get_total_consumed_energy()

        # the catch-up step itself is transitional: the surplus builds up
        # from zero while development leaves the constraint
        post = slice(post_window.start + 1, post_window.stop)

        surplus = (deliverable[post] - consumption[post]) / total[post]
        assert np.all(surplus >= MIN_SURPLUS)
        assert np.all(surplus <= MAX_SURPLUS)
