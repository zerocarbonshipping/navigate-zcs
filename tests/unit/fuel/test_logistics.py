# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.fuel.logistics — plant fuel-delivery expectations."""
import numpy as np
import pytest

from navigate.core import Scalar
from navigate.core.node_reference import NodeReference
from navigate.core.node_type import TRANSPORT
from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.plant import Plant
from navigate.core.nodes.region import Region
from navigate.core.unit import YEAR_TO_DAYS
from navigate.fuel.logistics import calculate_plant_logistics_expectations

TIMELINE = np.arange(3.) * YEAR_TO_DAYS
EMISSIONS = {'carbon_dioxide': None}

LEAD_TIME = 2.
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


class _StepRate:
    """Per-distance rate that jumps from `early` to `late` at `step_day`."""

    def __init__(self, early, late, step_day):
        self._early = early
        self._late = late
        self._step_day = step_day

    def get(self, time):
        return np.where(np.asarray(time, dtype=float) >= self._step_day, self._late, self._early)


def _make_plant(ports, cost_rate=None, lead_time=LEAD_TIME, lifetime=LIFETIME,
                discount_rate=DISCOUNT_RATE) -> Plant:
    plant = Plant('plant')
    plant.fuel = Fuel('oil')
    plant.region = Region('region')
    plant.set_cost_of_capital(discount_rate)

    plant.region.transport_cost['truck'] = Scalar(COST_RATE) if cost_rate is None else cost_rate
    plant.region.transport_wtt[('truck', 'carbon_dioxide')] = Scalar(WTT_RATE)

    plant.initialize_dependencies({}, ports, {})
    plant.initialize_expectation(len(TIMELINE), EMISSIONS, {}, ports, {})
    plant.expectation.set_lead_time(0, lead_time)
    plant.expectation.set_lifetime(0, lifetime)

    return plant


class TestCalculatePlantLogisticsExpectations:

    @pytest.mark.parametrize("bunkering_allowed, set_transport", [
        pytest.param(False, True, id="disallowed_port"),
        pytest.param(True, False, id="no_transport"),
    ])
    def test_skips_when_ineligible(self, bunkering_allowed, set_transport):
        ports = {'port_a': _StubPort(bunkering_allowed=bunkering_allowed)}
        plant = _make_plant(ports)
        if set_transport:
            plant.set_fuel_transport('port_a', NodeReference(TRANSPORT, 'truck'))
            plant.set_fuel_distance('port_a', DISTANCE)

        calculate_plant_logistics_expectations({'plant': plant}, ports, EMISSIONS, TIMELINE, 0)

        assert np.all(plant.expectation.get_levelized_delivery_cost('port_a') == 0.)
        assert np.all(plant.expectation.get_delivery_wtt('port_a', 'carbon_dioxide') == 0.)

    def test_constant_rate_levelizes_to_itself(self):
        # a constant per-ton delivery cost must levelize to exactly itself at
        # every step, independent of lead time, lifetime, and discounting
        ports = {'port_a': _StubPort(bunkering_allowed=True)}
        plant = _make_plant(ports)
        plant.set_fuel_transport('port_a', NodeReference(TRANSPORT, 'truck'))
        plant.set_fuel_distance('port_a', DISTANCE)

        calculate_plant_logistics_expectations({'plant': plant}, ports, EMISSIONS, TIMELINE, 0)

        assert np.allclose(plant.expectation.get_levelized_delivery_cost('port_a'), COST_RATE * DISTANCE)

        assert np.allclose(plant.expectation.get_delivery_wtt('port_a', 'carbon_dioxide'), WTT_RATE * DISTANCE)

    def test_time_varying_rate_averages_over_operating_window(self):
        # with zero discounting and integer lead time and lifetime, the
        # levelized delivery cost is the arithmetic mean of the per-ton cost
        # over the operating years [t + lead, t + lead + lifetime); the rate
        # here steps from 1 to 3 USD/ton/nm at year 3.5, so the operating
        # windows anchored at steps 0, 1, and 2 (lead 2, lifetime 3) average
        # (1, 1, 3), (1, 3, 3), and (3, 3, 3) respectively
        ports = {'port_a': _StubPort(bunkering_allowed=True)}
        rate = _StepRate(early=1., late=3., step_day=3.5 * YEAR_TO_DAYS)
        plant = _make_plant(ports, cost_rate=rate, lead_time=2., lifetime=3., discount_rate=0.)
        plant.set_fuel_transport('port_a', NodeReference(TRANSPORT, 'truck'))
        plant.set_fuel_distance('port_a', DISTANCE)

        calculate_plant_logistics_expectations({'plant': plant}, ports, EMISSIONS, TIMELINE, 0)

        expected = np.array([5. / 3., 7. / 3., 3.]) * DISTANCE
        assert np.allclose(plant.expectation.get_levelized_delivery_cost('port_a'), expected)

    def test_lead_time_is_read_per_step(self):
        # the window must follow the lead time in effect at each forward
        # step: with the same stepped rate and zero discounting as above, a
        # lead time of 2 at step 0 and 3 from step 1 on puts the operating
        # windows at years (2, 3, 4), (4, 5, 6), and (5, 6, 7), averaging
        # (1, 1, 3), (3, 3, 3), and (3, 3, 3) respectively
        ports = {'port_a': _StubPort(bunkering_allowed=True)}
        rate = _StepRate(early=1., late=3., step_day=3.5 * YEAR_TO_DAYS)
        plant = _make_plant(ports, cost_rate=rate, lead_time=2., lifetime=3., discount_rate=0.)
        plant.expectation.set_lead_time(1, 3.)
        plant.set_fuel_transport('port_a', NodeReference(TRANSPORT, 'truck'))
        plant.set_fuel_distance('port_a', DISTANCE)

        calculate_plant_logistics_expectations({'plant': plant}, ports, EMISSIONS, TIMELINE, 0)

        expected = np.array([5. / 3., 3., 3.]) * DISTANCE
        assert np.allclose(plant.expectation.get_levelized_delivery_cost('port_a'), expected)

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
