# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the kinds Route voyage shares accept, and setter logging."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from navigate.core.nodes.forecast import Forecast
from navigate.core.nodes.route import Route
from navigate.core.nodes.variable import Variable


def _mock_port(name):
    port = MagicMock()
    port.name = name
    return port


def _variable(value):
    variable = Variable("v")
    variable.set_value(value)
    return variable


class TestSetVoyageDistributionAcceptedKinds:
    """`set_voyage_distribution` accepts a float or a Variable, rejects a Forecast."""

    def _make_route(self):
        route = Route("r")
        route.ports = [_mock_port("a"), _mock_port("b")]
        route.initialize_dependencies()
        return route

    @pytest.mark.parametrize(
        "make_fraction",
        [lambda: 0.5, lambda: _variable(0.5)],
        ids=["float", "variable"],
    )
    def test_accepted_kinds_are_stored_under_the_port_pair(self, make_fraction):
        route = self._make_route()

        route.set_voyage_distribution("a", "b", make_fraction())

        assert route.voyage_distribution[("a", "b")].get(None, None) == pytest.approx(
            0.5
        )

    def test_forecast_is_rejected_like_any_unaccepted_node_type(self):
        route = self._make_route()

        with pytest.raises(
            ValueError,
            match=(
                r"only allows assignment of scalars and nodes of type Variable, "
                r'but got Forecast\("f"\)'
            ),
        ):
            route.set_voyage_distribution("a", "b", Forecast("f"))


class TestSetConditionDistributionRescaleLogging:
    """`set_condition_distribution` warns only once the rescale exceeds 1%."""

    def test_rescale_beyond_one_percent_logs_a_warning(self, caplog):
        route = Route("r")

        with caplog.at_level(logging.WARNING):
            route.set_condition_distribution([0.4, 0.4])

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert (
            "'ConditionDistribution' is rescaled proportionally to sum to 1."
            in warnings[0].getMessage()
        )

    def test_rescale_within_one_percent_logs_nothing(self, caplog):
        route = Route("r")

        with caplog.at_level(logging.WARNING):
            route.set_condition_distribution([0.5, 0.505])

        assert caplog.records == []
