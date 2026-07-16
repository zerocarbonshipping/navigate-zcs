# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Metric-prefix and unit-string formatting for plot axes.

Pure numeric helpers with no domain or matplotlib dependency: pick the best
SI prefix for a magnitude and build the corresponding unit label (mass,
energy, cost, cargo-miles).
"""

import math


def find_best_metric_prefix(value, default=0, symbol=True):
    """

    Note: https://en.wikipedia.org/wiki/Metric_prefix

    Parameters
    ----------
    value : float
        Value from which to interpret order of magnitude.
    default : int
        Existing order of magnitude of value relative to base SI-unit.
    symbol : bool
        If true return a symbol (k, M, etc.). If false return a word (million, billion, etc.)

    Returns
    -------

    """

    value = abs(value)
    if value > 0.:
        order = math.floor(math.log10(value)) + default
    else:
        order = 1

    divisor = 1.
    prefix_symbol = ''      #
    prefix_short = ''       # short scale

    if order < 2:
        # nothing
        pass

    elif (order >= 3) and (order < 6):
        # kilo
        divisor = 1e3
        prefix_symbol = 'k'
        prefix_short = 'thousand'

    elif (order >= 6) and (order < 9):
        # mega
        divisor = 1e6
        prefix_symbol = 'M'
        prefix_short = 'million'

    elif (order >= 9) and (order < 12):
        # giga
        divisor = 1e9
        prefix_symbol = 'G'
        prefix_short = 'billion'

    elif (order >= 12) and (order < 15):
        # tera
        divisor = 1e12
        prefix_symbol = 'T'
        prefix_short = 'trillion'

    elif (order >= 15) and (order < 18):
        # peta
        divisor = 1e15
        prefix_symbol = 'P'
        prefix_short = 'quadrillion'

    elif (order >= 18) and (order < 21):
        # exa
        divisor = 1e18
        prefix_symbol = 'E'
        prefix_short = 'quintillion'

    if symbol:
        prefix = prefix_symbol
    else:
        prefix = prefix_short

    return int(divisor / 10 ** default), prefix


def get_best_unit(value, rate=True, default=0, symbol=True):
    suffix = ''
    if rate:
        suffix = '/year'

    divisor, prefix = find_best_metric_prefix(value, default, symbol)
    return divisor, prefix, suffix


def get_best_unit_mass(value, default=0, rate=True):
    divisor, prefix, suffix = get_best_unit(value, rate, default)
    unit = '{}t{}'.format(prefix, suffix)
    return divisor, unit


def get_best_unit_energy(value, default=0, rate=True):
    divisor, prefix, suffix = get_best_unit(value, rate, default)
    unit = '{}J{}'.format(prefix, suffix)
    return divisor, unit


def get_best_unit_cost(value, default=0, rate=True):
    divisor, prefix, suffix = get_best_unit(value, rate, default, symbol=False)
    unit = '{} USD{}'.format(prefix, suffix)
    return divisor, unit


def get_best_unit_cargo_miles(value, default=0, rate=True):
    divisor, prefix, suffix = get_best_unit(value, rate, default, symbol=False)
    unit = '{} cargo-miles{}'.format(prefix, suffix)
    return divisor, unit
