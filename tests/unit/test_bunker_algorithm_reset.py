# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the per-time-step reset of BunkerAlgorithm's dynamic state."""

from __future__ import annotations

from navigate.bunker.bunker_algorithm import BunkerAlgorithm


def test_reset_targets_only_declared_attributes():
    """
    A reset assigning to a name absent from __init__ silently orphans the container.

    This is a regression guard for regulation_emission_coefficient.
    """
    algo = BunkerAlgorithm()
    declared = set(vars(algo))

    algo._reset_dynamic_properties()

    assert set(vars(algo)) == declared
