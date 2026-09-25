# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for Regulation threshold validation, profile output and GWP lookup."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from navigate.core.expectations import RegulationExpectation
from navigate.core.expression import Expression
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.emission import Emission
from navigate.core.nodes.regulation import Regulation
from navigate.core.table_data import TableData

# the model-wide emissions lifetime handed to the policy, years
MODEL_EMISSIONS_LIFETIME = 100.0


def _make_regulation(scheme, measure, vessels=("v1", "v2")):
    regulation = Regulation("reg")
    regulation.set_scheme(scheme)
    regulation.set_measure(measure)

    regulation.jurisdiction = [MagicMock()]
    regulation.emissions = [MagicMock()]
    regulation.fuels = [MagicMock()]

    regulation.include_vessel = dict.fromkeys(vessels, True)
    regulation.vessel_threshold = dict.fromkeys(vessels)

    return regulation


@pytest.mark.parametrize(
    ("scheme", "measure"),
    [
        ("INDIVIDUAL", "ABSOLUTE"),
        ("FLEXIBLE", "TRANSPORT"),
    ],
)
def test_initialize_raises_for_included_vessel_without_threshold(scheme, measure):
    # the guard is scheme/measure-independent; these two combinations stand in for the
    # full cross product
    regulation = _make_regulation(scheme, measure)
    regulation.set_vessel_threshold("v1", 10.0)

    with pytest.raises(ValueError, match="no vessel_threshold"):
        regulation.initialize()


def test_initialize_ignores_excluded_vessels_without_threshold():
    regulation = _make_regulation("INDIVIDUAL", "ABSOLUTE")
    regulation.include_vessel["v2"] = False
    regulation.set_vessel_threshold("v1", 10.0)

    regulation.initialize()


def test_calculate_profile_writes_policed_vessel_thresholds():
    regulation = _make_regulation("FLEXIBLE", "INTENSITY")
    regulation.set_vessel_threshold("*", 10.0)
    regulation.in_jurisdiction_vessel = {"v1": True, "v2": False}
    regulation.initialize()

    regulation.profile = MagicMock()
    regulation.calculate_profile(idx=0)

    regulation.profile.set_vessel_threshold.assert_called_once_with(0, "v1", 10.0)


def test_jurisdiction_rejects_an_expression():
    # a jurisdiction is a list of ports, read as nodes and never evaluated
    regulation = Regulation("reg")

    with pytest.raises(ValueError, match="nodes of type Port, but got expression"):
        regulation.set_jurisdiction([Expression('Port("x")')])


def _gwp_curve():
    # gwp against lifetime: 80 at 20 years, 30 at 100 years
    curve = Curve("gwp_methane")
    curve.set_table(TableData(rows=[[20.0, 80.0], [100.0, 30.0]]))
    return curve


def _lifetime_times_three():
    curve = Curve("gwp_emission")
    curve.set_table(TableData(rows=[[0.0, 0.0], [100.0, 300.0]]))
    return curve


@pytest.mark.parametrize(
    ("override", "policy_lifetime", "expected"),
    [
        # a curve override is read at the model lifetime: the 100-year row
        (_gwp_curve, None, 30.0),
        # the policy's own lifetime replaces the model's: the 20-year row
        (_gwp_curve, 20.0, 80.0),
        # a number does not depend on the lifetime
        (lambda: 25.0, 20.0, 25.0),
        # no override falls back to the emission's gwp, 3 x the lifetime here
        (None, 20.0, 60.0),
    ],
)
def test_policy_global_warming_potential_is_read_at_emissions_lifetime(
    override, policy_lifetime, expected
):
    emission = Emission("methane")
    emission.set_global_warming_potential(_lifetime_times_three())

    regulation = Regulation("reg")
    regulation.emissions = [emission]
    regulation._initialize_policy_dependencies({})
    if override is not None:
        regulation.set_global_warming_potential("methane", override())
    if policy_lifetime is not None:
        regulation.set_emissions_lifetime(policy_lifetime)

    expectation = RegulationExpectation()
    expectation.initialize(1, ["methane"], {})
    regulation._calculate_policy_expectations(
        expectation, {"methane": emission}, MODEL_EMISSIONS_LIFETIME
    )

    assert expectation.get_global_warming_potential("methane") == pytest.approx(
        expected
    )
