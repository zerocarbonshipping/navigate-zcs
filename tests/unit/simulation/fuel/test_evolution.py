# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for navigate.simulation.fuel.evolution.

The producer's production forecast.
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from navigate.core import Scalar
from navigate.core.increment import PlantIncrement
from navigate.simulation.fuel.evolution import (
    _calculate_increments_production,
    perform_decommissioning,
    perform_pipeline_delivery,
)
from navigate.util import YEAR

# far enough into the run that every increment below was delivered after the
# start of the timeline, days
TODAY = 25.0 * YEAR
LIFETIME = 20.0  # years

# the expected values are exact fractions; only the round-off of the day
# arithmetic separates them from the computed ones
REL_TOL = 1e-9


def _make_producer(increment: PlantIncrement, *, delivered: bool) -> SimpleNamespace:
    """Carry one plant type holding one increment, in the pipeline or delivered."""
    return SimpleNamespace(
        assets=[SimpleNamespace(lifetime=Scalar(LIFETIME))],
        pipeline=[[] if delivered else [increment]],
        increments=[[increment] if delivered else []],
    )


def _forecast_next_step(increment: PlantIncrement, production: float, step: float):
    """Forecast the increment's production one time-step of `step` days ahead."""
    times = np.array([TODAY, TODAY + step])
    forecast = _calculate_increments_production(
        [increment], np.array([production]), LIFETIME, TODAY, times
    )

    return forecast[1]


def _production_after_step(producer: SimpleNamespace, production: float) -> float:
    return sum(inc.multiplier for inc in producer.increments[0]) * production


@pytest.mark.parametrize(
    ("age", "age_span", "multiplier", "production", "step", "expected"),
    [
        # the 1-year entry window starts half a year ahead, so half the
        # 2 plants of 100 tons/year each are on stream a year from now
        pytest.param(-1.5, 1.0, 2.0, 100.0, YEAR, 100.0, id="window_straddles_step"),
        # the 365-day entry window starts 365 days ahead, so a 366-day step
        # delivers 1 day of it: 1/365 of a plant of 365 tons/year
        pytest.param(
            -730.0 / YEAR,
            365.0 / YEAR,
            1.0,
            365.0,
            366.0,
            1.0,
            id="leap_year_step",
        ),
    ],
)
def test_pipeline_forecast_matches_delivery(
    age, age_span, multiplier, production, step, expected
):
    increment = PlantIncrement(multiplier, age, age_span, decided=0.0)
    forecast = _forecast_next_step(increment, production, step)

    producer = _make_producer(replace(increment), delivered=False)
    producer.pipeline[0][0].age += step / YEAR
    perform_pipeline_delivery(producer)

    assert forecast == pytest.approx(expected, rel=REL_TOL)
    assert _production_after_step(producer, production) == pytest.approx(
        expected, rel=REL_TOL
    )


@pytest.mark.parametrize(
    ("age", "age_span", "multiplier", "production", "step", "expected"),
    [
        # the 1-year exit window starts half a year ahead of the 20-year
        # lifetime, so half the 2 plants of 100 tons/year each remain a year
        # from now
        pytest.param(18.5, 1.0, 2.0, 100.0, YEAR, 100.0, id="window_straddles_step"),
        # the 0.5-year exit window starts now, so a quarter-year step removes
        # half the plant of 100 tons/year
        pytest.param(19.5, 0.5, 1.0, 100.0, 0.25 * YEAR, 50.0, id="already_exiting"),
        # the 365-day exit window starts 365 days ahead, so a 366-day step
        # removes 1 day of it: 1/365 of a plant of 365 tons/year
        pytest.param(
            LIFETIME - 730.0 / YEAR,
            365.0 / YEAR,
            1.0,
            365.0,
            366.0,
            364.0,
            id="leap_year_step",
        ),
    ],
)
def test_existing_forecast_matches_decommissioning(
    age, age_span, multiplier, production, step, expected
):
    increment = PlantIncrement(multiplier, age, age_span, decided=age)
    forecast = _forecast_next_step(increment, production, step)

    producer = _make_producer(replace(increment), delivered=True)
    producer.increments[0][0].age += step / YEAR
    perform_decommissioning(producer)

    assert forecast == pytest.approx(expected, rel=REL_TOL)
    assert _production_after_step(producer, production) == pytest.approx(
        expected, rel=REL_TOL
    )
