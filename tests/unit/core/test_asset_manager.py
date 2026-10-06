# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the shared _AssetManager increment infrastructure."""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core.expression import Expression
from navigate.core.increment import PlantIncrement
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.fleet import Fleet
from navigate.core.nodes.forecast import Forecast
from navigate.core.nodes.producer import Producer
from navigate.core.table_data import TableData
from navigate.util import YEAR


class TestUpdateIncrementAges:
    """Test aging across the registered increment stores."""

    def test_producer_ages_increments_and_pipeline(self):
        producer = Producer("producer")
        producer.increments.append(
            [PlantIncrement(multiplier=1.0, age=2.0, age_span=1.0, decided=0.0)]
        )
        producer.pipeline.append(
            [PlantIncrement(multiplier=1.0, age=-1.5, age_span=1.0, decided=0.0)]
        )

        producer.update_increment_ages(time_step=YEAR / 2.0)

        assert producer.increments[0][0].age == pytest.approx(2.5)
        assert producer.increments[0][0].decided == pytest.approx(0.5)
        assert producer.pipeline[0][0].age == pytest.approx(-1.0)
        assert producer.pipeline[0][0].decided == pytest.approx(0.5)


def _assign_existing_pipeline(assignment):
    producer = Producer("producer")
    producer.existing_pipelines = {"plant": None}
    producer.set_existing_pipeline("plant", assignment)


def _assign_initial_age_distribution(assignment):
    Fleet("fleet").set_initial_age_distribution([assignment])


@pytest.mark.parametrize(
    ("assign", "type_"),
    [
        (_assign_existing_pipeline, "Forecast"),
        (_assign_initial_age_distribution, "Curve"),
    ],
)
def test_an_input_read_for_its_table_rejects_an_expression(assign, type_):
    # the table is read directly, never evaluated, so an expression there has
    # nothing to evaluate it
    with pytest.raises(ValueError, match=f"nodes of type {type_}, but got expression"):
        assign(Expression(f'{type_}("x") * 2'))


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
        producer.existing_pipelines = {"plant": _cumulative_forecast(np.inf)}

        with pytest.raises(
            ValueError, match=r'Pipeline \(Forecast\("counts"\)\) must hold finite'
        ):
            producer.check_consistency()

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
