# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Regression: fuel-conversion pathway.

An oil-dominated fleet with a cheap liquid-market LNG alternative and methane
newbuilds disabled: existing vessels convert oil -> methane on their retrofit
cycles, so `navigate/fleet/conversion.py` is the only channel into the methane
type. The activation guards prove conversions actually occur and that the
deck's discounting inputs stay pinned (nonzero CostOfCapital, differing
lifetimes) — without them a should-be-caught discounting change could be
numerically inert here, and the golden baseline would be vacuous.
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

DECK_DIR = Path(__file__).resolve().parent / "simulations" / "fuel_conversion"
BASELINE_DIR = Path(__file__).resolve().parent / "baselines" / "fuel_conversion"

VESSEL_OIL = "container_15000_teu_ice_oil"
VESSEL_METHANE = "container_15000_teu_ice_methane"

# the deck is sized so conversions clearly exceed a single vessel and recur:
# a marginal single-cohort trickle would leave most of the mechanism untested
MINIMUM_CONVERTED_VESSELS = 1.0
MINIMUM_CONVERTING_STEPS = 2


@pytest.fixture(scope="module")
def manager():
    clear_output_dir(DECK_DIR / "output")
    return run_simulation(DECK_DIR)


def check_activation(manager):
    """Deck validity: conversions occur and stay discounting-sensitive."""
    fleet = manager.nodes.fleets["container_15000_teu"]
    conversions = fleet.profile.get_fuel_conversions()[(VESSEL_OIL, VESSEL_METHANE)]

    assert conversions.sum() > MINIMUM_CONVERTED_VESSELS, (
        "No meaningful oil -> methane conversion occurred: the deck no longer "
        "exercises navigate/fleet/conversion.py"
    )
    assert np.count_nonzero(conversions > 0.0) >= MINIMUM_CONVERTING_STEPS, (
        "Conversions collapsed into a single time-step"
    )

    oil = manager.nodes.vessels[VESSEL_OIL]
    methane = manager.nodes.vessels[VESSEL_METHANE]
    assert methane.cost_of_capital.get() > 0.0, (
        "Destination CostOfCapital is zero: the conversion NPV no longer "
        "responds to discounting changes"
    )
    assert oil.lifetime.get() != methane.lifetime.get(), (
        "Equal lifetimes: the levelization window no longer responds to "
        "operating-window changes"
    )


@pytest.mark.slow
class TestFuelConversion:
    def test_invariants(self, manager):
        check_invariants(manager)

    def test_conversions_occur(self, manager):
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
