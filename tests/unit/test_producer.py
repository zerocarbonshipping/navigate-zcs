# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the Producer node."""

from __future__ import annotations

import pytest

from navigate.core.expression import Expression
from navigate.core.nodes.producer import Producer
from navigate.core.nodes.variable import Variable


def _make_variable(value: float) -> Variable:
    """Build a Variable node holding value, the way a deck reference resolves."""
    variable = Variable("jump_start_variable")
    variable.set_value(value)
    return variable


class TestJumpStartFraction:
    """JumpStartFraction is read through .get(), whatever kind it is assigned."""

    @pytest.mark.parametrize(
        ("jump_start_fraction", "expected"),
        [
            pytest.param(0.1, 0.1, id="float"),
            pytest.param(Expression("0.1 + 0.05"), 0.15, id="expression"),
            pytest.param(_make_variable(0.2), 0.2, id="variable"),
        ],
    )
    def test_get_evaluates_assigned_value(self, jump_start_fraction, expected):
        producer = Producer("producer")
        producer.set_jump_start_fraction(jump_start_fraction)

        assert producer.jump_start_fraction.get() == pytest.approx(expected)
