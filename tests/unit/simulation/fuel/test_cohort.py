# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.simulation.fuel.cohort."""

from __future__ import annotations

import pytest

from navigate.core.increment import PlantIncrement
from navigate.core.nodes.producer import Producer
from navigate.simulation.fuel.cohort import age_producer_cohorts
from navigate.util import YEAR


class TestAgeProducerCohorts:
    """Test ageing of the built and the pipeline cohorts."""

    def test_producer_ages_increments_and_pipeline(self):
        producer = Producer("producer")
        producer.increments.append(
            [PlantIncrement(multiplier=1.0, age=2.0, age_span=1.0, decided=0.0)]
        )
        producer.pipeline.append(
            [PlantIncrement(multiplier=1.0, age=-1.5, age_span=1.0, decided=0.0)]
        )

        age_producer_cohorts(producer, time_step=YEAR / 2.0)

        assert producer.increments[0][0].age == pytest.approx(2.5)
        assert producer.increments[0][0].decided == pytest.approx(0.5)
        assert producer.pipeline[0][0].age == pytest.approx(-1.0)
        assert producer.pipeline[0][0].decided == pytest.approx(0.5)
