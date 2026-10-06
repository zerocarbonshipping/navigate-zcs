# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.fuel.port_supply: producer import and bunkering limits."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from navigate.core import Scalar
from navigate.core.profiles.port_profile import PortProfile
from navigate.fuel.port_supply import (
    _align_export_with_bunkering_limits,
    _calculate_import_from_liquid_market,
    _calculate_import_from_producers,
)

TIMELINE = np.array([0.0])

FUEL_NAME = "fuel_a"
# PortProfile.initialize reads liquid_market to pick the bunker-supply-mass
# default and the heating value to convert mass to energy; 1.0 keeps the two
# numerically identical
FUEL = SimpleNamespace(
    name=FUEL_NAME, liquid_market=False, lower_heating_value=Scalar(1.0)
)
EMISSION_NAME = "carbon_dioxide"
EMISSIONS = {EMISSION_NAME: SimpleNamespace(global_warming_potential=Scalar(1.0))}


class _PortExpectation:
    def __init__(self, limit, handling_cost, overwrite):
        self.limit = np.asarray(limit, dtype=float)
        self.handling_cost = np.asarray(handling_cost, dtype=float)
        self.overwrite = None if overwrite is None else np.asarray(overwrite, float)
        self.price = None
        self.wtt = {}
        self.supply = None

    def get_shape(self, start=0):
        return self.handling_cost[start:].shape

    def get_bunkering_limit(self, fuel_name, idx):
        return self.limit[idx]

    def get_handling_cost(self, fuel_name, idx):
        return self.handling_cost[idx]

    def get_bunker_price_overwrite(self, fuel_name, idx):
        # a view into stored state, as the real getter returns
        return self.overwrite[idx]

    def get_bunker_price(self, fuel_name, idx):
        return self.price

    def set_bunker_price(self, idx, fuel_name, price):
        self.price = price

    def set_bunker_wtt(self, idx, fuel_name, emission_name, wtt):
        self.wtt[emission_name] = wtt

    def set_bunker_supply(self, idx, fuel_name, supply):
        self.supply = supply


class _Port:
    def __init__(self, limit=(np.inf,), handling_cost=None, overwrite=None):
        if handling_cost is None:
            handling_cost = np.zeros(len(limit))

        self.bunkering_allowed = {FUEL_NAME: True}
        self.bunker_price_overwrite = {FUEL_NAME: overwrite}
        self.bunker_wtt_overwrite = {(FUEL_NAME, EMISSION_NAME): None}
        self.expectation = _PortExpectation(limit, handling_cost, overwrite)

        # a real PortProfile, so the supply is read back exactly as production
        # code writes it
        self.profile = PortProfile()
        self.profile.initialize(
            timeline=np.arange(len(limit), dtype=float),
            emissions=EMISSIONS,
            fuels={FUEL_NAME: FUEL},
            emissions_lifetime=100.0,
        )

    def is_bunkering_allowed(self, fuel_name):
        return self.bunkering_allowed[fuel_name]


def _make_producer(export_distribution, production, delivered_cost, wtt=0.0):
    """Build a one-plant producer delivering at the same cost to every port."""
    plant = SimpleNamespace(
        name="plant",
        fuel=FUEL,
        expectation=SimpleNamespace(
            get_expected_delivered_cost=lambda port_name, idx: delivered_cost,
            get_expected_delivered_wtt=lambda port_name, emission_name, idx: wtt,
        ),
    )
    production = np.asarray(production, dtype=float)
    expectation = SimpleNamespace(
        get_export_distribution=lambda idx: export_distribution,
        get_expected_production=lambda plant_name, idx: production[idx],
    )

    return SimpleNamespace(plants=[plant], expectation=expectation)


# ---------------------------------------------------------------------------
# _align_export_with_bunkering_limits: surplus/deficit redistribution
# ---------------------------------------------------------------------------


