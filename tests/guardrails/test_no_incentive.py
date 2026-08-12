# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Guardrail: no-incentive scenario.

Without any GHG pricing mechanism, the newbuild choice model must allocate
nearly the whole fleet to oil and methane vessels. The intent prose and the
diagnostic list for failures live in simulations/no_incentive/BEHAVIOR.md.
"""
from pathlib import Path

import numpy as np
import pytest

from navigate.core.enum_ import FuelTypeID
from navigate.testing.simulation import check_invariants, run_simulation

SIMULATIONS_DIR = Path(__file__).resolve().parent / "simulations"

# Absolute tolerance on market shares: vessel counts are lumpy at fleet scale
# and the nested-logit allocation carries small numerical noise from the
# LP-coupled fuel pricing. 0.5 percentage points absorbs both without hiding
# a share that is off by a factor of two.
EPS_SHARE = 0.005

# Domain-owner thresholds (see BEHAVIOR.md, Threshold ownership): absent any
# incentive, methanol stays a marginal choice (~2-3% at most) and ammonia an
# even smaller one (~1%).
MAX_METHANOL_SHARE = 0.03
MAX_AMMONIA_SHARE = 0.01
MIN_OIL_METHANE_SHARE = 1. - MAX_METHANOL_SHARE - MAX_AMMONIA_SHARE


@pytest.fixture(scope="module")
def manager():
    return run_simulation(SIMULATIONS_DIR / "no_incentive")


@pytest.fixture(scope="module")
def market_shares(manager):
    """Fleet-wide market share per fuel type at the final time step."""
    fleet = manager.nodes.fleets["container_15000_teu"]
    fuel_types = {vessel.name: FuelTypeID(vessel.fuel_type) for vessel in fleet.get_vessels()}
    existing = fleet.profile.get_existing_vessels()

    total = sum(counts[-1] for counts in existing.values())
    shares = dict.fromkeys(fuel_types.values(), 0.)
    for name, counts in existing.items():
        shares[fuel_types[name]] += counts[-1] / total
    return shares


@pytest.mark.slow
class TestNoIncentive:

    def test_invariants(self, manager):
        check_invariants(manager)

    def test_supply_never_binding(self, manager):
        """Deck validity: supply must be ample so the discrete choice model,
        not a supply constraint, is what keeps the alternative-fuel shares
        small (see BEHAVIOR.md, Mechanism isolated)."""
        for name, producer in manager.nodes.producers.items():
            development = producer.profile.get_development()
            maximum = producer.profile.get_maximum_development()
            assert np.all(development <= 0.5 * maximum), \
                f"Producer '{name}' approaches its development constraint"

    def test_methanol_share_marginal(self, market_shares):
        assert market_shares[FuelTypeID.METHANOL] <= MAX_METHANOL_SHARE + EPS_SHARE

    def test_ammonia_share_marginal(self, market_shares):
        assert market_shares[FuelTypeID.AMMONIA] <= MAX_AMMONIA_SHARE + EPS_SHARE

    def test_oil_and_methane_dominate(self, market_shares):
        dominant = market_shares[FuelTypeID.OIL] + market_shares[FuelTypeID.METHANE]
        assert dominant >= MIN_OIL_METHANE_SHARE - EPS_SHARE
