# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the LP get-or-create build helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from navigate.bunker._build import add_variable, get_constraint

KEY = ("vessel_a", 2, "ammonia")


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(
            lambda alg, container: add_variable(alg, container, KEY, "bunker"),
            id="variable",
        ),
        pytest.param(
            lambda alg, container: get_constraint(alg, container, KEY, "<=", "cap"),
            id="constraint",
        ),
    ],
)
def test_an_existing_element_is_reused_not_rebuilt(build):
    # the algorithm has no model, so building a new element would fail
    alg = SimpleNamespace(model=None)
    existing = object()
    container = {KEY: existing}

    build(alg, container)

    assert container == {KEY: existing}
