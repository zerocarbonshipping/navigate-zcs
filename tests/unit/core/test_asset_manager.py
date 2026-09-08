# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the shared _AssetManager increment infrastructure."""
import pytest

from navigate.core.increment import Increment
from navigate.core.nodes.producer import Producer
from navigate.util import YEAR


class TestUpdateIncrementAges:
    """Test aging across the registered increment stores."""

    def test_producer_ages_increments_and_pipeline(self):
        producer = Producer('producer')
        producer.increments.append([Increment(multiplier=1., age=2., dt=1.)])
        producer.pipeline.append([Increment(multiplier=1., age=-1.5, dt=1., decided=0.)])

        producer.update_increment_ages(time_step=YEAR / 2.)

        assert producer.increments[0][0].age == pytest.approx(2.5)
        assert producer.pipeline[0][0].age == pytest.approx(-1.)
        assert producer.pipeline[0][0].decided == pytest.approx(0.5)
