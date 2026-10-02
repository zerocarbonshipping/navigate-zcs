# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.output.plots._units."""

from __future__ import annotations

import pytest

from navigate.output.plots._units import (
    find_best_metric_prefix,
    get_best_unit,
    get_best_unit_cargo_miles,
    get_best_unit_cost,
    get_best_unit_energy,
    get_best_unit_mass,
)


@pytest.mark.parametrize(
    ("value", "divisor", "prefix"),
    [
        (0.0, 1, ""),
        (5.0, 1, ""),
        (500.0, 1, ""),  # order 2 falls in the gap: no prefix
        (1.5e3, 1000, "k"),
        (2.0e6, 1000000, "M"),
        (3.0e9, 1000000000, "G"),
        (4.0e12, 1000000000000, "T"),
        (-2.0e6, 1000000, "M"),  # magnitude only, sign ignored
    ],
)
def test_find_best_metric_prefix_symbol(value, divisor, prefix):
    assert find_best_metric_prefix(value) == (divisor, prefix)


def test_find_best_metric_prefix_word_scale():
    assert find_best_metric_prefix(2.0e6, symbol=False) == (1000000, "million")
    assert find_best_metric_prefix(3.0e9, symbol=False) == (1000000000, "billion")


def test_find_best_metric_prefix_default_offset():
    # default is the value's existing order of magnitude: a value already given in
    # millions (default=6) is picked up as 'M' with a relative divisor of 1.
    assert find_best_metric_prefix(2.0, default=6) == (1, "M")


@pytest.mark.parametrize(
    ("value", "default", "divisor", "prefix"),
    [
        # 0.5 GJ is below the GJ input unit: the divisor used to truncate to
        # int(1e6 / 1e9) == 0; it now scales the value up to 500 MJ instead.
        (0.5, 9, 1e-3, "M"),
        # 0.5 MW: the same below-input-unit truncation at a smaller default.
        (0.5, 6, 1e-3, "k"),
        # a zero value used to hit the same truncation (int(1 / 1e9) == 0),
        # dividing by it; it now divides by 1e-9, leaving a zero value zero.
        (0.0, 9, 1e-9, ""),
    ],
)
def test_find_best_metric_prefix_below_input_unit(value, default, divisor, prefix):
    assert find_best_metric_prefix(value, default=default) == (divisor, prefix)


@pytest.mark.parametrize(
    ("value", "default", "divisor", "prefix"),
    [
        (2.5e10, 0, 1e9, "G"),
        (5e3, 6, 1e3, "G"),
    ],
)
def test_find_best_metric_prefix_default_offset_unchanged(
    value, default, divisor, prefix
):
    assert find_best_metric_prefix(value, default=default) == (divisor, prefix)


def test_get_best_unit_rate_suffix():
    assert get_best_unit(2.0e6) == (1000000, "M", "/year")
    assert get_best_unit(2.0e6, rate=False) == (1000000, "M", "")


@pytest.mark.parametrize(
    ("func", "kwargs", "expected"),
    [
        (get_best_unit_mass, {}, (1000000, "Mt/year")),
        (get_best_unit_mass, {"rate": False}, (1000000, "Mt")),
        (get_best_unit_energy, {}, (1000000, "MJ/year")),
        (
            get_best_unit_cost,
            {},
            (1000000, "million USD/year"),
        ),  # cost uses the word scale
        (get_best_unit_cargo_miles, {}, (1000000, "million cargo-miles/year")),
        (get_best_unit_cargo_miles, {"rate": False}, (1000000, "million cargo-miles")),
    ],
)
def test_get_best_unit_wrappers(func, kwargs, expected):
    assert func(2.0e6, **kwargs) == expected
