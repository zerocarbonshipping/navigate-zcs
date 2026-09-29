# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.fuel.port_supply — producer import to ports."""

from __future__ import annotations

import numpy as np

from navigate.fuel.port_supply import _calculate_import_from_producers

TIMELINE = np.array([0.0])
IDX = 0
EMISSIONS = {"co2": None}


class _StubFuel:
    def __init__(self, name):
        self.name = name


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


class _StubPortProfile:
    def __init__(self):
        self.bunker_price = {}
        self.bunker_wtt = {}
        self.bunker_supply_mass = {}

    def set_bunker_price(self, idx, fuel_name, price):
        self.bunker_price[fuel_name] = price

    def set_bunker_wtt(self, idx, fuel_name, emission_name, wtt):
        self.bunker_wtt[(fuel_name, emission_name)] = wtt

    def set_bunker_supply_mass(self, idx, fuel_name, supply):
        self.bunker_supply_mass[fuel_name] = supply


class _StubPort:
    def __init__(self, fuel_name, handling_cost=0.0, bunkering_limit=np.inf):
        self.bunkering_allowed = {fuel_name: True}
        self.bunker_price_overwrite = {fuel_name: None}
        self.bunker_wtt_overwrite = {(fuel_name, e): None for e in EMISSIONS}
        self.expectation = _StubPortExpectation(
            handling_cost={fuel_name: np.full_like(TIMELINE, handling_cost)},
            bunkering_limit={fuel_name: np.full_like(TIMELINE, bunkering_limit)},
        )
        self.profile = _StubPortProfile()

    def is_bunkering_allowed(self, fuel_name):
        return self.bunkering_allowed[fuel_name]


class TestCalculateImportFromProducers:
    def test_infinite_production_at_an_unlimited_port_never_reaches_the_profile(self):
        # an unconstrained producer (MaximumDevelopment = INF) reports infinite
        # expected production; the port has no bunkering limit set, so its
        # limit is the default np.inf too. The bunker price is well-defined
        # (the single exporting plant's own cost plus handling), so the
        # supply is not zeroed by the price check, and reaches the port at
        # np.inf — which the profile must never record.
        fuel_name = "fuel_x"
        port = _StubPort(fuel_name, handling_cost=5.0, bunkering_limit=np.inf)
        plant = _StubPlant(
            "plant_x",
            fuel_name,
            cost={"port_a": np.array([200.0])},
            wtt={("port_a", "co2"): np.array([0.05])},
        )
        producer = _StubProducer(
            plants=[plant],
            export_distribution={"port_a": np.array([1.0])},
            production={"plant_x": np.array([np.inf])},
        )

        _calculate_import_from_producers(
            ports={"port_a": port},
            producers={"producer_a": producer},
            emissions=EMISSIONS,
            fuels={fuel_name: _StubFuel(fuel_name)},
            timeline=TIMELINE,
            idx=IDX,
        )

        # the expectation is internal state and may legitimately carry the
        # unconstrained supply forward as infinite
        assert np.isinf(port.expectation.bunker_supply[fuel_name][0])

        # price and WTT are well-defined: the single infinite-supply plant's
        # own cost/WTT, unaffected by the inf/inf that a plain supply-weighted
        # average would have produced
        assert port.expectation.bunker_price[fuel_name][0] == 205.0
        assert port.expectation.bunker_wtt[(fuel_name, "co2")][0] == 0.05
        assert port.profile.bunker_price[fuel_name] == 205.0
        assert port.profile.bunker_wtt[(fuel_name, "co2")] == 0.05

        # the profile never records the infinite supply
        assert fuel_name not in port.profile.bunker_supply_mass

    def test_infinite_plant_dominates_and_ignores_finite_plants(self):
        # two plants export the same fuel to the same port: one finite, one
        # from an unconstrained producer. The infinite plant's supply makes
        # the port's total import infinite, so price and WTT are the
        # equally-weighted average of the infinite-supply plants only,
        # discarding the finite plant's contribution entirely (mirroring
        # _average_wtt_over_ports's treatment of infinite-supply ports)
        fuel_name = "fuel_x"
        port = _StubPort(fuel_name, handling_cost=0.0, bunkering_limit=np.inf)

        finite_plant = _StubPlant(
            "plant_finite",
            fuel_name,
            cost={"port_a": np.array([100.0])},
            wtt={("port_a", "co2"): np.array([0.01])},
        )
        infinite_plant = _StubPlant(
            "plant_infinite",
            fuel_name,
            cost={"port_a": np.array([300.0])},
            wtt={("port_a", "co2"): np.array([0.09])},
        )

        finite_producer = _StubProducer(
            plants=[finite_plant],
            export_distribution={"port_a": np.array([1.0])},
            production={"plant_finite": np.array([1000.0])},
        )
        infinite_producer = _StubProducer(
            plants=[infinite_plant],
            export_distribution={"port_a": np.array([1.0])},
            production={"plant_infinite": np.array([np.inf])},
        )

        _calculate_import_from_producers(
            ports={"port_a": port},
            producers={
                "producer_finite": finite_producer,
                "producer_infinite": infinite_producer,
            },
            emissions=EMISSIONS,
            fuels={fuel_name: _StubFuel(fuel_name)},
            timeline=TIMELINE,
            idx=IDX,
        )

        assert np.isinf(port.expectation.bunker_supply[fuel_name][0])
        assert port.expectation.bunker_price[fuel_name][0] == 300.0
        assert port.expectation.bunker_wtt[(fuel_name, "co2")][0] == 0.09
        assert fuel_name not in port.profile.bunker_supply_mass

    def test_all_finite_plants_keep_the_supply_weighted_average(self):
        # with no infinite-supply plant, price and WTT are the classic
        # supply-weighted average across all exporting plants, and the
        # finite supply reaches the profile unguarded
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
            emissions=EMISSIONS,
            fuels={fuel_name: _StubFuel(fuel_name)},
            timeline=TIMELINE,
            idx=IDX,
        )

        # (600 * 100 + 400 * 200) / 1000 = 140.0
        assert port.expectation.bunker_price[fuel_name][0] == 140.0
        # (600 * 0.02 + 400 * 0.04) / 1000 = 0.028
        assert np.isclose(port.expectation.bunker_wtt[(fuel_name, "co2")][0], 0.028)
        assert port.expectation.bunker_supply[fuel_name][0] == 1000.0
        assert port.profile.bunker_supply_mass[fuel_name] == 1000.0
