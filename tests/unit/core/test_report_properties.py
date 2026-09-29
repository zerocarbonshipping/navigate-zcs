# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
A Report command's property token resolves to a getter on its own profile class.

The report writer calls the getter without arguments, so a getter that needs one
is refused like a missing one.
"""

from __future__ import annotations

import pytest

from navigate.core.profiles import FleetProfile
from navigate.core.report_properties import resolve_getter


def test_a_token_resolves_to_the_getter_of_its_command():
    assert resolve_getter("add_fleet_property", "CargoMiles") == "get_cargo_miles"


@pytest.mark.parametrize(
    ("command", "token"),
    [
        ("add_fleet_property", "CargoMils"),
        # BunkerPrice is a port getter, which no vessel profile carries
        ("add_vessel_property", "BunkerPrice"),
    ],
    ids=["unknown_token", "token_of_another_command"],
)
def test_a_token_the_command_does_not_report_is_refused(command, token):
    with pytest.raises(ValueError, match=rf"'{token}'.*{command}"):
        resolve_getter(command, token)


def test_a_getter_that_requires_an_argument_is_refused(monkeypatch):
    # tests/unit/core/test_profile_getters.py keeps every real profile getter
    # argument-free, so the fleet profile is handed one that is not
    def get_keyed_probe(self, key):
        return key

    monkeypatch.setattr(FleetProfile, "get_keyed_probe", get_keyed_probe, raising=False)

    with pytest.raises(ValueError, match="'KeyedProbe'"):
        resolve_getter("add_fleet_property", "KeyedProbe")
