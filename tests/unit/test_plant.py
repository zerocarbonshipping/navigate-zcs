# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the Plant node."""

from __future__ import annotations

import pytest

from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.plant import Plant
from navigate.core.nodes.process import Process
from navigate.core.nodes.region import Region
from navigate.core.nodes.source import Source
from navigate.core.nodes.transport import Transport

PORTS = {"port_a": None, "port_b": None}
FEEDSTOCKS = {"water": None, "biomass": None}
PROCESSES = {"electrolysis": None}


def _make_plant() -> Plant:
    plant = Plant("plant")
    plant.fuel = Fuel("oil")
    plant.process = Process("process")
    plant.region = Region("region")
    plant.source = Source("source")
    plant.set_capacity(100.0)
    plant.initialize_dependencies(FEEDSTOCKS, PORTS, PROCESSES)
    return plant


class TestFuelTransport:
    def test_distance_without_transport_raises(self):
        plant = _make_plant()
        plant.set_fuel_distance("port_a", 500.0)

        with pytest.raises(ValueError, match="no transport is assigned"):
            plant.initialize()

    def test_transport_without_distance_defaults_to_zero(self):
        plant = _make_plant()
        truck = Transport("truck")
        plant.set_fuel_transport("port_a", truck)
        plant.initialize()

        transport, distance = plant.fuel_deliveries["port_a"]
        assert transport is truck
        assert distance.get() == 0.0
        assert plant.fuel_deliveries["port_b"] is None

    def test_event_reassignment_rebuilds_deliveries(self):
        # an event read reruns reinitialize: the deliveries must follow the
        # distance an event gives port_a, replacing the zero its transport was
        # first delivered over, and the transport newly given to port_b, which
        # carries no distance and so is delivered over zero miles
        plant = _make_plant()
        truck, ship = Transport("truck"), Transport("ship")
        plant.set_fuel_transport("port_a", truck)
        plant.initialize()
        assert plant.fuel_deliveries["port_a"][1].get() == 0.0

        plant.set_fuel_distance("port_a", 800.0)
        plant.set_fuel_transport("port_b", ship)
        plant.reinitialize()

        transport_a, distance_a = plant.fuel_deliveries["port_a"]
        transport_b, distance_b = plant.fuel_deliveries["port_b"]
        assert transport_a is truck
        assert distance_a.get() == 800.0
        assert transport_b is ship
        assert distance_b.get() == 0.0


class TestFeedTransport:
    def test_deliveries_cover_feedstocks_and_processes(self):
        # a feed key is a feedstock or a process name; each is paired on its
        # own: a transport with its distance, a transport alone with zero, and
        # a name without a transport with None
        plant = _make_plant()
        truck, pipeline = Transport("truck"), Transport("pipeline")
        plant.set_feed_transport("water", truck)
        plant.set_feed_distance("water", 100.0)
        plant.set_feed_transport("electrolysis", pipeline)
        plant.initialize()

        water_transport, water_distance = plant.feed_deliveries["water"]
        process_transport, process_distance = plant.feed_deliveries["electrolysis"]
        assert water_transport is truck
        assert water_distance.get() == 100.0
        assert process_transport is pipeline
        assert process_distance.get() == 0.0
        assert plant.feed_deliveries["biomass"] is None


class TestLiquidMarketGuard:
    def test_liquid_market_fuel_raises(self):
        plant = _make_plant()
        plant.fuel.set_liquid_market("TRUE")

        with pytest.raises(ValueError, match="belongs to a liquid market"):
            plant.initialize()


class TestCommandValueValidatedBeforeKeyMatch:
    def test_invalid_value_on_a_missing_key_reports_the_value_error(self):
        # the value is validated before the key is matched, so a command wrong
        # in both ways reports the value error, not the missing key
        plant = _make_plant()

        with pytest.raises(ValueError, match=r"must be ≥ 0\.0"):
            plant.set_fuel_distance("missing", -1.0)
