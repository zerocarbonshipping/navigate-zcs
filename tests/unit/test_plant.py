# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the Plant node."""
import pytest

from navigate.core.node_reference import NodeReference
from navigate.core.node_type import TRANSPORT
from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.plant import Plant
from navigate.core.nodes.process import Process
from navigate.core.nodes.region import Region
from navigate.core.nodes.source import Source

PORTS = {'port_a': None, 'port_b': None}


def _make_plant() -> Plant:
    plant = Plant('plant')
    plant.fuel = Fuel('oil')
    plant.process = Process('process')
    plant.region = Region('region')
    plant.source = Source('source')
    plant.set_capacity(100.)
    plant.initialize_dependencies({}, PORTS, {})
    return plant


class TestFuelTransport:

    def test_dependencies_seed_per_port(self):
        plant = _make_plant()

        assert plant.fuel_transport == {'port_a': None, 'port_b': None}
        assert plant.fuel_distance == {'port_a': None, 'port_b': None}

    def test_distance_without_transport_raises(self):
        plant = _make_plant()
        plant.set_fuel_distance('port_a', 500.)

        with pytest.raises(ValueError, match="no transport is assigned"):
            plant.initialize()

    def test_transport_without_distance_defaults_to_zero(self):
        plant = _make_plant()
        plant.set_fuel_transport('port_a', NodeReference(TRANSPORT, 'truck'))
        plant.initialize()

        assert plant.fuel_distance['port_a'].get() == 0.

    def test_wildcard_assigns_every_port(self):
        plant = _make_plant()
        plant.set_fuel_transport('*', NodeReference(TRANSPORT, 'truck'))
        plant.set_fuel_distance('*', 500.)
        plant.initialize()

        assert all(transport is not None for transport in plant.fuel_transport.values())
        assert all(distance.get() == 500. for distance in plant.fuel_distance.values())


class TestLiquidMarketGuard:

    def test_liquid_market_fuel_raises(self):
        plant = _make_plant()
        plant.fuel.set_liquid_market('TRUE')

        with pytest.raises(ValueError, match="belongs to a liquid market"):
            plant.initialize()
