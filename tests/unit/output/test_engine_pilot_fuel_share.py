# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
plot_engine_pilot_fuel_share's fuel-type selection and minimum-share rules.

Shows a panel per vessel.primary_fuel_type that has one of its own converters
dual-fuel and listing that primary type among its main fuel types.
get_pilot_fuel_share() keys its data by vessel.primary_fuel_type (every fuel a
vessel bunkers is recorded under that single type, see
navigate/bunker/transfer/bunker.py), so a vessel whose primary type differs
from one of its converters' main fuel types is excluded, keeping the share
and its minimum comparable.
"""

from __future__ import annotations

from types import SimpleNamespace

from navigate.core.enum_ import FuelTypeID
from navigate.output.plots.engine_pilot_fuel_share import (
    _minimum_pilot_share,
    _select_fuel_types,
    plot_engine_pilot_fuel_share,
)


def _converter(main, pilot=(), minimum_pilot_fuel=0.0):
    return SimpleNamespace(
        main_fuel_types=list(main),
        pilot_fuel_types=list(pilot),
        is_dual_fuel=lambda: bool(pilot),
        minimum_pilot_fuel=SimpleNamespace(get=lambda: minimum_pilot_fuel),
    )


def _vessel(primary_fuel_type, converters):
    return SimpleNamespace(
        primary_fuel_type=primary_fuel_type,
        power_system=SimpleNamespace(get_converters=lambda: converters),
    )


def test_select_fuel_types_is_vessel_primary_type_with_matching_converter():
    # a methanol-primary vessel whose propulsion is dual-fuel, methanol main,
    # oil pilot -- a matching converter, selected
    methanol_vessel = _vessel(
        FuelTypeID.METHANOL,
        [_converter(main=[FuelTypeID.METHANOL], pilot=[FuelTypeID.OIL])],
    )
    # an oil-primary vessel carrying a second, dual-fuel converter whose main
    # fuel types include OIL alongside methane -- a matching converter,
    # selected
    oil_vessel_matching = _vessel(
        FuelTypeID.OIL,
        [
            _converter(main=[FuelTypeID.OIL]),
            _converter(
                main=[FuelTypeID.OIL, FuelTypeID.METHANE], pilot=[FuelTypeID.OIL]
            ),
        ],
    )
    # an oil-primary vessel (its propulsion converter, oil-only, dominates
    # power) whose only dual-fuel converter's main type is METHANOL, not OIL
    # -- no matching converter, excluded
    oil_vessel_mismatched = _vessel(
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
        "oil_matching": oil_vessel_matching,
        "oil_mismatched": oil_vessel_mismatched,
        "ammonia": ammonia_vessel,
    }

    result = _select_fuel_types(vessels)

    # oil_vessel_mismatched and ammonia_vessel are both excluded; FUEL_TYPE_ORDER
    # puts OIL before METHANOL.
    assert result == [FuelTypeID.OIL, FuelTypeID.METHANOL]


def test_select_fuel_types_empty_with_no_dual_fuel_converter():
    vessels = {"oil": _vessel(FuelTypeID.OIL, [_converter(main=[FuelTypeID.OIL])])}

    assert _select_fuel_types(vessels) == []


def test_minimum_pilot_share_is_max_over_matching_converters_per_primary_type():
    low = _vessel(
        FuelTypeID.METHANOL,
        [
            _converter(
                main=[FuelTypeID.METHANOL],
                pilot=[FuelTypeID.OIL],
                minimum_pilot_fuel=0.05,
            )
        ],
    )
    high = _vessel(
        FuelTypeID.METHANOL,
        [
            _converter(
                main=[FuelTypeID.METHANOL],
                pilot=[FuelTypeID.OIL],
                minimum_pilot_fuel=0.10,
            )
        ],
    )
    # not in fuel_types, excluded even with a larger minimum
    other = _vessel(
        FuelTypeID.AMMONIA,
        [
            _converter(
                main=[FuelTypeID.AMMONIA],
                pilot=[FuelTypeID.OIL],
                minimum_pilot_fuel=0.90,
            )
        ],
    )

    vessels = {"low": low, "high": high, "other": other}

    result = _minimum_pilot_share(vessels, [FuelTypeID.METHANOL])

    assert result == {FuelTypeID.METHANOL: 0.10}


def test_plot_writes_no_file_with_no_dual_fuel_vessel(tmp_path):
    vessels = {"oil": _vessel(FuelTypeID.OIL, [_converter(main=[FuelTypeID.OIL])])}
    manager = SimpleNamespace(
        dateline=None, nodes=SimpleNamespace(vessels=vessels), profile=None
    )

    plot_engine_pilot_fuel_share(manager, str(tmp_path))

    assert not (tmp_path / "engine_pilot_fuel_share.png").exists()
