# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
plot_global_fuel_type_consumed's fuel-type selection rule.

Shows a stack layer only for a fuel type the deck declares a Fuel for.
get_fuel_type_energy() is built from bunkered fuel mass, which is keyed only
by declared Fuel names, so it is exactly zero for a type no Fuel declares.
"""

from __future__ import annotations

from types import SimpleNamespace

from navigate.core.enum_ import FuelTypeID
from navigate.output.plots.global_fuel_type_consumed import (
    _select_fuel_types,
    plot_global_fuel_type_consumed,
)


def _no_declared_fuels():
    return {fuel_type: [] for fuel_type in FuelTypeID}


def test_select_fuel_types_is_declared_fuel_types_in_order():
    fuel_type_to_fuels = _no_declared_fuels()
    fuel_type_to_fuels[FuelTypeID.METHANOL] = ["methanol_fuel"]
    fuel_type_to_fuels[FuelTypeID.OIL] = ["oil_fuel"]

    result = _select_fuel_types(fuel_type_to_fuels)

    # FUEL_TYPE_ORDER puts OIL before METHANOL.
    assert result == [FuelTypeID.OIL, FuelTypeID.METHANOL]


def test_select_fuel_types_empty_when_no_fuel_declared():
    assert _select_fuel_types(_no_declared_fuels()) == []


def test_plot_writes_no_file_with_no_fuel_types(tmp_path):
    results = SimpleNamespace(
        dateline=None,
        nodes=SimpleNamespace(fuels={}),
        profile=SimpleNamespace(get_fuel_type_energy=lambda: {}),
    )

    plot_global_fuel_type_consumed(results, tmp_path)

    assert not (tmp_path / "global_fuel_type_consumed.png").exists()
