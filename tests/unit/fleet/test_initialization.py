# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for assigning vessels to the fleets that list them."""

from __future__ import annotations

import re

import pytest

from navigate.core.nodes.fleet import Fleet
from navigate.core.nodes.vessel import Vessel
from navigate.fleet import assign_vessels_to_fleets


def _fleet(name: str, vessels: list[Vessel]) -> Fleet:
    fleet = Fleet(name)
    fleet.set_vessels(vessels)
    return fleet


def test_a_vessel_listed_in_a_second_fleet_is_rejected():
    shared = Vessel("shared")
    fleets = [_fleet("first", [shared]), _fleet("second", [Vessel("own"), shared])]

    message = (
        'Fleet("second"): Vessel("shared") is already assigned to a different'
        ' fleet, Fleet("first").'
    )
    with pytest.raises(ValueError, match=re.escape(message)):
        assign_vessels_to_fleets(fleets)
