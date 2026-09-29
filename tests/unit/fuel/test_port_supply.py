# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for navigate.fuel.port_supply._align_finite_export_with_bunkering_limits.

Tests verify the correctness of the trim-and-redistribute mechanism that reconciles
a port's imported fuel supply with its bunkering limit:
  - an over-limit port is trimmed to its limit and the freed surplus reaches an
    under-limit port whose deficit can absorb it;
  - a surplus larger than the total deficit leaves every limited port exactly at
    its limit and drops the remainder;
  - a port with no bunkering limit set has no deficit of its own and absorbs
    whatever surplus the limited ports could not;
  - a port where bunkering is disallowed is excluded from the mechanism entirely;
  - the redistribution is applied independently at each masked time element, and
    an unmasked element is left untouched.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from navigate.fuel.port_supply import _align_finite_export_with_bunkering_limits

FUEL_NAME = "fuel_a"
FUEL = SimpleNamespace(name=FUEL_NAME)


class _StubExpectation:
    def __init__(self, limit):
        self._limit = np.asarray(limit, dtype=float)

    def get_bunkering_limit(self, fuel_name, idx):
        return self._limit


class _StubPort:
    def __init__(self, limit, allowed=True):
        self.expectation = _StubExpectation(limit)
        self._allowed = allowed

    def is_bunkering_allowed(self, fuel_name):
        return self._allowed


def _redistribute(limits, imports, mask, allowed=None):
    """Run the function under test and return each port's resulting import."""
    allowed = allowed or {}

    ports = {name: _StubPort(limits[name], allowed.get(name, True)) for name in limits}
    supplies = {
        name: {FUEL_NAME: np.asarray(imports[name], dtype=float)} for name in limits
    }

    _align_finite_export_with_bunkering_limits(
        supplies, FUEL, ports, np.s_[:], np.asarray(mask, dtype=bool)
    )

    return {name: supplies[name][FUEL_NAME] for name in limits}


# each row: limits, imports, mask, allowed overrides, expected result
CASES = {
    "over_and_under_limit_deficit_covers_surplus": (
        {"a": [10.0], "b": [100.0]},
        {"a": [30.0], "b": [30.0]},
        [True],
        None,
        # a is trimmed to its limit (10); its 20 surplus fully covers b's 70
        # deficit only in part - here the deficit (70) exceeds the surplus (20),
        # so all of it moves to b: b ends at 30 + 20 = 50
        {"a": [10.0], "b": [50.0]},
    ),
    "deficit_smaller_than_surplus_excess_dropped": (
        {"a": [10.0], "b": [20.0]},
        {"a": [50.0], "b": [15.0]},
        [True],
        None,
        # a's surplus (40) exceeds b's deficit (5): b is filled exactly to its
        # limit (20) and the remaining 35 has nowhere to go
        {"a": [10.0], "b": [20.0]},
    ),
    "unlimited_port_absorbs_remaining_surplus": (
        {"a": [10.0], "b": [np.inf]},
        {"a": [30.0], "b": [5.0]},
        [True],
        None,
        # b has no limit, so it never registers a deficit in stage one; a's
        # full 20 surplus is left over and is handed to b in stage two
        {"a": [10.0], "b": [25.0]},
    ),
    "disallowed_port_gets_nothing": (
        {"a": [10.0], "b": [100.0]},
        {"a": [30.0], "b": [5.0]},
        [True],
        {"b": False},
        # b is excluded from the mechanism entirely: it neither contributes
        # nor receives, so a's 20 surplus has nowhere to go and is dropped
        {"a": [10.0], "b": [5.0]},
    ),
    "mask_excludes_unmasked_time_elements": (
        {"a": [10.0, 10.0, 10.0], "b": [100.0, 100.0, 100.0]},
        {"a": [30.0, 999.0, 5.0], "b": [30.0, 999.0, 150.0]},
        [True, False, True],
        None,
        # index 0 repeats the first case (a over, b under); index 1 is
        # unmasked and must be left untouched; index 2 reverses the roles (a
        # under by 5, b over by 50): a is filled fully to its limit (10) and
        # b is trimmed to its limit (100), dropping the rest of its surplus
        {"a": [10.0, 999.0, 10.0], "b": [50.0, 999.0, 100.0]},
    ),
}


@pytest.mark.parametrize(
    ("limits", "imports", "mask", "allowed", "expected"),
    list(CASES.values()),
    ids=list(CASES.keys()),
)
def test_redistribution(limits, imports, mask, allowed, expected):
    result = _redistribute(limits, imports, mask, allowed)

    for port_name, values in expected.items():
        assert result[port_name] == pytest.approx(values)
