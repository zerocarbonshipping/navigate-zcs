# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The property tokens each Report command accepts, checked as the command runs.

A command's token must name a getter on the profile class of the nodes the
command reports on; navigate.parser._commands checks each Report command
against it.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

from navigate.core.profiles import (
    FleetProfile,
    GlobalProfile,
    LevyProfile,
    PlantProfile,
    PortProfile,
    ProducerProfile,
    RegulationProfile,
    VesselProfile,
)
from navigate.util import attribute_to_setter

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from navigate.core.profiles._base_profile import _BaseProfile

PROFILE_CLASSES: dict[str, type[_BaseProfile]] = {
    "add_property": GlobalProfile,
    "add_fleet_property": FleetProfile,
    "add_levy_property": LevyProfile,
    "add_plant_property": PlantProfile,
    "add_port_property": PortProfile,
    "add_producer_property": ProducerProfile,
    "add_regulation_property": RegulationProfile,
    "add_vessel_property": VesselProfile,
}


def check_report_command(
    command: str, method: Callable[..., object], inputs: Sequence[object]
) -> None:
    """
    Check the property token a Report command is called with.

    Parameters
    ----------
    command
        Name of the Report command.
    method
        The Report node's bound method for the command.
    inputs
        The command's deck inputs, whose count the caller has already checked.

    Raises
    ------
    ValueError
        If the command does not report the property its token names.
    """
    token = inspect.signature(method).bind(*inputs).arguments["attribute"]
    check_report_property(command, token)


def check_report_property(command: str, token: str) -> None:
    """
    Check that a Report command reports the property a token names.

    Parameters
    ----------
    command
        Name of the Report command, e.g. ``add_fleet_property``.
    token
        The property token as a deck writes it, e.g. ``CargoMiles``.

    Raises
    ------
    ValueError
        If the command's profile class has no getter for the token.
    """
    if not hasattr(PROFILE_CLASSES[command], attribute_to_setter(token, method="get")):
        raise ValueError(
            f"does not report the property '{token}'; the properties {command}"
            " reports are listed in the 'Report Node Properties' appendix on the"
            " Report page of the reference manual"
        )
