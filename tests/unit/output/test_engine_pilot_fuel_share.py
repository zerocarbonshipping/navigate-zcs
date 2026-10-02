# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
plot_engine_pilot_fuel_share's fuel-type selection rule.

Shows a panel per vessel.primary_fuel_type that has at least one dual-fuel
converter -- never per converter.main_fuel_types. get_pilot_fuel_share() keys
its data by vessel.primary_fuel_type (every fuel a vessel bunkers is recorded
under that single type, see navigate/bunker/transfer/bunker.py), so a vessel
whose primary type differs from one of its converter's own main fuel type
must still be selected, and keyed, by the vessel's primary type (#393, #399).
"""

from __future__ import annotations

from types import SimpleNamespace

from navigate.core.enum_ import FuelTypeID
from navigate.output.plots.engine_pilot_fuel_share import (
    _select_fuel_types,
    plot_engine_pilot_fuel_share,
)


def _converter(main, pilot=()):
    return SimpleNamespace(
        main_fuel_types=list(main),
        pilot_fuel_types=list(pilot),
        is_dual_fuel=lambda: bool(pilot),
    )


def _vessel(primary_fuel_type, converters):
    return SimpleNamespace(
        primary_fuel_type=primary_fuel_type,
        power_system=SimpleNamespace(get_converters=lambda: converters),
    )


def test_select_fuel_types_is_vessel_primary_type_not_converter_main_type():
    # a methanol-primary vessel whose propulsion is dual-fuel, methanol main,
    # oil pilot -- the ordinary case, where the two keys agree
    methanol_vessel = _vessel(
        FuelTypeID.METHANOL,
        [_converter(main=[FuelTypeID.METHANOL], pilot=[FuelTypeID.OIL])],
    )
    # an oil-primary vessel (its propulsion converter, oil-only, dominates
    # power) that also carries a second, dual-fuel converter whose own main
    # type is METHANOL -- the mismatch case
    oil_vessel = _vessel(
        FuelTypeID.OIL,
        [
            _converter(main=[FuelTypeID.OIL]),
            _converter(main=[FuelTypeID.METHANOL], pilot=[FuelTypeID.OIL]),
        ],
    )
    # an ammonia-primary vessel with no dual-fuel converter at all
    ammonia_vessel = _vessel(
        FuelTypeID.AMMONIA, [_converter(main=[FuelTypeID.AMMONIA])]
    )

    vessels = {
        "methanol": methanol_vessel,
        "oil": oil_vessel,
        "ammonia": ammonia_vessel,
    }

    result = _select_fuel_types(vessels)

    # the oil vessel is selected by its own primary type (OIL), not by its
    # dual-fuel converter's main type (METHANOL); the ammonia vessel is
    # excluded, as none of its converters are dual-fuel. FUEL_TYPE_ORDER puts
    # OIL before METHANOL.
    assert result == [FuelTypeID.OIL, FuelTypeID.METHANOL]


def test_select_fuel_types_empty_with_no_dual_fuel_converter():
    vessels = {"oil": _vessel(FuelTypeID.OIL, [_converter(main=[FuelTypeID.OIL])])}

    assert _select_fuel_types(vessels) == []


def test_plot_writes_no_file_with_no_dual_fuel_vessel(tmp_path):
    vessels = {"oil": _vessel(FuelTypeID.OIL, [_converter(main=[FuelTypeID.OIL])])}
    manager = SimpleNamespace(
        dateline=None, nodes=SimpleNamespace(vessels=vessels), profile=None
    )

    plot_engine_pilot_fuel_share(manager, str(tmp_path))

    assert not (tmp_path / "engine_pilot_fuel_share.png").exists()
