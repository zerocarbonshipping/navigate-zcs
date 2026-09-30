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
    _calculate_import_from_producers,
)

TIMELINE = np.array([0.0])
IDX = 0

FUEL_NAME = "fuel_a"
FUEL = SimpleNamespace(name=FUEL_NAME)
EMISSION_NAME = "carbon_dioxide"
EMISSIONS = {EMISSION_NAME: None}


class _StubEmission:
    def __init__(self):
        self.global_warming_potential = Scalar(1.0)


# the producer-import tests below use their own fuel/emission names, kept apart
# from FUEL_NAME/EMISSIONS above so neither group's fixtures leak into the other
PRODUCER_EMISSIONS = {"co2": _StubEmission()}


# ---------------------------------------------------------------------------
# _align_export_with_bunkering_limits: surplus/deficit redistribution
# ---------------------------------------------------------------------------


class _LimitPortExpectation:
    def __init__(self, limit):
        self._limit = np.asarray(limit, dtype=float)

    def get_bunkering_limit(self, fuel_name, idx):
        return self._limit


class _LimitPort:
    def __init__(self, limit, allowed=True):
        self.expectation = _LimitPortExpectation(limit)
        self._allowed = allowed

    def is_bunkering_allowed(self, fuel_name):
        return self._allowed


def _redistribute(limits, imports, allowed=None):
    """Run the function under test and return each port's resulting import."""
    allowed = allowed or {}

    ports = {name: _LimitPort(limits[name], allowed.get(name, True)) for name in limits}
    supplies = {
        name: {FUEL_NAME: np.asarray(imports[name], dtype=float)} for name in limits
    }

    _align_export_with_bunkering_limits(supplies, FUEL, ports, np.s_[:])

    return {name: supplies[name][FUEL_NAME] for name in limits}


