# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the Producer node."""

from __future__ import annotations

import pytest

from navigate.core.expression import Expression
from navigate.core.nodes.producer import Producer


class TestJumpStartFraction:
    """A deck expression assigned to JumpStartFraction is evaluated where read."""

    @pytest.mark.parametrize(
        ("jump_start_fraction", "expected"),
        [
            pytest.param(0.1, 0.1, id="float"),
            pytest.param(Expression("0.1 + 0.05"), 0.15, id="expression"),
        ],
    )
    def test_get_evaluates_assigned_value(self, jump_start_fraction, expected):
        producer = Producer("producer")
        producer.set_jump_start_fraction(jump_start_fraction)

        assert producer.jump_start_fraction.get() == pytest.approx(expected)
