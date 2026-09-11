# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for Regulation threshold validation and profile output."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

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
    "scheme, measure",
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


def test_calculate_profile_writes_policed_vessel_thresholds():
    regulation = _make_regulation("FLEXIBLE", "INTENSITY")
    regulation.set_vessel_threshold("*", 10.0)
    regulation.in_jurisdiction_vessel = {"v1": True, "v2": False}
    regulation.initialize()

    regulation.profile = MagicMock()
    regulation.calculate_profile(idx=0)

    regulation.profile.set_vessel_threshold.assert_called_once_with(0, "v1", 10.0)
