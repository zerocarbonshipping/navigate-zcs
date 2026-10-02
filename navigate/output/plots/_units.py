# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Metric-prefix and unit-string formatting for plot axes.

Pure numeric helpers with no domain or matplotlib dependency: pick the best
SI prefix for a magnitude and build the corresponding unit label (mass,
energy, cost, cargo-miles).
"""

from __future__ import annotations

import math


def find_best_metric_prefix(
    value: float, unit_order: int = 0, symbol: bool = True
) -> tuple[float, str]:
    """
    Return the divisor and metric prefix best matching the value's magnitude.

    Note: https://en.wikipedia.org/wiki/Metric_prefix

    Parameters
    ----------
    value
        Value from which to interpret order of magnitude.
    unit_order
        Order of magnitude of the value's unit relative to the base SI unit
        (9 for a value in GJ).
    symbol
        If true return a symbol (k, M, etc.). If false return a word (million,
        billion, etc.)

    Returns
    -------
    tuple[float, str]
        Divisor that scales the value to the prefixed unit, and the prefix.
    """
    value = abs(value)
    order = math.floor(math.log10(value)) + unit_order if value > 0.0 else 1

    divisor = 1.0
    prefix_symbol = ""
    prefix_short = ""  # short scale

    if 3 <= order < 6:
        divisor = 1e3
        prefix_symbol = "k"
        prefix_short = "thousand"

    elif 6 <= order < 9:
        divisor = 1e6
        prefix_symbol = "M"
        prefix_short = "million"

    elif 9 <= order < 12:
        divisor = 1e9
        prefix_symbol = "G"
        prefix_short = "billion"

    elif 12 <= order < 15:
        divisor = 1e12
        prefix_symbol = "T"
        prefix_short = "trillion"

    elif 15 <= order < 18:
        divisor = 1e15
        prefix_symbol = "P"
        prefix_short = "quadrillion"

    elif 18 <= order < 21:
        divisor = 1e18
        prefix_symbol = "E"
        prefix_short = "quintillion"

    prefix = prefix_symbol if symbol else prefix_short

    return divisor / 10**unit_order, prefix


def get_best_unit(
    value: float, rate: bool = True, unit_order: int = 0, symbol: bool = True
) -> tuple[float, str, str]:
    suffix = ""
    if rate:
        suffix = "/year"

    divisor, prefix = find_best_metric_prefix(value, unit_order, symbol)
    return divisor, prefix, suffix


def get_best_unit_mass(value: float, rate: bool = True) -> tuple[float, str]:
    divisor, prefix, suffix = get_best_unit(value, rate)
    unit = f"{prefix}t{suffix}"
    return divisor, unit


def get_best_unit_energy(value: float, unit_order: int = 0) -> tuple[float, str]:
    divisor, prefix, suffix = get_best_unit(value, True, unit_order)
    unit = f"{prefix}J{suffix}"
    return divisor, unit


def get_best_unit_cost(value: float, rate: bool = True) -> tuple[float, str]:
    divisor, prefix, suffix = get_best_unit(value, rate, symbol=False)
    unit = f"{prefix} USD{suffix}"
    return divisor, unit


def get_best_unit_cargo_miles(value: float, rate: bool = True) -> tuple[float, str]:
    divisor, prefix, suffix = get_best_unit(value, rate, symbol=False)
    unit = f"{prefix} cargo-miles{suffix}"
    return divisor, unit
