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


class TestMinimumOfftakeDuration:
    """
    MinimumOfftakeDuration accepts any duration above zero.

    Pipeline planning rounds the duration up to whole years and reads that many
    years of demand, so a zero duration would read none.
    """

    @pytest.mark.parametrize("duration", [0.0, -1.0])
    def test_rejects_non_positive(self, duration):
        producer = Producer("producer")

        with pytest.raises(ValueError, match=r"must be > 0\.0"):
            producer.set_minimum_offtake_duration(duration)

    def test_accepts_sub_year(self):
        producer = Producer("producer")
        producer.set_minimum_offtake_duration(0.5)

        assert producer.minimum_offtake_duration.get() == pytest.approx(0.5)
