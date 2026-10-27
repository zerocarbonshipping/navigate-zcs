# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Add the vessel and regulation variables of the LP, and set their bounds."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.bunker._build import add_variable
from navigate.simulation.bunker._indices import get_port_converters

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def update_vessel_variables(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Add the LP variables of a vessel that do not exist yet, and bound its shore power.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel whose variables are updated.
    """
    v = vessel.name
    route = vessel.route
    legs = route.get_legs()
    stops = route.get_stops()
    fuels_per_converter = vessel.fuels_per_converter

    for p, port in enumerate(route.ports):
        for f in vessel.usable_fuels:
            if port.bunkering_allowed[f]:
                add_variable(alg, alg.bunker, (v, p, f), "bunker")

    for c, fuels in fuels_per_converter.items():
        for f in fuels:
            for leg in legs:
                add_variable(alg, alg.spend_sea, (v, c, f, *leg), "spend_sea")

    # only the converters serving port energy demands spend in port
    for c in get_port_converters(vessel):
        for f in fuels_per_converter[c]:
            for p in stops:
                add_variable(alg, alg.spend_port, (v, c, f, p), "spend_port")

    for p in route.get_tank_stops():
        for f in vessel.usable_fuels:
            add_variable(alg, alg.mass_tank, (v, p, f), "mass_tank")

    shore_power_limits = vessel.expectation.get_shore_power_limit_port(alg.idx)

    for p, limit in enumerate(shore_power_limits):
        if limit > 0.0:
            add_variable(alg, alg.shore_power, (v, p), "shore_power")

        # a connection whose limit fell to zero keeps its variable, bounded at zero
        if (v, p) in alg.shore_power:
            alg.model.set_upper_bound(alg.shore_power[v, p], limit)


def update_regulation_variables(alg: BunkerAlgorithm) -> None:
    """
    Add the remedial factor variables of the regulations that do not exist yet.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    individual = alg.remedial_factor_individual
    flexibility = alg.remedial_factor_flexibility

    for key in alg.regulation_rhs_individual:
        add_variable(alg, individual, key, "remedial_factor_individual")

    for key in alg.regulation_rhs_flexibility:
        add_variable(alg, flexibility, key, "remedial_factor_flexibility")
