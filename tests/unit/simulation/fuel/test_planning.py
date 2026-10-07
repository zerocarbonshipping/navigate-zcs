# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for navigate.simulation.fuel.planning.

Pipeline planning and stored expectation.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from navigate.core import Scalar
from navigate.simulation.fuel.planning import (
    _calculate_uptake_inter_metric,
    perform_pipeline_planning,
)
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


class _PlanningPlantExpectation:
    def __init__(self, demand_newbuilds):
        self._demand_newbuilds = demand_newbuilds
        self.inter_fuel_metric = None
        self.intra_fuel_metric = None

    def get_production(self, idx):
        return PRODUCTION

    def get_demand_newbuilds(self):
        return self._demand_newbuilds

    def set_demand_newbuilds(self, value):
        self._demand_newbuilds = value

    def set_inter_fuel_metric(self, value):
        self.inter_fuel_metric = value

    def set_intra_fuel_metric(self, value):
        self.intra_fuel_metric = value

    def get_levelized_delivered_cost(self, port_name, idx):
        return 50.0

    def is_in_demand(self):
        # keeps calculate_modelled_uptake on its empty-uptake path, so the
        # test does not also have to stand in for the discrete-choice model
        return False


class _PlanningPlant:
    def __init__(self, name, fuel_name):
        self.name = name
        self.fuel = SimpleNamespace(name=fuel_name, lower_heating_value=Scalar(1.0))
        self.expectation = _PlanningPlantExpectation(demand_newbuilds=1.0e6)
        self.cost_of_capital = Scalar(0.1)
        self.lifetime = Scalar(5.0)
        self.lead_time = Scalar(0.0)


class _PlanningProducerExpectation:
    def __init__(self, fair_share_demand):
        self._fair_share_demand = fair_share_demand  # dict[str, FloatArray]

    def get_fair_share_demand(self):
        return self._fair_share_demand

    def get_export_distribution(self, idx):
        return {"port_a": 1.0}


class _PlanningProfile:
    def __init__(self):
        self.development = None

    def set_development(self, idx, total_increments):
        self.development = total_increments


class _PlanningProducer:
    def __init__(self, assets, fair_share_demand):
        self.assets = assets
        self.allow_plant = {plant.name: True for plant in assets}
        self.expectation = _PlanningProducerExpectation(fair_share_demand)
        self.minimum_offtake_duration = Scalar(5.0)
        self.maximum_development = Scalar(10.0)
        self.maximum_ramp_up = Scalar(0.0)
        # inertia of 1.0 carries the full previous uptake forward undecayed,
        # so the development limit it consumes matches this step's own limit
        # exactly and the modelled-uptake path is never entered
        self.inertia = Scalar(1.0)
        self.current_utilization = 1.0
        self.current_uptake = np.array([0.5, 0.5])
        self.feed_constraints = {}
        self.pipeline = [[] for _ in assets]
        self.profile = _PlanningProfile()


def _make_producer():
    assets = [_PlanningPlant("plant_a", FUEL_A), _PlanningPlant("plant_b", FUEL_B)]
    fair_share_demand = {
        FUEL_A: np.full_like(TIMELINE, INITIAL_DEMAND),
        FUEL_B: np.full_like(TIMELINE, INITIAL_DEMAND),
    }

    return _PlanningProducer(assets, fair_share_demand), fair_share_demand


class TestPerformPipelinePlanning:
    def test_stored_fair_share_demand_is_unchanged(self):
        # the inertia development entirely consumes the step's development
        # limit, so every plant gets a nonzero inertia increment and the
        # production subtracted from demand is nonzero for both fuels
        producer, fair_share_demand = _make_producer()
        stored_before = {
            fuel_name: values.copy() for fuel_name, values in fair_share_demand.items()
        }

        # fair-share demand is uniform across the timeline, so interpolating
        # it onto a plant's evaluation horizon returns that same uniform
        # value; the per-plant metric then divides by the plant's own
        # production, so subtracting the inertia-covered production from
        # demand first should show up here as a lower demand_newbuilds - an
        # implementation that dropped the subtraction, leaving demand and
        # its stored array both untouched, would still pass the assertions
        # above but fail this one
        expected_demand_newbuilds = INITIAL_DEMAND / PRODUCTION - INERTIA_INCREMENT

        perform_pipeline_planning(producer, TIMELINE, TIME_STEP, IDX)

        for fuel_name, before in stored_before.items():
            assert fair_share_demand[fuel_name] == pytest.approx(before)

        for plant in producer.assets:
            assert plant.expectation._demand_newbuilds == pytest.approx(
                expected_demand_newbuilds
            )


class TestMinimumOfftakeDuration:
    # demand falls by one plant's production a year from ten plants' worth, so
    # the plant-equivalent multiplier is 10, 9, 8, ... at the yearly points of
    # the evaluation horizon (lead time 0, lifetime 5 years)
    @pytest.mark.parametrize(
        ("duration", "expected"),
        [
            pytest.param(0.5, 10.0, id="under-a-year-reads-one-year"),
            pytest.param(1.0, 10.0, id="one-year"),
            pytest.param(1.5, 9.0, id="rounded-up-to-two-years"),
            pytest.param(3.0, 8.0, id="three-years"),
        ],
    )
    def test_demand_newbuilds_is_lowest_multiplier_within_duration(
        self, duration, expected
    ):
        plant = _PlanningPlant("plant_a", FUEL_A)
        demand = {FUEL_A: 10.0 * PRODUCTION - PRODUCTION * TIMELINE / YEAR}

        _calculate_uptake_inter_metric(plant, demand, Scalar(duration), TIMELINE, IDX)

        assert plant.expectation.get_demand_newbuilds() == pytest.approx(expected)
