# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Scaling an input scales what it drives by the same factor.

A fleet's trade grows from its initial size (TradeGrowth is relative), the base
deck's fuels are liquid-market and no port or newbuild limit binds, so twice
the initial vessels is the same fleet twice over: every extensive quantity
doubles at every step and every intensive one stays put. A levy charges its
level per ton above the threshold, so twice the level collects twice as much
at the first step, before any fleet decision can respond.
"""

from __future__ import annotations

import numpy as np
import pytest

FLEET = "container_15000_teu"
LEVY = "combination_levy"

BASE_VESSELS = 500  # InitialVessels in 0_includes/fleet.inc
BASE_LEVEL = 100  # Level in levy.inc, USD/ton CO2-eq
FACTOR = 2

# Both runs solve the same problems scaled by an exact power of two, so only
# float rounding can separate them; none is observed, and 1e-9 leaves room
# for a reordered sum without hiding a real departure from proportionality.
SCALING_RTOL = 1e-9

pytestmark = pytest.mark.slow


def _scaled_fleet(run_combination, factor):
    layer = ("initial_vessels.inc", {"initial_vessels": BASE_VESSELS * factor})
    return run_combination(layer).nodes.fleets[FLEET]


@pytest.mark.parametrize(
    "getter",
    [
        "get_consumed_energy",
        "get_equivalent_wtw",
        "get_newbuilds",
        "get_existing_vessels",
        "get_fuel_expenses",
    ],
)
def test_twice_the_fleet_doubles_its_extensive_results(run_combination, getter):
    base = getattr(_scaled_fleet(run_combination, 1).profile, getter)()
    scaled = getattr(_scaled_fleet(run_combination, FACTOR).profile, getter)()

    assert scaled.keys() == base.keys()
    assert any(np.any(array > 0.0) for array in base.values()), f"{getter} is zero"
    for key, array in base.items():
        np.testing.assert_allclose(
            scaled[key], FACTOR * array, rtol=SCALING_RTOL, err_msg=str(key)
        )


def test_twice_the_levy_level_doubles_the_first_collection(run_combination):
    def collected(level):
        results = run_combination(
            ("levy.inc", {"scheme": "PENALTY", "scope": "WTW", "lower_threshold": 85}),
            ("levy_level.inc", {"level": level}),
        )
        return results.nodes.levies[LEVY].profile.get_collected()[0]

    base = collected(BASE_LEVEL)

    assert base > 0.0, "the levy must collect"
    assert collected(FACTOR * BASE_LEVEL) == pytest.approx(
        FACTOR * base, rel=SCALING_RTOL
    )
