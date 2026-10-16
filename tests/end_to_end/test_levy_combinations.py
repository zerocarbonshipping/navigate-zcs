# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Every Scheme x Scope x UpperThreshold of a Levy runs and collects with its sign.

Per scope, the lower threshold lies between the emission factors of LNG and
oil, so oil is penalized and LNG subsidized. The first step is read for the
comparisons across schemes: no fleet or speed decision has acted yet, so every
run burns the same fuel there and only the levy coefficient differs.
"""

from __future__ import annotations

import itertools

import numpy as np
import pytest

SCHEMES = ("PENALTY", "SUBSIDY", "BOTH")
SCOPES = ("WTT", "TTW", "WTW")

LEVY = "combination_levy"

# Emission factors of the base deck's fuels, from the inputs pinned in
# simulations/combinations/0_includes, in kg CO2-eq per GJ of effective energy,
# (1 - slip) * LHV:
#
#   oil (LHV 40, no slip): WTT 0.8/40 = 20.0, TTW 3.2/40 = 80.0, WTW 100.0
#   LNG (LHV 50, slip 0.01, methane GWP 30): WTT 0.45/49.5 = 9.1,
#       TTW (0.99*2.75 + 0.01*30)/49.5 = 61.1, WTW 70.1
#
# The lower threshold lies near the middle of each scope's gap between LNG and
# oil, so oil is penalized and LNG subsidized; the upper threshold lies between
# the lower one and oil, so the cap binds on oil. Each keeps at least 3 kg/GJ
# from either factor.
LOWER_THRESHOLD = {"WTT": 14.0, "TTW": 70.0, "WTW": 85.0}
UPPER_THRESHOLD = {"WTT": 17.0, "TTW": 75.0, "WTW": 92.0}

# the same coefficients summed in a different order
SUMMATION_RTOL = 1e-9

pytestmark = pytest.mark.slow


def _collected(run_combination, scheme, scope, upper):
    layers = [
        (
            "levy.inc",
            {
                "scheme": scheme,
                "scope": scope,
                "lower_threshold": LOWER_THRESHOLD[scope],
            },
        )
    ]
    if upper:
        layers.append(
            ("levy_upper_threshold.inc", {"upper_threshold": UPPER_THRESHOLD[scope]})
        )

    results = run_combination(*layers)
    return results.nodes.levies[LEVY].profile.get_collected()


@pytest.mark.parametrize(
    ("scheme", "scope", "upper"),
    list(itertools.product(SCHEMES, SCOPES, (False, True))),
)
def test_levy_collects_with_the_sign_of_its_scheme(
    run_combination, scheme, scope, upper
):
    collected = _collected(run_combination, scheme, scope, upper)

    assert np.all(collected != 0.0), "the levy must act at every step"
    if scheme == "PENALTY":
        assert np.all(collected > 0.0)
    elif scheme == "SUBSIDY":
        assert np.all(collected < 0.0)


@pytest.mark.parametrize(
    ("scope", "upper"), list(itertools.product(SCOPES, (False, True)))
)
def test_both_is_penalty_plus_subsidy(run_combination, scope, upper):
    penalty = _collected(run_combination, "PENALTY", scope, upper)[0]
    subsidy = _collected(run_combination, "SUBSIDY", scope, upper)[0]
    both = _collected(run_combination, "BOTH", scope, upper)[0]

    assert both == pytest.approx(penalty + subsidy, rel=SUMMATION_RTOL)


@pytest.mark.parametrize(
    ("scheme", "scope"), list(itertools.product(("PENALTY", "BOTH"), SCOPES))
)
def test_upper_threshold_caps_the_penalty(run_combination, scheme, scope):
    uncapped = _collected(run_combination, scheme, scope, upper=False)[0]
    capped = _collected(run_combination, scheme, scope, upper=True)[0]

    assert capped < uncapped


@pytest.mark.parametrize("scope", SCOPES)
def test_subsidy_ignores_the_upper_threshold(run_combination, scope):
    uncapped = _collected(run_combination, "SUBSIDY", scope, upper=False)
    capped = _collected(run_combination, "SUBSIDY", scope, upper=True)

    np.testing.assert_array_equal(capped, uncapped)
