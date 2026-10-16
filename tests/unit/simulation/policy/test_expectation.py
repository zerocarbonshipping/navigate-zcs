# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the policy expectation helpers.

Tests verify the correctness of:
  - _calculate_global_warming_potentials: a policy's GWP override is read at the
    model's emissions lifetime, or at the policy's own lifetime when it sets
    one, and an emission without an override falls back to its own GWP.
"""

from __future__ import annotations

import pytest

from navigate.core.nodes.curve import Curve
from navigate.core.nodes.emission import Emission
from navigate.core.nodes.regulation import Regulation
from navigate.core.table_data import TableData
from navigate.simulation.policy.expectation import _calculate_global_warming_potentials

# the model-wide emissions lifetime handed to the policy, years
MODEL_EMISSIONS_LIFETIME = 100.0


def _gwp_curve():
    # gwp against lifetime: 80 at 20 years, 30 at 100 years
    curve = Curve("gwp_methane")
    curve.set_table(TableData(rows=[[20.0, 80.0], [100.0, 30.0]]))
    curve.build_table()
    return curve


def _lifetime_times_three():
    curve = Curve("gwp_emission")
    curve.set_table(TableData(rows=[[0.0, 0.0], [100.0, 300.0]]))
    curve.build_table()
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
    regulation.fuels = []
    regulation._initialize_policy_dependencies({})
    if override is not None:
        regulation.set_global_warming_potential("methane", override())
    if policy_lifetime is not None:
        regulation.set_emissions_lifetime(policy_lifetime)

    expectation = regulation.expectation
    expectation.initialize(1, ["methane"], {}, {})
    _calculate_global_warming_potentials(
        regulation, {"methane": emission}, MODEL_EMISSIONS_LIFETIME
    )

    gwp = expectation.get_global_warming_potential("methane")
    assert gwp == pytest.approx(expected)
