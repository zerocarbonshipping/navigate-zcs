# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.fuel.logistics — plant fuel-delivery expectations."""
import numpy as np

from navigate.core import Scalar
from navigate.core.node_reference import NodeReference
from navigate.core.node_type import TRANSPORT
from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.plant import Plant
from navigate.core.nodes.region import Region
from navigate.economics.metric import calculate_age_levelized_cost
from navigate.fuel.logistics import calculate_plant_logistics_expectations

TIMELINE = np.array([0., 365.25, 730.5])
EMISSIONS = {'carbon_dioxide': None}

LIFETIME = 30.
DISCOUNT_RATE = 0.1
COST_RATE = 0.1     # USD/ton/nm
WTT_RATE = 0.001    # ton emission/ton fuel/nm
DISTANCE = 500.     # nm


class _StubPort:
    def __init__(self, bunkering_allowed):
        self._bunkering_allowed = bunkering_allowed

    def is_bunkering_allowed(self, fuel_name):
        return self._bunkering_allowed


def _make_plant(ports) -> Plant:
    plant = Plant('plant')
    plant.fuel = Fuel('oil')
    plant.region = Region('region')
    plant.set_cost_of_capital(DISCOUNT_RATE)

    plant.region.transport_cost['truck'] = Scalar(COST_RATE)
    plant.region.transport_wtt[('truck', 'carbon_dioxide')] = Scalar(WTT_RATE)

    plant.initialize_dependencies({}, ports, {})
    plant.initialize_expectation(len(TIMELINE), EMISSIONS, {}, ports, {})
    plant.expectation.set_lifetime(0, LIFETIME)

    return plant


class TestCalculatePlantLogisticsExpectations:

    def test_disallowed_port_is_skipped(self):
        ports = {'port_a': _StubPort(bunkering_allowed=False)}
        plant = _make_plant(ports)
        plant.set_fuel_transport('port_a', NodeReference(TRANSPORT, 'truck'))
        plant.set_fuel_distance('port_a', DISTANCE)

        calculate_plant_logistics_expectations({'plant': plant}, ports, EMISSIONS, TIMELINE, 0)

        assert np.all(plant.expectation.get_levelized_delivery_cost('port_a') == 0.)
        assert np.all(plant.expectation.get_delivery_wtt('port_a', 'carbon_dioxide') == 0.)

    def test_no_transport_leaves_zero_defaults(self):
        ports = {'port_a': _StubPort(bunkering_allowed=True)}
        plant = _make_plant(ports)

        calculate_plant_logistics_expectations({'plant': plant}, ports, EMISSIONS, TIMELINE, 0)

        assert np.all(plant.expectation.get_levelized_delivery_cost('port_a') == 0.)
        assert np.all(plant.expectation.get_delivery_wtt('port_a', 'carbon_dioxide') == 0.)

    def test_transport_sets_levelized_cost_and_wtt(self):
        ports = {'port_a': _StubPort(bunkering_allowed=True)}
        plant = _make_plant(ports)
        plant.set_fuel_transport('port_a', NodeReference(TRANSPORT, 'truck'))
        plant.set_fuel_distance('port_a', DISTANCE)

        calculate_plant_logistics_expectations({'plant': plant}, ports, EMISSIONS, TIMELINE, 0)

        cost = COST_RATE * DISTANCE * np.ones(len(TIMELINE))
        expected = calculate_age_levelized_cost(cost, LIFETIME, DISCOUNT_RATE)
        assert np.allclose(plant.expectation.get_levelized_delivery_cost('port_a'), expected)

        assert np.allclose(plant.expectation.get_delivery_wtt('port_a', 'carbon_dioxide'), WTT_RATE * DISTANCE)

    def test_plants_sharing_a_rate_keep_their_own_distance(self):
        ports = {'port_a': _StubPort(bunkering_allowed=True)}
        near, far = _make_plant(ports), _make_plant(ports)
        for plant, distance in ((near, DISTANCE), (far, 2 * DISTANCE)):
            plant.set_fuel_transport('port_a', NodeReference(TRANSPORT, 'truck'))
            plant.set_fuel_distance('port_a', distance)

        calculate_plant_logistics_expectations({'near': near, 'far': far}, ports, EMISSIONS, TIMELINE, 0)

        near_wtt = near.expectation.get_delivery_wtt('port_a', 'carbon_dioxide')
        far_wtt = far.expectation.get_delivery_wtt('port_a', 'carbon_dioxide')
        assert np.allclose(far_wtt, 2 * near_wtt)
        assert np.allclose(far.expectation.get_levelized_delivery_cost('port_a'),
                           2 * near.expectation.get_levelized_delivery_cost('port_a'))
