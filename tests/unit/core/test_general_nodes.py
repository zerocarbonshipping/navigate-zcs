# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the general-node settings a run reads as plain numbers.

The bunker algorithm and the GWP lookup read these settings as a bare int or
float, never through a getter, so a setter must refuse anything else at the
deck line instead of letting the run fail on it.
"""

from __future__ import annotations

import pytest

from navigate.core.expression import Expression
from navigate.core.general_nodes.bunker_options import BunkerOptions
from navigate.core.general_nodes.model_definition import ModelDefinition


def test_fair_share_maximum_iterations_rejects_a_fraction():
    with pytest.raises(
        ValueError, match=r"only allows assignment of integers, but got 2\.5"
    ):
        BunkerOptions().set_fair_share_maximum_iterations(2.5)


@pytest.mark.parametrize(
    ("node_class", "setter_name", "message"),
    [
        (
            BunkerOptions,
            "set_fair_share_maximum_iterations",
            "requires a scalar, but got expression",
        ),
        (
            BunkerOptions,
            "set_solution_tolerance",
            "only allows assignment of scalars, but got expression",
        ),
        (
            BunkerOptions,
            "set_fair_share_tolerance",
            "only allows assignment of scalars, but got expression",
        ),
        (
            ModelDefinition,
            "set_emissions_lifetime",
            "only allows assignment of scalars, but got expression",
        ),
    ],
    ids=[
        "FairShareMaximumIterations",
        "SolutionTolerance",
        "FairShareTolerance",
        "EmissionsLifetime",
    ],
)
def test_a_setting_read_as_a_number_rejects_an_expression(
    node_class, setter_name, message
):
    with pytest.raises(ValueError, match=message):
        getattr(node_class(), setter_name)(Expression("1 + 2"))
