# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for enum-level invariants."""
from navigate.core.enum_ import EnergyDemandTypePortID


def test_port_energy_demand_types_are_ordered():
    # LP variable/constraint creation order follows this constant; an unordered
    # container (set) makes the LP row/column order vary between runs
    assert isinstance(EnergyDemandTypePortID, tuple)
