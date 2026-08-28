# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

import navigate.core.enum_ as enum_
from navigate.bunker._build import add_variable
from navigate.bunker.utils import get_converters, get_port_converters


def update_vessel_variables(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Update all variables related to a single vessel.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which variables are updated.
    """

    v = vessel.name
    route = vessel.route
    ports = route.ports
    usable_fuels = vessel.usable_fuels
    converters = get_converters(vessel)
    port_converters = get_port_converters(vessel)
    fuels_per_converter = alg.fuels_per_converter
    leg_idx = route.get_leg_indices()
    port_idx = range(len(ports))

    # add bunker variables
    for p, port in enumerate(ports):
        for f in usable_fuels:
            if port.is_bunkering_allowed(f):
                add_variable(alg, alg.bunker, (v, p, f), "bunker")

    # add spend at sea variables
    for c in converters:
        for f in fuels_per_converter[v, c]:
            for port_start, port_end in leg_idx:
                add_variable(alg, alg.spend_sea, (v, c, f, port_start, port_end), "spend_sea")

    # add spend in port variables (only for converters with port energy demand)
    for c in port_converters:
        for f in fuels_per_converter[v, c]:
            for p in port_idx:
                add_variable(alg, alg.spend_port, (v, c, f, p), "spend_port")

    # add mass variables
    if route.route_type == enum_.RouteTypeID.ROUND_TRIP:
        for p in port_idx:
            for f in usable_fuels:
                add_variable(alg, alg.mass_tank, (v, p, f), "mass_tank")

    # add shore power variables
    vessel_capacity = vessel.expectation.get_shore_power_capacity(alg.idx)

    if vessel_capacity > 0.:
        for p, port in enumerate(ports):

            connection_share = port.expectation.get_shore_power_connection_share(alg.idx)

            if connection_share > 0.:
                add_variable(alg, alg.shore_power, (v, p), "shore_power")


def update_regulation_variables(alg: BunkerAlgorithm) -> None:
    """
    Update regulation remedial factor variables.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    for key in alg.regulation_rhs_individual:
        add_variable(alg, alg.remedial_factor_individual, key, "remedial_factor_individual")

    for key in alg.regulation_total_rhs_flexibility:
        add_variable(alg, alg.remedial_factor_flexibility, key, "remedial_factor_flexibility")
