# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
plot_fuel_type_supply_demand's fuel-type selection rule.

Shows a panel for a fuel type the deck declares a Fuel for, or that some
converter uses as a main or pilot fuel even without a declared Fuel -- fleet
aggregation sums demand by MainFuelTypes/PilotFuelTypes alone
(navigate/fleet/aggregation.py), so a converter can carry non-zero demand for
a type no Fuel declares.
"""

from __future__ import annotations

from types import SimpleNamespace

from navigate.core.enum_ import FuelTypeID
from navigate.output.plots.fuel_type_supply_demand import (
    _select_fuel_types,
    plot_fuel_type_supply_demand,
)


def _no_declared_fuels():
    return {fuel_type: [] for fuel_type in FuelTypeID}


def _converter(main, pilot=()):
    return SimpleNamespace(get_fuel_types=lambda: [*main, *pilot])


def test_select_fuel_types_is_declared_union_converter_types_in_order():
    fuel_type_to_fuels = _no_declared_fuels()
    fuel_type_to_fuels[FuelTypeID.AMMONIA] = ["ammonia_fuel"]  # declared, no converter

    converters = {
        "propulsion": _converter(main=[FuelTypeID.METHANOL]),  # converter only
        "electrical": _converter(main=[FuelTypeID.OIL], pilot=[FuelTypeID.METHANE]),
    }

    result = _select_fuel_types(fuel_type_to_fuels, converters)

    # FUEL_TYPE_ORDER is (OIL, LPG, METHANE, METHANOL, ETHANOL, AMMONIA, HYDROGEN,
    # ELECTRICITY); OIL and METHANE come from the converters, AMMONIA from the
    # declared Fuel, METHANOL from both -- each appears once, in that order.
    assert result == [
        FuelTypeID.OIL,
        FuelTypeID.METHANE,
        FuelTypeID.METHANOL,
        FuelTypeID.AMMONIA,
    ]


def test_select_fuel_types_empty_when_nothing_declares_or_uses_a_type():
    assert _select_fuel_types(_no_declared_fuels(), converters={}) == []


def test_plot_writes_no_file_with_no_fuel_types(tmp_path):
    manager = SimpleNamespace(
        dateline=None,
        nodes=SimpleNamespace(ports={}, fuels={}, converters={}),
        profile=None,
    )

    plot_fuel_type_supply_demand(manager, str(tmp_path))

    assert not (tmp_path / "fuel_type_supply_demand.png").exists()