# each row: limits, imports, allowed overrides, expected result
CASES = {
    "over_and_under_limit_deficit_covers_surplus": (
        {"a": [10.0], "b": [100.0]},
        {"a": [30.0], "b": [30.0]},
        None,
        # a is trimmed to its limit (10); its 20 surplus fully covers b's 70
        # deficit only in part - here the deficit (70) exceeds the surplus (20),
        # so all of it moves to b: b ends at 30 + 20 = 50
        {"a": [10.0], "b": [50.0]},
    ),
    "deficit_smaller_than_surplus_excess_dropped": (
        {"a": [10.0], "b": [20.0]},
        {"a": [50.0], "b": [15.0]},
        None,
        # a's surplus (40) exceeds b's deficit (5): b is filled exactly to its
        # limit (20) and the remaining 35 has nowhere to go
        {"a": [10.0], "b": [20.0]},
    ),
    "unlimited_port_absorbs_remaining_surplus": (
        {"a": [10.0], "b": [np.inf]},
        {"a": [30.0], "b": [5.0]},
        None,
        # b has no limit, so it never registers a deficit in stage one; a's
        # full 20 surplus is left over and is handed to b in stage two
        {"a": [10.0], "b": [25.0]},
    ),
    "disallowed_port_gets_nothing": (
        {"a": [10.0], "b": [100.0]},
        {"a": [30.0], "b": [5.0]},
        {"b": False},
        # b is excluded from the mechanism entirely: it neither contributes
        # nor receives, so a's 20 surplus has nowhere to go and is dropped
        {"a": [10.0], "b": [5.0]},
    ),
    "time_elements_are_redistributed_independently": (
        {"a": [10.0, 10.0], "b": [100.0, 100.0]},
        {"a": [30.0, 5.0], "b": [30.0, 150.0]},
        None,
        # index 0 repeats the first case (a over, b under); index 1 reverses
        # the roles (a under by 5, b over by 50): a is filled fully to its
        # limit (10) and b is trimmed to its limit (100), dropping the rest of
        # its surplus
        {"a": [10.0, 10.0], "b": [50.0, 100.0]},
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
    "two_unlimited_ports_split_the_remainder_equally": (
        {"a": [10.0], "u1": [np.inf], "u2": [np.inf]},
        {"a": [50.0], "u1": [5.0], "u2": [3.0]},
        None,
        # neither u1 nor u2 registers a deficit, so all of a's 40 surplus is
        # left over and split equally between them: 40/2=20 each
        {"a": [10.0], "u1": [25.0], "u2": [23.0]},
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
# _calculate_import_from_producers: price/WTT and the profile write
# ---------------------------------------------------------------------------


class _StubFuel:
    def __init__(self, name):
        self.name = name
        # PortProfile.initialize reads this to pick the bunker-supply-mass
        # default; every fuel here is a producer fuel, never liquid market
        self.liquid_market = False
        # PortProfile.initialize reads this to convert mass to energy; a
        # value of 1.0 keeps mass and energy numerically identical
        self.lower_heating_value = Scalar(1.0)


class _StubPlantExpectation:
    def __init__(self, cost, wtt):
        self._cost = cost  # dict[port_name, np.ndarray]
        self._wtt = wtt  # dict[(port_name, emission_name), np.ndarray]

    def get_expected_delivered_cost(self, port_name, idx):
        return self._cost[port_name][idx]

    def get_expected_delivered_wtt(self, port_name, emission_name, idx):
        return self._wtt[(port_name, emission_name)][idx]


class _StubPlant:
    def __init__(self, name, fuel_name, cost, wtt):
        self.name = name
        self.fuel = _StubFuel(fuel_name)
        self.expectation = _StubPlantExpectation(cost, wtt)


class _StubProducerExpectation:
    def __init__(self, export_distribution, production):
        self._export_distribution = export_distribution  # dict[port_name, array]
        self._production = production  # dict[plant_name, array]

    def get_export_distribution(self, idx):
        return {p: value[idx] for p, value in self._export_distribution.items()}

    def get_expected_production(self, plant_name, idx):
        return self._production[plant_name][idx]


class _StubProducer:
    def __init__(self, plants, export_distribution, production):
        self.plants = plants
        self.expectation = _StubProducerExpectation(export_distribution, production)


class _StubPortExpectation:
    def __init__(self, handling_cost, bunkering_limit):
        self._handling_cost = handling_cost  # dict[fuel_name, array]
        self._bunkering_limit = bunkering_limit  # dict[fuel_name, array]
        self.bunker_price = {}
        self.bunker_wtt = {}
        self.bunker_supply = {}

    def get_handling_cost(self, fuel_name, idx):
        return self._handling_cost[fuel_name][idx]

    def get_bunkering_limit(self, fuel_name, idx):
        return self._bunkering_limit[fuel_name][idx]

    def get_bunker_price_overwrite(self, fuel_name, idx):
        raise AssertionError("no port in these tests overwrites its bunker price")

    def get_bunker_wtt_overwrite(self, fuel_name, emission_name, idx):
        raise AssertionError("no port in these tests overwrites its bunker WTT")

    def set_bunker_price(self, idx, fuel_name, price):
        self.bunker_price[fuel_name] = price

    def set_bunker_wtt(self, idx, fuel_name, emission_name, wtt):
        self.bunker_wtt[(fuel_name, emission_name)] = wtt

    def set_bunker_supply(self, idx, fuel_name, supply):
        self.bunker_supply[fuel_name] = supply

    def get_bunker_price(self, fuel_name, idx):
        return self.bunker_price[fuel_name][idx]


class _StubPort:
    def __init__(self, fuel_name, handling_cost=0.0, bunkering_limit=np.inf):
        self.bunkering_allowed = {fuel_name: True}
        self.bunker_price_overwrite = {fuel_name: None}
        self.bunker_wtt_overwrite = {(fuel_name, e): None for e in PRODUCER_EMISSIONS}
        self.expectation = _StubPortExpectation(
            handling_cost={fuel_name: np.full_like(TIMELINE, handling_cost)},
            bunkering_limit={fuel_name: np.full_like(TIMELINE, bunkering_limit)},
        )

        # a real PortProfile, not a stub, so the supply is read back exactly
        # as production code writes it
        self.profile = PortProfile()
        self.profile.initialize(
            timeline=TIMELINE,
            emissions=PRODUCER_EMISSIONS,
            fuels={fuel_name: _StubFuel(fuel_name)},
            emissions_lifetime=100.0,
        )

    def is_bunkering_allowed(self, fuel_name):
        return self.bunkering_allowed[fuel_name]


class TestCalculateImportFromProducers:
    def test_price_and_wtt_are_the_supply_weighted_average(self):
        # price and WTT are the supply-weighted average across all exporting
        # plants, and the supply reaches the profile
        fuel_name = "fuel_x"
        port = _StubPort(fuel_name, handling_cost=0.0, bunkering_limit=np.inf)

        plant_a = _StubPlant(
            "plant_a",
            fuel_name,
            cost={"port_a": np.array([100.0])},
            wtt={("port_a", "co2"): np.array([0.02])},
        )
        plant_b = _StubPlant(
            "plant_b",
            fuel_name,
            cost={"port_a": np.array([200.0])},
            wtt={("port_a", "co2"): np.array([0.04])},
        )

        producer_a = _StubProducer(
            plants=[plant_a],
            export_distribution={"port_a": np.array([1.0])},
            production={"plant_a": np.array([600.0])},
        )
        producer_b = _StubProducer(
            plants=[plant_b],
            export_distribution={"port_a": np.array([1.0])},
            production={"plant_b": np.array([400.0])},
        )

        _calculate_import_from_producers(
            ports={"port_a": port},
            producers={"producer_a": producer_a, "producer_b": producer_b},
            emissions=PRODUCER_EMISSIONS,
            fuels={fuel_name: _StubFuel(fuel_name)},
            timeline=TIMELINE,
            idx=IDX,
        )

        # (600 * 100 + 400 * 200) / 1000 = 140.0
        assert port.expectation.bunker_price[fuel_name][0] == 140.0
        # (600 * 0.02 + 400 * 0.04) / 1000 = 0.028
        assert np.isclose(port.expectation.bunker_wtt[(fuel_name, "co2")][0], 0.028)
        assert port.expectation.bunker_supply[fuel_name][0] == 1000.0
        assert port.profile.get_bunker_supply_mass()[fuel_name][0] == 1000.0


# ---------------------------------------------------------------------------
# _calculate_import_from_producers: the zero-import exclusion end to end
# ---------------------------------------------------------------------------
#
# A port the export distribution sends nothing to has its price and WTT
# written from a 0/0 weighted average (zero) plus its handling cost, before
# alignment ever runs. _calculate_import_from_producers then zeroes any
# port's post-alignment supply where that price is not above TOLERANCE - so a
# zero-import port with no handling cost of its own would lose a wrongly
# redistributed share to that check regardless, and a nonzero handling cost
# is what lets a wrongly redistributed share survive it. Both must instead
# receive no share of the redistribution in the first place.


class _ImportPortExpectation:
    def __init__(self, limit, handling_cost):
        self._limit = np.asarray(limit, dtype=float)
        self._handling_cost = np.asarray(handling_cost, dtype=float)
        self.price = None
        self.supply = None

    def get_bunkering_limit(self, fuel_name, idx):
        return self._limit

    def get_handling_cost(self, fuel_name, idx):
        return self._handling_cost.copy()

    def set_bunker_price(self, idx, fuel_name, price):
        self.price = price

    def get_bunker_price(self, fuel_name, idx):
        return self.price

    def set_bunker_wtt(self, idx, fuel_name, emission_name, wtt):
        pass

    def set_bunker_supply(self, idx, fuel_name, supply):
        self.supply = supply


class _ImportPortProfile:
    def set_bunker_price(self, idx, fuel_name, price):
        pass

    def set_bunker_wtt(self, idx, fuel_name, emission_name, wtt):
        pass

    def set_bunker_supply_mass(self, idx, fuel_name, mass):
        pass


class _ImportPort:
    def __init__(self, limit, handling_cost=(0.0,)):
        self.bunkering_allowed = {FUEL_NAME: True}
        self.bunker_price_overwrite = {FUEL_NAME: None}
        self.bunker_wtt_overwrite = {(FUEL_NAME, EMISSION_NAME): None}
        self.expectation = _ImportPortExpectation(limit, handling_cost)
        self.profile = _ImportPortProfile()

    def is_bunkering_allowed(self, fuel_name):
        return self.bunkering_allowed[fuel_name]


class _ImportPlantExpectation:
    def __init__(self, delivered_cost, delivered_wtt):
        self._delivered_cost = delivered_cost
        self._delivered_wtt = delivered_wtt

    def get_expected_delivered_cost(self, port_name, idx):
        return self._delivered_cost

    def get_expected_delivered_wtt(self, port_name, emission_name, idx):
        return self._delivered_wtt


class _ImportPlant:
    def __init__(self, name, delivered_cost, delivered_wtt=0.0):
        self.name = name
        self.fuel = FUEL
        self.expectation = _ImportPlantExpectation(delivered_cost, delivered_wtt)


class _ImportProducerExpectation:
    def __init__(self, export_distribution, production):
        self._export_distribution = export_distribution
        self._production = production

    def get_export_distribution(self, idx):
        return self._export_distribution

    def get_expected_production(self, plant_name, idx):
        return self._production


class _ImportProducer:
    def __init__(self, plants, export_distribution, production):
        self.plants = plants
        self.expectation = _ImportProducerExpectation(export_distribution, production)


def test_zero_import_ports_are_excluded_even_with_a_survivable_price():
    # rich exceeds its limit (100 imported, limit 10: surplus 90); recipient
    # is under its limit (15 imported, limit 20: deficit 5) and is the only
    # legitimate recipient, so it is filled exactly to its limit (20);
    # empty_limited and empty_unlimited receive no export at all. Both carry
    # a nonzero handling cost, so their price (handling cost alone, since
    # 0/0 supply-weighted cost defaults to zero) is above TOLERANCE - enough
    # for a wrongly redistributed share to survive the post-alignment check.
    # Both must nonetheless end at zero.
    rich = _ImportPort(limit=[10.0])
    recipient = _ImportPort(limit=[20.0])
    empty_limited = _ImportPort(limit=[6.0], handling_cost=[50.0])
    empty_unlimited = _ImportPort(limit=[np.inf], handling_cost=[50.0])

    ports = {
        "rich": rich,
        "recipient": recipient,
        "empty_limited": empty_limited,
        "empty_unlimited": empty_unlimited,
    }
    plant = _ImportPlant("plant", delivered_cost=100.0)
    producer = _ImportProducer(
        plants=[plant],
        export_distribution={
            "rich": 100.0,
            "recipient": 15.0,
            "empty_limited": 0.0,
            "empty_unlimited": 0.0,
        },
        production=np.array([1.0]),
    )

    _calculate_import_from_producers(
        ports, {"producer": producer}, EMISSIONS, {FUEL_NAME: FUEL}, TIMELINE, 0
    )

    assert rich.expectation.supply == pytest.approx([10.0])
    assert recipient.expectation.supply == pytest.approx([20.0])
    assert empty_limited.expectation.supply == pytest.approx([0.0])
    assert empty_unlimited.expectation.supply == pytest.approx([0.0])
