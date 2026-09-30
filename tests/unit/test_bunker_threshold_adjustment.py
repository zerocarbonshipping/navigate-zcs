# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the regulation right-hand-side update after threshold adjustment."""

from __future__ import annotations

import pytest

from navigate.bunker import solver_highs
from navigate.bunker.threshold_adjustment import _update_regulation_rhs_for_adjustment
from navigate.core.enum_ import RegulationMeasureID, RegulationSchemeID

# the LP below has a vertex optimum; HiGHS returns it to within its default
# primal feasibility tolerance of 1e-7
SOLUTION_TOLERANCE = 1e-6


class _StubRegulation:
    def __init__(self, scheme, measure, policed_vessels):
        self.scheme = scheme
        self.measure = measure
        self.policed_vessels = policed_vessels

    def vessel_is_policed(self, v):
        return v in self.policed_vessels


class _StubAlgorithm:
    def __init__(self, vessels, multipliers):
        self.vessels = dict.fromkeys(vessels)
        self.multipliers = multipliers
        self.adjusted_vessel_thresholds = {}
        self.regulation_measure = {}
        self.regulation_threshold_individual = {}
        self.regulation_rhs_individual = {}
        self.regulation_threshold_flexibility = {}
        self.regulation_rhs_flexibility = {}
        self.regulation_total_rhs_flexibility = {}


def _maximised_variable_under_threshold():
    """Return max x subject to x <= 0; its optimum is x = rhs of the constraint."""
    model = solver_highs.Model()
    x = model.addVar()
    x.Obj = -1.0
    threshold = model.addConstr(x <= 0.0)
    return model, x, threshold


@pytest.mark.parametrize(
    ("measure", "adjusted_threshold", "vessel_measure", "expected_rhs"),
    [
        # an absolute threshold is the right-hand side itself
        (RegulationMeasureID.ABSOLUTE, 7.0, 4.0, 7.0),
        # a per-cargo-mile threshold scales with the vessel's cargo-miles
        (RegulationMeasureID.TRANSPORT, 2.5, 4.0, 10.0),
    ],
)
def test_individual_threshold_constraint_takes_adjusted_threshold(
    measure, adjusted_threshold, vessel_measure, expected_rhs
):
    alg = _StubAlgorithm(["v1"], {"v1": 1.0})
    regulation = _StubRegulation(RegulationSchemeID.INDIVIDUAL, measure, {"v1"})
    model, x, threshold = _maximised_variable_under_threshold()
    alg.regulation_threshold_individual[("reg", "v1")] = threshold
    alg.adjusted_vessel_thresholds[("reg", "v1")] = adjusted_threshold
    alg.regulation_measure[("reg", "v1")] = vessel_measure

    _update_regulation_rhs_for_adjustment(alg, {"reg": regulation})
    model.optimize()
    solution = x.X

    assert threshold.rhs == expected_rhs
    assert solution == pytest.approx(expected_rhs, abs=SOLUTION_TOLERANCE)


def test_flexible_threshold_constraint_takes_multiplier_weighted_sum():
    # policed v1: 2.0 per cargo-mile * 3.0 cargo-miles * multiplier 2 = 12.0
    # policed v2: 1.0 per cargo-mile * 5.0 cargo-miles * multiplier 1 = 5.0
    # v3 is not policed and contributes nothing, so the fleet total is 17.0
    alg = _StubAlgorithm(["v1", "v2", "v3"], {"v1": 2.0, "v2": 1.0, "v3": 1.0})
    regulation = _StubRegulation(
        RegulationSchemeID.FLEXIBLE, RegulationMeasureID.TRANSPORT, {"v1", "v2"}
    )
    model, x, threshold = _maximised_variable_under_threshold()
    alg.regulation_threshold_flexibility["reg"] = threshold
    alg.adjusted_vessel_thresholds.update(
        {("reg", "v1"): 2.0, ("reg", "v2"): 1.0, ("reg", "v3"): 100.0}
    )
    alg.regulation_measure.update(
        {("reg", "v1"): 3.0, ("reg", "v2"): 5.0, ("reg", "v3"): 1.0}
    )

    _update_regulation_rhs_for_adjustment(alg, {"reg": regulation})
    model.optimize()
    solution = x.X

    assert threshold.rhs == 17.0
    assert solution == pytest.approx(17.0, abs=SOLUTION_TOLERANCE)
