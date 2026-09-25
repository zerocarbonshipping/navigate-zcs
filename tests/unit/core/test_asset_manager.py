# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the shared _AssetManager increment infrastructure."""

from __future__ import annotations

import pytest

from navigate.core.expression import Expression
from navigate.core.increment import Increment
from navigate.core.nodes.fleet import Fleet
from navigate.core.nodes.producer import Producer
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