def _redistribute(limits, imports, allowed=None):
    """Run the function under test and return each port's resulting import."""
    allowed = allowed or {}

    ports = {name: _Port(limit=limits[name]) for name in limits}
    for name, port in ports.items():
        port.bunkering_allowed[FUEL_NAME] = allowed.get(name, True)
    supplies = {
        name: {FUEL_NAME: np.asarray(imports[name], dtype=float)} for name in limits
    }

    _align_export_with_bunkering_limits(supplies, FUEL, ports, np.s_[:])

    return {name: supplies[name][FUEL_NAME] for name in limits}


# each row: limits, imports, allowed overrides, expected result
CASES = {
    "over_and_under_limit": (
        {"a": [10.0], "b": [100.0]},
        {"a": [30.0], "b": [30.0]},
        None,
        # a is trimmed to its limit (10); its 20 surplus is short of b's 70
        # deficit, so all of it moves to b: b ends at 30 + 20 = 50
        {"a": [10.0], "b": [50.0]},
    ),
    "disallowed_port_gets_nothing": (
        {"a": [10.0], "b": [100.0]},
        {"a": [30.0], "b": [5.0]},
        {"b": False},
        # b is excluded from the mechanism entirely: it neither contributes
        # nor receives, so a's 20 surplus has nowhere to go and is dropped
        {"a": [10.0], "b": [5.0]},
    ),
    "two_deficit_ports_share_proportionally_when_deficit_exceeds_surplus": (
        {"a": [10.0], "b1": [70.0], "b2": [100.0]},
        {"a": [40.0], "b1": [10.0], "b2": [10.0]},
        None,
        # a's 30 surplus is short of b1 and b2's combined 150 deficit (60 and
        # 90), so each gets only its proportional share: 60/150*30=12 and
        # 90/150*30=18 - an implementation that sent all 30 to one of them
        # would fail this
        {"a": [10.0], "b1": [22.0], "b2": [28.0]},
    ),
    "two_deficit_ports_both_reach_their_limit_when_surplus_exceeds_deficit": (
        {"a": [10.0], "b1": [20.0], "b2": [50.0]},
        {"a": [110.0], "b1": [10.0], "b2": [30.0]},
        None,
        # a's 100 surplus covers b1 and b2's combined 30 deficit (10 and 20)
        # with room to spare: both are filled exactly to their own limit and
        # the remaining 70 has nowhere to go
        {"a": [10.0], "b1": [20.0], "b2": [50.0]},
    ),
    "unlimited_ports_split_the_remainder_equally": (
        {"a": [10.0], "b": [20.0], "u1": [np.inf], "u2": [np.inf]},
        {"a": [50.0], "b": [15.0], "u1": [5.0], "u2": [3.0]},
        None,
        # neither u1 nor u2 registers a deficit, so a's 40 surplus first fills
        # b's 5 deficit and the remaining 35 is split equally between them:
        # 35/2=17.5 each
        {"a": [10.0], "b": [20.0], "u1": [22.5], "u2": [20.5]},
    ),
    "zero_import_ports_get_nothing_limited_or_not": (
        {
            "a": [10.0],
            "recipient": [20.0],
            "empty_limited": [6.0],
            "empty_unlimited": [np.inf],
        },
        {
            "a": [100.0],
            "recipient": [15.0],
            "empty_limited": [0.0],
            "empty_unlimited": [0.0],
        },
        None,
        # empty_limited and empty_unlimited were never sent any fuel, so
        # neither registers a deficit nor counts as an eligible unlimited
        # recipient, despite one having a finite limit well above its (zero)
        # import; recipient's real deficit (5) is fully covered by a's 90
        # surplus, filling it exactly to its limit, and the remaining 85 is
        # dropped since no eligible port is left to take it
        {
            "a": [10.0],
            "recipient": [20.0],
            "empty_limited": [0.0],
            "empty_unlimited": [0.0],
        },
    ),
}


@pytest.mark.parametrize(
    ("limits", "imports", "allowed", "expected"),
    list(CASES.values()),
    ids=list(CASES.keys()),
)
def test_redistribution(limits, imports, allowed, expected):
    result = _redistribute(limits, imports, allowed)

    for port_name, values in expected.items():
        assert result[port_name] == pytest.approx(values)


# ---------------------------------------------------------------------------
# _calculate_import_from_producers: price, WTT and supply
# ---------------------------------------------------------------------------


