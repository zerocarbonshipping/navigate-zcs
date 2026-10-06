# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.output.plots._units."""

from __future__ import annotations

import pytest

from navigate.output.plots._units import find_best_metric_prefix


@pytest.mark.parametrize(
    ("value", "divisor", "prefix"),
    [
        (0.0, 1, ""),
        (500.0, 1, ""),  # order 2 falls in the gap: no prefix
        (1.5e3, 1000, "k"),
        (-2.0e6, 1000000, "M"),  # magnitude only, sign ignored
    ],
)
def test_find_best_metric_prefix_symbol(value, divisor, prefix):
    assert find_best_metric_prefix(value) == (divisor, prefix)


def test_find_best_metric_prefix_word_scale():
    assert find_best_metric_prefix(2.0e6, symbol=False) == (1000000, "million")
    assert find_best_metric_prefix(3.0e9, symbol=False) == (1000000000, "billion")


def test_find_best_metric_prefix_unit_order():
    # unit_order is the order of magnitude of the value's unit: a value already
    # given in millions (unit_order=6) is picked up as 'M' with a relative
    # divisor of 1.
    assert find_best_metric_prefix(2.0, unit_order=6) == (1, "M")


@pytest.mark.parametrize(
    ("value", "unit_order", "divisor", "prefix"),
    [
        # 0.5 GJ is below the GJ input unit: the divisor scales it up to 500 MJ
        (0.5, 9, 1e-3, "M"),
        # a zero value takes no prefix and a nonzero divisor, so it stays zero
        (0.0, 9, 1e-9, ""),
    ],
)
def test_find_best_metric_prefix_below_input_unit(value, unit_order, divisor, prefix):
    assert find_best_metric_prefix(value, unit_order=unit_order) == (divisor, prefix)


@pytest.mark.parametrize(
    ("value", "unit_order", "divisor", "prefix"),
    [
        (5e3, 6, 1e3, "G"),
    ],
)
def test_find_best_metric_prefix_above_input_unit(value, unit_order, divisor, prefix):
    assert find_best_metric_prefix(value, unit_order=unit_order) == (divisor, prefix)
