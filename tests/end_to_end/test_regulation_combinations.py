# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Every Measure x Scheme x Scope x AllowThresholdAdjustment of a Regulation runs.

The regulation in simulations/combinations/regulation.inc sets a zero threshold,
which no vessel meets in any measure or scope, so every combination is
non-compliant at every step. Without adjustment, the whole emission is the gap:
it is charged at the remedial cost, and it does not depend on the measure that
states the threshold or on the scheme that pools it. That charge prices every
ton the fleet emits, so it must reach the fleet's decisions: the regulated
fleet emits less than an unregulated one. With adjustment, the threshold is
raised to what is achievable and nothing is left to remedy.
"""

from __future__ import annotations

import itertools

import numpy as np
import pytest

MEASURES = ("ABSOLUTE", "INTENSITY", "TRANSPORT", "TRANSPORT_NOMINAL")
SCHEMES = ("INDIVIDUAL", "FLEXIBLE")
SCOPES = ("WTT", "TTW", "WTW")

REGULATION = "combination_regulation"

# RemedialCost in regulation.inc, USD per unit of non-compliance
REMEDIAL_COST = 100.0

# the same emissions summed in a different order across measures and schemes
SUMMATION_RTOL = 1e-9

pytestmark = pytest.mark.slow


def _run(run_combination, measure, scheme, scope, adjustment):
    return run_combination(
        (
            "regulation.inc",
            {
                "measure": measure,
                "scheme": scheme,
                "scope": scope,
                "allow_threshold_adjustment": adjustment,
            },
        )
    )


def _profile(run_combination, measure, scheme, scope, adjustment):
    results = _run(run_combination, measure, scheme, scope, adjustment)
    return results.nodes.regulations[REGULATION].profile


@pytest.mark.parametrize(
    ("measure", "scheme", "scope"), list(itertools.product(MEASURES, SCHEMES, SCOPES))
)
def test_an_unmet_threshold_charges_every_emission(
    run_combination, measure, scheme, scope
):
    profile = _profile(run_combination, measure, scheme, scope, "FALSE")
    units = profile.get_remedial_units()

    assert np.all(units > 0.0), "a zero threshold must leave a gap at every step"
    np.testing.assert_allclose(
        profile.get_remedial_expenses(), REMEDIAL_COST * units, rtol=SUMMATION_RTOL
    )

    # the gap to a zero threshold is the whole emission, whichever measure states
    # the threshold and whether the scheme pools it
    reference = _profile(run_combination, "ABSOLUTE", "INDIVIDUAL", scope, "FALSE")
    np.testing.assert_allclose(
        units, reference.get_remedial_units(), rtol=SUMMATION_RTOL
    )


@pytest.mark.parametrize(
    ("measure", "scheme", "scope"), list(itertools.product(MEASURES, SCHEMES, SCOPES))
)
def test_an_unmet_threshold_lowers_emissions(run_combination, measure, scheme, scope):
    regulated = _run(run_combination, measure, scheme, scope, "FALSE")
    unregulated = run_combination()

    def wtw(results):
        return results.profile.get_total_equivalent_wtw().sum()

    assert wtw(regulated) < wtw(unregulated)


@pytest.mark.parametrize(
    ("measure", "scheme", "scope"), list(itertools.product(MEASURES, SCHEMES, SCOPES))
)
def test_threshold_adjustment_raises_the_threshold_to_compliance(
    run_combination, measure, scheme, scope
):
    profile = _profile(run_combination, measure, scheme, scope, "TRUE")

    assert np.all(profile.get_remedial_units() == 0.0)

    if scheme == "INDIVIDUAL":
        for vessel, threshold in profile.get_adjusted_vessel_threshold().items():
            assert np.all(threshold > 0.0), f"{vessel} threshold was not adjusted"
    else:
        assert np.all(profile.get_adjusted_shared_threshold() > 0.0)
