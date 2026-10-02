# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Guardrail tests for the shared fuel label/colour/order tables.

The plot modules key off :data:`FUEL_TYPE_LABEL` / :data:`FUEL_TYPE_COLOR` (per
fuel type) and :data:`FUEL_LABEL` / :data:`FUEL_COLOR` (per individual fuel), and
iterate the ordering tuples :data:`FUEL_TYPE_ORDER` / :data:`FUEL_ORDER`. This
test makes sure the tables stay in sync -- e.g. a name in an ordering must have a
label and a colour, else it silently drops out of (or crashes) a stacked plot.
"""

from __future__ import annotations

from navigate.core.enum_ import FuelTypeID
from navigate.output.plots._labels import (
    FUEL_COLOR,
    FUEL_LABEL,
    FUEL_ORDER,
    FUEL_TYPE_COLOR,
    FUEL_TYPE_LABEL,
    FUEL_TYPE_ORDER,
)


def test_fuel_type_tables_cover_every_member():
    """A fuel type missing here crashes or drops out of every plot keying by it."""
    all_fuel_types = set(FuelTypeID)

    assert set(FUEL_TYPE_ORDER) == all_fuel_types
    assert set(FUEL_TYPE_LABEL) == all_fuel_types
    assert set(FUEL_TYPE_COLOR) == all_fuel_types
    assert len(FUEL_TYPE_ORDER) == len(set(FUEL_TYPE_ORDER))

    assert set(FUEL_ORDER) <= set(FUEL_LABEL)
    assert set(FUEL_ORDER) <= set(FUEL_COLOR)
    assert len(FUEL_ORDER) == len(set(FUEL_ORDER))
