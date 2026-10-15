# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the inputs Fleet and Producer share through _AssetManager."""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core.expression import Expression
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.fleet import Fleet
from navigate.core.nodes.forecast import Forecast
from navigate.core.nodes.plant import Plant
from navigate.core.nodes.producer import Producer
from navigate.core.table_data import TableData


class TestExpressionsRejected:
    """Inputs read for their table, never evaluated, take no expression."""

    def test_existing_pipeline(self):
        producer = Producer("producer")
        producer.existing_pipelines = {"plant": None}

        with pytest.raises(
            ValueError, match="nodes of type Forecast, but got expression"
        ):
            producer.set_existing_pipeline("plant", Expression('Forecast("f") * 2'))

    def test_initial_age_distribution(self):
        with pytest.raises(ValueError, match="nodes of type Curve, but got expression"):
            Fleet("fleet").set_initial_age_distribution([Expression('Curve("c")')])


def _cumulative_forecast(last):
    forecast = Forecast("counts")
    forecast.set_table(TableData(rows=[["01-01-2026", 1.0], ["01-01-2030", last]]))
    forecast.replace_reference_table(np.datetime64("2026-01-01"))
    return forecast


class TestInfiniteTableEntriesRejected:
    """
    Inputs read for their table, never evaluated, reject INF values themselves.

    The existing pipeline and the initial age distribution are read through
    their table's values, so no bound an attribute imposes ever reaches them,
    and an infinite plant count or fraction would enter the model unchecked.
    """

    def test_existing_pipeline(self):
        producer = Producer("producer")
        producer.set_plants(Plant("plant"))
        producer.existing_pipelines = {"plant": _cumulative_forecast(np.inf)}

        with pytest.raises(
            ValueError, match=r'Pipeline \(Forecast\("counts"\)\) must hold finite'
        ):
            producer.initialize()

    def test_initial_age_distribution(self):
        curve = Curve("ages")
        curve.set_table(TableData(rows=[[0.0, 0.5], [1.0, np.inf]]))
        curve.build_table()
        fleet = Fleet("fleet")
        fleet.set_initial_age_distribution([curve])

        with pytest.raises(
            ValueError,
            match=r'InitialAgeDistribution \(Curve\("ages"\)\) must hold finite',
        ):
            fleet._check_initial_age_distribution_is_finite()

    def test_finite_tables_pass(self):
        producer = Producer("producer")
        producer.set_plants(Plant("plant"))
        producer.existing_pipelines = {"plant": _cumulative_forecast(2.0)}
        producer.initialize()
