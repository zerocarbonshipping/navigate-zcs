# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.fuel.production — feed transport cost and emissions."""

from __future__ import annotations

import numpy as np

from navigate.core import Scalar
from navigate.core.nodes.feedstock import Feedstock
from navigate.core.nodes.plant import Plant
from navigate.core.nodes.region import Region
from navigate.core.nodes.transport import Transport
from navigate.economics.flows import Component
from navigate.fuel.production import (
    _calculate_transport_cost,
    _calculate_transport_emissions,
)

EMISSIONS = {"carbon_dioxide": None}
FEEDSTOCKS = {"water": None, "biomass": None}

COST_RATE = 0.1  # USD/ton/nm
WTT_RATE = 0.001  # ton emission/ton feed/nm
DISTANCE = 100.0  # nm
PRODUCTION = 1000.0  # ton fuel/year
CONVERSION = 2.0  # ton feed/ton fuel

# lead time 1 and lifetime 2 from time 0 span three calendar-year bins, the
# first spent under construction
OPERATING = np.array([0.0, 1.0, 1.0])


def _make_plant() -> Plant:
    plant = Plant("plant")
    plant.initialize_dependencies(FEEDSTOCKS, {}, {})
    plant.set_feed_transport("water", Transport("truck"))
    plant.set_feed_distance("water", DISTANCE)
    plant.apply_command_defaults()
    return plant


def _make_region() -> Region:
    region = Region("region")
    region.transport_cost["truck"] = Scalar(COST_RATE)
    region.transport_wtt[("truck", "carbon_dioxide")] = Scalar(WTT_RATE)
    return region


def _make_component() -> Component:
    return Component(lead_time=1.0, lifetime=2.0, time_initial=0.0, emissions=EMISSIONS)


class TestCalculateTransport:
    def test_transported_feed_adds_cost_and_emissions_per_ton_mile(self):
        # the feed moved per year is conversion * production = 2000 tons over
        # 100 nm: 2000 * 100 * 0.1 = 20000 USD and 2000 * 100 * 0.001 = 200 tons
        # of emission in each operating year, nothing under construction
        plant, region, component = _make_plant(), _make_region(), _make_component()
        feed = Feedstock("water")

        _calculate_transport_cost(
            component, plant, feed, region, PRODUCTION, CONVERSION
        )
        _calculate_transport_emissions(
            component, plant, feed, EMISSIONS, region, PRODUCTION, CONVERSION
        )

        np.testing.assert_allclose(component.opex_flow, 20000.0 * OPERATING)
        np.testing.assert_allclose(
            component.wtt_flow["carbon_dioxide"], 200.0 * OPERATING
        )

    def test_feed_without_transport_adds_nothing(self):
        plant, region, component = _make_plant(), _make_region(), _make_component()
        feed = Feedstock("biomass")

        _calculate_transport_cost(
            component, plant, feed, region, PRODUCTION, CONVERSION
        )
        _calculate_transport_emissions(
            component, plant, feed, EMISSIONS, region, PRODUCTION, CONVERSION
        )

        assert np.all(component.opex_flow == 0.0)
        assert np.all(component.wtt_flow["carbon_dioxide"] == 0.0)