def test_price_and_wtt_are_the_supply_weighted_average():
    # price and WTT are the supply-weighted average across all exporting
    # plants, and the supply reaches the profile
    port = _Port()
    producers = {
        "producer_a": _make_producer({"port_a": 1.0}, [600.0], 100.0, wtt=0.02),
        "producer_b": _make_producer({"port_a": 1.0}, [400.0], 200.0, wtt=0.04),
    }

    _calculate_import_from_producers(
        {"port_a": port}, producers, EMISSIONS, {FUEL_NAME: FUEL}, TIMELINE, 0
    )

    # (600 * 100 + 400 * 200) / 1000 = 140.0
    assert port.expectation.price[0] == 140.0
    # (600 * 0.02 + 400 * 0.04) / 1000 = 0.028
    assert np.isclose(port.expectation.wtt[EMISSION_NAME][0], 0.028)
    assert port.expectation.supply[0] == 1000.0
    assert port.profile.get_bunker_supply_mass()[FUEL_NAME][0] == 1000.0


def test_zero_import_ports_are_excluded_even_with_a_survivable_price():
    # a port the export distribution sends nothing to has its price written
    # from a 0/0 weighted average (zero) plus its handling cost, before
    # alignment runs; the supply is later zeroed wherever that price is not
    # above TOLERANCE, so only a nonzero handling cost lets a wrongly
    # redistributed share survive. Here rich is over its limit (surplus 90)
    # and recipient under it (deficit 5); the two empty ports carry a
    # handling cost and must nonetheless end at zero
    rich = _Port(limit=[10.0])
    recipient = _Port(limit=[20.0])
    empty_limited = _Port(limit=[6.0], handling_cost=[50.0])
    empty_unlimited = _Port(limit=[np.inf], handling_cost=[50.0])

    ports = {
        "rich": rich,
        "recipient": recipient,
        "empty_limited": empty_limited,
        "empty_unlimited": empty_unlimited,
    }
    export_distribution = {
        "rich": 100.0,
        "recipient": 15.0,
        "empty_limited": 0.0,
        "empty_unlimited": 0.0,
    }
    producer = _make_producer(export_distribution, [1.0], delivered_cost=100.0)

    _calculate_import_from_producers(
        ports, {"producer": producer}, EMISSIONS, {FUEL_NAME: FUEL}, TIMELINE, 0
    )

    assert rich.expectation.supply == pytest.approx([10.0])
    assert recipient.expectation.supply == pytest.approx([20.0])
    assert empty_limited.expectation.supply == pytest.approx([0.0])
    assert empty_unlimited.expectation.supply == pytest.approx([0.0])


# ---------------------------------------------------------------------------
# both import paths: the price overwrite is stored state
# ---------------------------------------------------------------------------


def _import_from_liquid_market(ports, timeline):
    _calculate_import_from_liquid_market(ports, {FUEL_NAME: FUEL}, EMISSIONS, idx=0)


def _import_from_producers(ports, timeline):
    producer = _make_producer({"port_a": 1.0}, [1.0, 1.0], delivered_cost=100.0)
    _calculate_import_from_producers(
        ports, {"producer": producer}, EMISSIONS, {FUEL_NAME: FUEL}, timeline, 0
    )


@pytest.mark.parametrize(
    "import_fuel",
    [
        pytest.param(_import_from_liquid_market, id="liquid_market"),
        pytest.param(_import_from_producers, id="producers"),
    ],
)
def test_import_does_not_mutate_the_stored_price_overwrite(import_fuel):
    # get_bunker_price_overwrite hands back a slice of the port's stored
    # overwrite array; adding the handling cost onto it must not leave that
    # slice changed
    port = _Port(
        limit=[np.inf, np.inf], handling_cost=[5.0, 5.0], overwrite=[40.0, 40.0]
    )

    import_fuel({"port_a": port}, np.array([0.0, 1.0]))

    assert port.expectation.overwrite == pytest.approx([40.0, 40.0])
    assert port.expectation.price == pytest.approx([45.0, 45.0])
