# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Report properties named in committed decks resolve to profile getters.

Report properties have no parser-side allow-list: navigate.output.report_writer resolves the
getter on the node's profile at write time and skips the column with a logged error when it is
missing. This test pins the committed surface instead: every property token in a committed
deck must map, via attribute_to_setter, to a getter on the profile class of the command it is
passed to, callable without arguments the way the report writer calls it.

The deck scan is regex-based and expects single-line property calls, like the committed decks.
"""

from __future__ import annotations

import inspect
import re

import pytest

from helpers.simulation import REPO_ROOT
from navigate.core.profiles import (
    FleetProfile,
    LevyProfile,
    ManagerProfile,
    PlantProfile,
    PortProfile,
    ProducerProfile,
    RegulationProfile,
    VesselProfile,
)
from navigate.parser._commands import _REPORT_COMMANDS
from navigate.util import attribute_to_setter

PROFILE_CLASSES = {
    "add_property": ManagerProfile,
    "add_fleet_property": FleetProfile,
    "add_levy_property": LevyProfile,
    "add_plant_property": PlantProfile,
    "add_port_property": PortProfile,
    "add_producer_property": ProducerProfile,
    "add_regulation_property": RegulationProfile,
    "add_vessel_property": VesselProfile,
}

assert set(PROFILE_CLASSES) == set(_REPORT_COMMANDS)

_PROPERTY_CALL = re.compile(
    r'\b({})\(\s*(?:"[^"]*"\s*,\s*)?([A-Za-z][A-Za-z0-9]*)'.format(
        "|".join(PROFILE_CLASSES)
    )
)
_COMMENT = re.compile(r"#[^\n]*")


def _deck_properties():
    """Every distinct (command, token) pair used in a committed .inc/.nav file."""
    found = {}
    for directory in ("assumptions", "simulations", "tests", "tutorials"):
        for path in sorted((REPO_ROOT / directory).rglob("*")):
            if path.suffix in (".inc", ".nav"):
                for pair in _PROPERTY_CALL.findall(_COMMENT.sub("", path.read_text())):
                    found.setdefault(pair, path)

    # every report command stays exercised by some committed deck; an empty scan means the
    # scanner rotted, not that the repo is clean
    assert {command for command, _ in found} == set(PROFILE_CLASSES)

    return [
        pytest.param(command, token, id=f"{path.relative_to(REPO_ROOT)}:{token}")
        for (command, token), path in found.items()
    ]


@pytest.mark.parametrize("command, token", _deck_properties())
def test_deck_report_properties_resolve(command, token):
    profile_class = PROFILE_CLASSES[command]
    getter_name = attribute_to_setter(token, method="get")

    assert hasattr(profile_class, getter_name), (
        f"'{token}' does not resolve: {profile_class.__name__} has no getter '{getter_name}'"
    )

    parameters = list(
        inspect.signature(getattr(profile_class, getter_name)).parameters.values()
    )[1:]
    assert all(
        p.default is not inspect.Parameter.empty
        or p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        for p in parameters
    ), (
        f"'{token}' resolves to {profile_class.__name__}.{getter_name}, which the report writer cannot call without arguments"
    )
