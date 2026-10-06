# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for Route voyage-distribution, its accepted kinds, and setter logging."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from navigate.core import Scalar
from navigate.core.enum_ import RouteTypeID
from navigate.core.nodes.forecast import Forecast
from navigate.core.nodes.route import Route


def _mock_port(name):
    port = MagicMock()
    port.name = name
    return port


def _make_regional_route(voyage_distribution):
    route = Route("r")
    route.route_type = RouteTypeID.REGIONAL_TRIP
    route.ports = [_mock_port("a"), _mock_port("b")]
    route.speeds = [Scalar(10.0)]
    route.condition_distribution = [1.0]
    route.time_at_sea = 0.5
    route.voyage_distribution = dict(voyage_distribution)
    route.initialize_dependencies()
    route.initialize()
    return route


class TestVoyageDistributionNormalization:
    def test_fractions_normalized_to_unity(self):
        # pairs left unassigned, here the port-to-itself legs, fill to zero
        route = _make_regional_route({("a", "b"): Scalar(0.6), ("b", "a"): Scalar(0.2)})

        fractions = route.get_voyage_distribution()
        assert fractions[("a", "b")] == pytest.approx(0.75)
        assert fractions[("b", "a")] == pytest.approx(0.25)
        assert fractions[("a", "a")] == pytest.approx(0.0)
        assert fractions[("b", "b")] == pytest.approx(0.0)

    def test_zero_total_splits_equally(self):
        route = _make_regional_route({})

        fractions = route.get_voyage_distribution()
        assert len(fractions) == 4
        assert all(fraction == pytest.approx(0.25) for fraction in fractions.values())

    def test_reinitialize_refreshes_the_cache(self):
        # an EVENTS re-assignment reaches the node as a mutated dict followed
        # by another initialize() run
        route = _make_regional_route({("a", "b"): Scalar(1.0)})
        route.voyage_distribution[("a", "b")] = Scalar(0.25)
        route.voyage_distribution[("b", "a")] = Scalar(0.75)
        route.initialize()

        fractions = route.get_voyage_distribution()
        assert fractions[("a", "b")] == pytest.approx(0.25)
        assert fractions[("b", "a")] == pytest.approx(0.75)

    def test_to_array_orders_inner_index_by_origin_port(self):
        route = _make_regional_route(
            {("a", "b"): Scalar(0.75), ("b", "a"): Scalar(0.25)}
        )

        # to_array orders as (origin, destination) pairs: aa, ba, ab, bb
        values = route.get_voyage_distribution(to_array=True)
        assert values == pytest.approx([0.0, 0.25, 0.75, 0.0])


def test_voyage_distribution_rejects_a_forecast():
    # a fraction is a float or a Variable; a Forecast is refused like any
    # other node type the setter does not accept
    route = Route("r")
    route.ports = [_mock_port("a"), _mock_port("b")]
    route.initialize_dependencies()

    with pytest.raises(
        ValueError,
        match=(
            r"only allows assignment of scalars and nodes of type Variable, "
            r'but got Forecast\("f"\)'
        ),
    ):
        route.set_voyage_distribution("a", "b", Forecast("f"))


@pytest.mark.parametrize(
    ("distribution", "warnings"),
    [([0.4, 0.4], 1), ([0.5, 0.505], 0)],
    ids=["beyond_one_percent", "within_one_percent"],
)
def test_condition_distribution_rescale_warns_only_beyond_one_percent(
    caplog, distribution, warnings
):
    with caplog.at_level(logging.WARNING):
        Route("r").set_condition_distribution(distribution)

    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == warnings
    assert all(
        "'ConditionDistribution' is rescaled proportionally to sum to 1." in message
        for message in messages
    )
