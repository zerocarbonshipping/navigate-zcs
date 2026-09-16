# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Regression: carbon-levy pathway.

An oil/ammonia fleet under a ramping WTW carbon levy and no Regulation: the
levy prices fossil oil's pinned CO2 factor and is the only policy signal in
the deck, exercising the Levy node and the levy terms in the bunker LP, which
no other committed deck activates. The activation guards prove the levy is
actually collected throughout — a levy that stops collecting (an emission
factor pinned to zero, a jurisdiction emptied, include_vessel unset) would
leave the golden baseline covering nothing.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from helpers.baseline import (
    RUNNER_NOISE_ATOL,
    RUNNER_NOISE_RTOL,
    regen_or_compare,
)
from helpers.simulation import check_invariants, clear_output_dir, run_simulation

DECK_DIR = Path(__file__).resolve().parent / "simulations" / "carbon_levy"
BASELINE_DIR = Path(__file__).resolve().parent / "baselines" / "carbon_levy"


@pytest.fixture(scope="module")
def manager():
    clear_output_dir(DECK_DIR / "output")
    return run_simulation(DECK_DIR)


def check_activation(manager):
    """Deck validity: the levy is live and collects on every decision step."""
    levy = manager.nodes.levies["carbon_levy"]

    assert np.all(levy.level.get(manager.timeline) > 0.0), (
        "The levy level is not positive over the horizon: the deck no longer "
        "prices emissions"
    )

    # the first step only initializes expectations (guardrail convention)
    collected = levy.profile.get_collected()
    assert np.all(collected[1:] > 0.0), (
        "The levy stopped collecting: the deck no longer exercises the levy "
        "terms in the bunker LP"
    )

    # the ramp is sized to cross the deck's oil-vs-ammonia break-even
    # mid-horizon: without an actual transition the supply chain in the deck
    # is dead weight and the baseline covers only the collection arithmetic
    ammonia = manager.profile.get_consumed_energy()["ammonia_electro"]
    assert ammonia[-1] > 0.0, (
        "The levy no longer flips any consumption to ammonia: the transition "
        "phase of the deck is inert"
    )


@pytest.mark.slow
class TestCarbonLevy:
    def test_invariants(self, manager):
        check_invariants(manager)

    def test_levy_collects(self, manager):
        check_activation(manager)

    def test_matches_baseline(self, manager, regen_baselines_flag):
        regen_or_compare(
            manager,
            BASELINE_DIR,
            DECK_DIR / "output",
            regen=regen_baselines_flag,
            check_activation=check_activation,
            rtol=RUNNER_NOISE_RTOL,
            atol=RUNNER_NOISE_ATOL,
        )
