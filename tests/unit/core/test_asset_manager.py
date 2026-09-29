# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the shared _AssetManager increment infrastructure."""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core.expression import Expression
from navigate.core.increment import Increment
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.fleet import Fleet
from navigate.core.nodes.forecast import Forecast
from navigate.core.nodes.producer import Producer
from navigate.core.nodes.vessel import Vessel
from navigate.core.table_data import TableData
from navigate.util import YEAR


class TestUpdateIncrementAges:
    """Test aging across the registered increment stores."""

    def test_producer_ages_increments_and_pipeline(self):
        producer = Producer("producer")
        producer.increments.append([Increment(multiplier=1.0, age=2.0, age_span=1.0)])
        producer.pipeline.append(
            [Increment(multiplier=1.0, age=-1.5, age_span=1.0, decided=0.0)]
        )

        producer.update_increment_ages(time_step=YEAR / 2.0)

        assert producer.increments[0][0].age == pytest.approx(2.5)
        assert producer.pipeline[0][0].age == pytest.approx(-1.0)
        assert producer.pipeline[0][0].decided == pytest.approx(0.5)


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
    Inputs read for their table, never evaluated, reject INF entries themselves.

    No bound an attribute imposes reaches a table that is never evaluated, so
    an infinite count or fraction would otherwise enter the model unchecked.
    """

    def test_existing_pipeline(self):
        producer = Producer("producer")
        producer.existing_pipelines = {"plant": _cumulative_forecast(np.inf)}

        with pytest.raises(
            ValueError, match=r'Pipeline \(Forecast\("counts"\)\) must hold finite'
        ):
            producer.check_consistency()

    def test_orderbook(self):
        fleet = Fleet("fleet")
        fleet.assets = [Vessel("vessel")]
        fleet.orderbooks = [_cumulative_forecast(np.inf)]

        with pytest.raises(
            ValueError, match=r'Orderbook \(Forecast\("counts"\)\) must hold finite'
        ):
            fleet.check_consistency()

    @pytest.mark.parametrize(
        "rows",
        [[[0.0, 0.5], [1.0, np.inf]], [[0.0, 0.5], [np.inf, 0.5]]],
        ids=["infinite_fraction", "infinite_age"],
    )
    def test_initial_age_distribution(self, rows):
        curve = Curve("ages")
        curve.set_table(TableData(rows=rows))
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
        producer.existing_pipelines = {"plant": _cumulative_forecast(2.0)}
        producer.check_consistency()
