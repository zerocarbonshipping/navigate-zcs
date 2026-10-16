# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
A dearer LNG moves each fleet decision away from LNG.

Raising LNG's bunker price keeps it the cheaper fuel per GJ but narrows its
lead over oil, so every decision that weighs fuel cost must respond in the same
direction: a newbuild is less likely to burn LNG, an oil vessel is less likely
to convert to LNG, and a methane vessel sails slower, since each knot now costs
more fuel expense. Only the direction is asserted, read off the decided steps:
the first step only initializes expectations.
"""

from __future__ import annotations

import numpy as np
import pytest

FLEET = "container_15000_teu"
OIL_VESSEL = "container_15000_teu_ice_oil"
METHANE_VESSEL = "container_15000_teu_ice_methane"

# USD/ton. Per GJ, against oil's 550/40 = 13.75 in 0_includes/fuels_ports.inc,
# LNG rises from the base deck's 380/50 = 7.6 to 480/50 = 9.6.
DEARER_LNG_PRICE = 480

pytestmark = pytest.mark.slow


def _run(run_combination, dearer, conversion):
    layers = []
    if dearer:
        layers.append(("lng_price.inc", {"lng_price": DEARER_LNG_PRICE}))
    if conversion:
        layers.append(("fuel_conversion.inc", {}))
    return run_combination(*layers)


def _fleet(results):
    return results.nodes.fleets[FLEET]


def test_dearer_lng_lowers_the_methane_share_of_newbuilds(run_combination):
    def methane_share(results):
        newbuilds = _fleet(results).profile.get_newbuilds()
        methane = newbuilds[METHANE_VESSEL].sum()
        assert methane > 0.0, "the fleet must build methane vessels"
        return methane / (methane + newbuilds[OIL_VESSEL].sum())

    base = methane_share(_run(run_combination, dearer=False, conversion=False))
    dearer = methane_share(_run(run_combination, dearer=True, conversion=False))

    assert dearer < base


def test_dearer_lng_lowers_the_conversions_to_methane(run_combination):
    def conversions(results):
        lane = (OIL_VESSEL, METHANE_VESSEL)
        return _fleet(results).profile.get_fuel_conversions()[lane].sum()

    base = conversions(_run(run_combination, dearer=False, conversion=True))
    dearer = conversions(_run(run_combination, dearer=True, conversion=True))

    assert base > 0.0, "the base fleet must convert oil vessels"
    assert dearer < base


def test_dearer_lng_slows_the_methane_vessels(run_combination):
    def speed(results):
        (vessel,) = (v for v in _fleet(results).vessels if v.name == METHANE_VESSEL)
        return vessel.profile.get_optimal_speed()[1:]

    base = speed(_run(run_combination, dearer=False, conversion=False))
    dearer = speed(_run(run_combination, dearer=True, conversion=False))

    assert np.all(dearer < base)
