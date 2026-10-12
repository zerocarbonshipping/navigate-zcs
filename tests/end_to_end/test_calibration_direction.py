# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
A stronger decision sensitivity moves each choice toward its better option.

Each sensitivity is an odds ratio (docs/reference_manual/fleet.md and
producer.md): against a 10% higher cost, below 1 penalizes the dearer option;
against an NPV advantage, above 1 rewards the more valuable one. Pushing the
value away from 1 must therefore move the choice monotonically toward the
option that is better under the base deck's pinned inputs:

- InterFuelSensitivity: LNG costs 380/50 = 7.6 USD/GJ against oil's
  550/40 = 13.75, so the methane share of newbuilds rises as the ratio falls.
- TechnologySensitivity: the package of technology_uptake.inc saves 5% of the
  propulsion fuel for a CAPEX of 1 MUSD, a positive NPV, so its newbuild
  uptake rises with the ratio.
- FuelConversionSensitivity: converting an oil vessel to LNG for 10 MUSD
  (fuel_conversion.inc) pays back on the fuel price gap, so conversions rise
  with the ratio.

Only the direction is asserted, on the decided steps where the choice is made.
"""

from __future__ import annotations

import itertools

import numpy as np
import pytest

FLEET = "container_15000_teu"
OIL_VESSEL = "container_15000_teu_ice_oil"
METHANE_VESSEL = "container_15000_teu_ice_methane"
TECHNOLOGY = "combination_technology"

# USD, as CHEAP_CAPEX in test_technology_combinations.py
CAPEX = 1e6

# each sensitivity's values, from the weakest response to the strongest
INTER_FUEL = (0.9, 0.75, 0.5)
TECHNOLOGY_SENSITIVITY = (1.5, 2, 4)
FUEL_CONVERSION = (1.5, 2, 4)

pytestmark = pytest.mark.slow


def _fleet(results):
    return results.nodes.fleets[FLEET]


def _increasing(series):
    """Assert each run's values exceed the previous run's at every step."""
    for weaker, stronger in itertools.pairwise(series):
        assert np.all(stronger > weaker), (weaker, stronger)


def test_a_stronger_inter_fuel_sensitivity_favours_the_cheaper_fuel(
    run_combination,
):
    def methane_share(sensitivity):
        layer = ("inter_fuel_sensitivity.inc", {"sensitivity": sensitivity})
        newbuilds = _fleet(run_combination(layer)).profile.get_newbuilds()
        total = newbuilds[METHANE_VESSEL] + newbuilds[OIL_VESSEL]
        built = total > 0.0
        assert np.count_nonzero(built) >= 2, "the fleet must build"
        return newbuilds[METHANE_VESSEL][built] / total[built]

    _increasing([methane_share(s) for s in INTER_FUEL])


def test_a_stronger_technology_sensitivity_raises_the_uptake(run_combination):
    def uptake(sensitivity):
        fleet = _fleet(
            run_combination(
                ("technology_uptake.inc", {"capex": CAPEX}),
                ("technology_sensitivity.inc", {"sensitivity": sensitivity}),
            )
        )
        uptake = fleet.profile.get_newbuild_technology_uptake()
        newbuilds = fleet.profile.get_newbuilds()
        shares = []
        for vessel in (OIL_VESSEL, METHANE_VESSEL):
            built = newbuilds[vessel] > 0.0
            assert np.count_nonzero(built) >= 2, f"{vessel} is never built"
            shares.append(
                uptake[(vessel, TECHNOLOGY)][built] / newbuilds[vessel][built]
            )
        return np.concatenate(shares)

    _increasing([uptake(s) for s in TECHNOLOGY_SENSITIVITY])


def test_a_stronger_conversion_sensitivity_converts_more_vessels(run_combination):
    def conversions(sensitivity):
        fleet = _fleet(
            run_combination(
                ("fuel_conversion.inc", {}),
                ("fuel_conversion_sensitivity.inc", {"sensitivity": sensitivity}),
            )
        )
        converted = fleet.profile.get_fuel_conversions()[(OIL_VESSEL, METHANE_VESSEL)]
        return converted[1:]

    series = [conversions(s) for s in FUEL_CONVERSION]

    assert np.all(series[0] > 0.0), "the fleet must convert oil vessels"
    _increasing(series)
