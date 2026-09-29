# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Resolve the property token of a Report command to the profile getter it reads.

navigate.core.node_report resolves each token as the Report node records it.
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
from navigate.util import attribute_to_setter

if TYPE_CHECKING:
    from collections.abc import Callable

PROFILE_CLASSES: dict[str, type] = {
    "add_property": ManagerProfile,
    "add_fleet_property": FleetProfile,
    "add_levy_property": LevyProfile,
    "add_plant_property": PlantProfile,
    "add_port_property": PortProfile,
    "add_producer_property": ProducerProfile,
    "add_regulation_property": RegulationProfile,
    "add_vessel_property": VesselProfile,
}


def is_argument_free(function: Callable[..., object]) -> bool:
    """
    Check whether the report writer can call a bound getter without arguments.

    ``report_writer._extract_properties`` calls ``getattr(profile, getter)()``, so
    every parameter past ``self`` must carry a default or be variadic.

    Parameters
    ----------
    function
        The unbound getter read off the profile class.

    Returns
    -------
    bool
        Whether the getter takes no required argument beyond ``self``.
    """
    parameters = list(inspect.signature(function).parameters.values())[1:]

    return all(
        p.default is not inspect.Parameter.empty
        or p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        for p in parameters
    )


def resolve_getter(command: str, token: str) -> str:
    """
    Name the profile getter a Report command reads for a property token.

    Parameters
    ----------
    command
        The Report command the token is passed to, e.g. ``add_fleet_property``.
    token
        The property token as a deck writes it, e.g. ``CargoMiles``.

    Returns
    -------
    str
        The getter name, e.g. ``get_cargo_miles``.

    Raises
    ------
    ValueError
        If the command's profile class has no getter for the token that takes
        no argument.
    """
    getter = attribute_to_setter(token, method="get")
    getters = dict(inspect.getmembers(PROFILE_CLASSES[command], inspect.isfunction))
    candidate = getters.get(getter)

    if candidate is None or not is_argument_free(candidate):
        raise ValueError(
            f"does not report the property '{token}'; the properties {command}"
            " reports are listed in the 'Report Node Properties' appendix on the"
            " Report page of the reference manual"
        )

    return getter
