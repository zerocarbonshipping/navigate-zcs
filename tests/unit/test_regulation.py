# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for Regulation threshold validation and profile output."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from navigate.core.enum_ import RegulationSchemeID
from navigate.core.expression import Expression
from navigate.core.nodes.regulation import Regulation


def _make_regulation(scheme, measure, vessels=("v1", "v2")):
    regulation = Regulation("reg")
    regulation.set_scheme(scheme)
    regulation.set_measure(measure)

    regulation.jurisdiction = [MagicMock()]
    regulation.emissions = [MagicMock()]
    regulation.fuels = [MagicMock()]

    regulation.include_vessel = dict.fromkeys(vessels, True)
    regulation.vessel_threshold = dict.fromkeys(vessels)

    return regulation


@pytest.mark.parametrize(
    ("scheme", "measure"),
    [
        ("INDIVIDUAL", "ABSOLUTE"),
        ("FLEXIBLE", "TRANSPORT"),
    ],
)
def test_initialize_raises_for_included_vessel_without_threshold(scheme, measure):
    # the guard is scheme/measure-independent; these two combinations stand in for the
    # full cross product
    regulation = _make_regulation(scheme, measure)
    regulation.set_vessel_threshold("v1", 10.0)

    with pytest.raises(ValueError, match="no vessel_threshold"):
        regulation.initialize()


def test_initialize_ignores_excluded_vessels_without_threshold():
    regulation = _make_regulation("INDIVIDUAL", "ABSOLUTE")
    regulation.include_vessel["v2"] = False
    regulation.set_vessel_threshold("v1", 10.0)

    regulation.initialize()


def test_flexibility_horizon_warns_when_assigned_under_individual_scheme(caplog):
    regulation = _make_regulation("INDIVIDUAL", "ABSOLUTE", vessels=())
    regulation.set_flexibility_horizon(5.0)

    with caplog.at_level(logging.WARNING):
        regulation.initialize()

    assert [record.getMessage() for record in caplog.records] == [
        "Regulation(\"reg\"): 'FlexibilityHorizon' is assigned but is unused for"
        " Scheme = INDIVIDUAL."
    ]


def test_flexibility_horizon_default_does_not_warn_under_individual_scheme(caplog):
    regulation = _make_regulation("INDIVIDUAL", "ABSOLUTE", vessels=())

    with caplog.at_level(logging.WARNING):
        regulation.initialize()

    assert caplog.records == []


def test_flexibility_horizon_does_not_warn_when_assigned_under_flexible_scheme(caplog):
    regulation = _make_regulation("FLEXIBLE", "ABSOLUTE", vessels=())
    regulation.set_flexibility_horizon(5.0)

    with caplog.at_level(logging.WARNING):
        regulation.initialize()

    assert caplog.records == []


def test_flexibility_horizon_warns_once_per_assignment_under_individual_scheme(caplog):
    # the parser reruns check_consistency() on every EVENTS pass regardless of
    # whether that pass touched the node, so a repeated pass must stay silent
    regulation = _make_regulation("INDIVIDUAL", "ABSOLUTE", vessels=())
    regulation.set_flexibility_horizon(5.0)

    with caplog.at_level(logging.WARNING):
        regulation.initialize()
        regulation.reinitialize()

    assert len(caplog.records) == 1

    caplog.clear()
    regulation.set_flexibility_horizon(6.0)

    with caplog.at_level(logging.WARNING):
        regulation.reinitialize()

    assert len(caplog.records) == 1


def test_flexibility_horizon_warns_once_if_scheme_stops_being_flexible(caplog):
    # an assignment that was never reported as unused stays pending across passes,
    # so it still warns once the scheme it was assigned under is no longer FLEXIBLE
    regulation = _make_regulation("FLEXIBLE", "ABSOLUTE", vessels=())
    regulation.set_flexibility_horizon(5.0)

    with caplog.at_level(logging.WARNING):
        regulation.initialize()

    assert caplog.records == []

    regulation.scheme = RegulationSchemeID.INDIVIDUAL

    with caplog.at_level(logging.WARNING):
        regulation.reinitialize()

    assert len(caplog.records) == 1


def test_calculate_profile_writes_policed_vessel_thresholds():
    regulation = _make_regulation("FLEXIBLE", "INTENSITY")
    regulation.set_vessel_threshold("*", 10.0)
    regulation.in_jurisdiction_vessel = {"v1": True, "v2": False}
    regulation.initialize()

    regulation.profile = MagicMock()
    regulation.calculate_profile(idx=0)

    regulation.profile.set_vessel_threshold.assert_called_once_with(0, "v1", 10.0)


def test_jurisdiction_rejects_an_expression():
    # a jurisdiction is a list of ports, read as nodes and never evaluated
    regulation = Regulation("reg")

    with pytest.raises(ValueError, match="nodes of type Port, but got expression"):
        regulation.set_jurisdiction([Expression('Port("x")')])
