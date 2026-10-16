# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Add the vessel and regulation variables of the LP that do not exist yet."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.bunker._build import add_variable
from navigate.simulation.bunker.utils import get_port_converters

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


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
    port_converters = get_port_converters(vessel)
    fuels_per_converter = vessel.fuels_per_converter
    leg_idx = route.get_legs()
    port_idx = range(len(ports))

    for p, port in enumerate(ports):
        for f in usable_fuels:
            if port.is_bunkering_allowed(f):
                add_variable(alg, alg.bunker, (v, p, f), "bunker")

    for c, burned in fuels_per_converter.items():
        for f in burned:
            for port_start, port_end in leg_idx:
                add_variable(
                    alg, alg.spend_sea, (v, c, f, port_start, port_end), "spend_sea"
                )

    # only the converters serving port energy demands spend in port
    for c in port_converters:
        for f in fuels_per_converter[c]:
            for p in port_idx:
                add_variable(alg, alg.spend_port, (v, c, f, p), "spend_port")

    for p in route.get_tank_stops():
        for f in usable_fuels:
            add_variable(alg, alg.mass_tank, (v, p, f), "mass_tank")

    shore_power_limits = vessel.expectation.get_shore_power_limit_port(alg.idx)

    for p, limit in enumerate(shore_power_limits):
        if limit > 0.0:
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
        add_variable(
            alg, alg.remedial_factor_individual, key, "remedial_factor_individual"
        )

    for r in alg.regulation_total_rhs_flexibility:
        add_variable(
            alg, alg.remedial_factor_flexibility, r, "remedial_factor_flexibility"
        )
