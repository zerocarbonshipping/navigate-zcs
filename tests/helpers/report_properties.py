# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Shared state for the tests that check report properties against profile getters.

Used by tests/attribute: the committed-deck scan in test_report_properties.py and
the report-property checks over the reference manual.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

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
from navigate.core.profiles._base_profile import _BaseProfile
from navigate.parser._commands import _REPORT_COMMANDS
from navigate.util import attribute_to_setter

if TYPE_CHECKING:
    from collections.abc import Callable

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

# public getters declared on _BaseProfile itself describe the timeline a profile
# is sized to rather than a result, so no report property names them
PLUMBING_GETTERS = {name for name in vars(_BaseProfile) if name.startswith("get_")}

assert sorted(PLUMBING_GETTERS) == ["get_length", "get_shape"]


def is_argument_free(function: Callable[..., object]) -> bool:
    """
    Check whether the report writer can call a bound getter without arguments.

    ``report_writer._extract_properties`` calls ``getattr(profile, getter)()``, so
    every parameter past ``self`` must carry a default or be variadic.

    Parameters
    ----------
    function : callable
        The unbound getter read off the profile class.

    Returns
    -------
    bool :
        Whether the getter takes no required argument beyond ``self``.
    """
    parameters = list(inspect.signature(function).parameters.values())[1:]

    return all(
        p.default is not inspect.Parameter.empty
        or p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        for p in parameters
    )


def getter_for(token: str) -> str:
    """
    Name the profile getter a report-property token resolves to.

    Parameters
    ----------
    token : str
        The property token as a deck writes it, e.g. ``TotalEquivalentWTT``.

    Returns
    -------
    str :
        The getter name, e.g. ``get_total_equivalent_wtt``.
    """
    return attribute_to_setter(token, method="get")


def token_for(getter: str) -> str:
    """
    Spell the report-property token a profile getter would be reached by.

    ``attribute_to_setter`` is lossy - it drops every character outside an
    ``[A-Z][a-z]*`` run - so this is a candidate token, not an inverse: a caller
    must check that ``getter_for`` maps it back to the getter it started from.

    Parameters
    ----------
    getter : str
        A getter name on a profile class, e.g. ``get_total_equivalent_wtt``.

    Returns
    -------
    str :
        The candidate token, e.g. ``TotalEquivalentWtt``.
    """
    return "".join(part.capitalize() for part in getter.removeprefix("get_").split("_"))
