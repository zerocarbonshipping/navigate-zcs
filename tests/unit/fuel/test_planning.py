# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.fuel.planning: pipeline planning and stored expectation."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from navigate.core import Scalar
from navigate.fuel.planning import perform_pipeline_planning
from navigate.util import YEAR

# a daily-stepped horizon long enough to cover every plant's evaluation
# timeline (lead time 0, lifetime 5 years) starting at idx 0
TIMELINE = np.arange(0.0, 3660.0, 30.0)
TIME_STEP = 30.0
IDX = 0

FUEL_A = "fuel_a"
FUEL_B = "fuel_b"

PRODUCTION = 100.0  # tons/year, both plants
INITIAL_DEMAND = 1000.0  # tons/year, both fuels

# both plants split the producer's uptake 50/50 (current_uptake below), and
# inertia of 1.0 carries that split forward undecayed and unconstrained, so
# each plant's inertia increment is half of the step's whole development
# limit: current_utilization (1.0) * maximum_development.get() (10.0) *
# time_step / YEAR
INERTIA_INCREMENT = 0.5 * (1.0 * 10.0 * TIME_STEP / YEAR)


class _PlantExpectation:
    def __init__(self):
        self.demand_newbuilds = 1.0e6

    def get_production(self, idx):
        return PRODUCTION

    def get_demand_newbuilds(self):
        return self.demand_newbuilds

    def set_demand_newbuilds(self, value):
        self.demand_newbuilds = value

    def set_inter_fuel_metric(self, value):
        pass

    def set_intra_fuel_metric(self, value):
        pass

    def get_levelized_delivered_cost(self, port_name, idx):
        return 50.0


def _make_plant(name, fuel_name):
    return SimpleNamespace(
        name=name,
        fuel=SimpleNamespace(name=fuel_name, lower_heating_value=Scalar(1.0)),
        expectation=_PlantExpectation(),
        cost_of_capital=Scalar(0.1),
        lifetime=Scalar(5.0),
        lead_time=Scalar(0.0),
    )


def _make_producer(fair_share_demand):
    assets = [_make_plant("plant_a", FUEL_A), _make_plant("plant_b", FUEL_B)]
    expectation = SimpleNamespace(
        get_fair_share_demand=lambda: fair_share_demand,
        get_export_distribution=lambda idx: {"port_a": 1.0},
    )

    # inertia of 1.0 carries the full previous uptake forward undecayed, so
    # the development it consumes matches this step's own limit exactly and
    # the modelled-uptake path is never entered
    return SimpleNamespace(
        assets=assets,
        allow_plant={plant.name: True for plant in assets},
        expectation=expectation,
        minimum_offtake_duration=Scalar(5.0),
        maximum_development=Scalar(10.0),
        maximum_ramp_up=Scalar(0.0),
        inertia=Scalar(1.0),
        current_utilization=1.0,
        current_uptake=np.array([0.5, 0.5]),
        feed_constraints={},
        pipeline=[[] for _ in assets],
        profile=SimpleNamespace(set_development=lambda idx, value: None),
    )


class TestPerformPipelinePlanning:
    def test_stored_fair_share_demand_is_unchanged(self):
        # the inertia development consumes the step's whole development
        # limit, so every plant gets a nonzero inertia increment and the
        # production subtracted from demand is nonzero for both fuels
        fair_share_demand = {
            FUEL_A: np.full_like(TIMELINE, INITIAL_DEMAND),
            FUEL_B: np.full_like(TIMELINE, INITIAL_DEMAND),
        }
        producer = _make_producer(fair_share_demand)

        # fair-share demand is uniform across the timeline, so the per-plant
        # metric is that value over the plant's own production; subtracting
        # the inertia-covered production first must lower demand_newbuilds,
        # so an implementation that dropped the subtraction would still keep
        # the stored arrays untouched but fail this
        expected_demand_newbuilds = INITIAL_DEMAND / PRODUCTION - INERTIA_INCREMENT

        perform_pipeline_planning(producer, TIMELINE, TIME_STEP, IDX)

        for values in fair_share_demand.values():
            assert values == pytest.approx(np.full_like(TIMELINE, INITIAL_DEMAND))

        for plant in producer.assets:
            assert plant.expectation.demand_newbuilds == pytest.approx(
                expected_demand_newbuilds
            )
