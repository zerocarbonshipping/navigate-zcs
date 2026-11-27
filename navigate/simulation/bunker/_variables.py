# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Add the vessel and regulation variables of the LP."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.bunker._build import add_variable
from navigate.simulation.bunker._constraints.regulation_threshold_flexibility import (
    is_pooled,
)
from navigate.simulation.bunker._constraints.shore_power_limit import (
    can_draw_shore_power,
)

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def update_vessel_variables(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Add the LP variables of a vessel that do not exist yet.

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

    for p, fuels in enumerate(vessel.bunkerable_fuels):
        for f in fuels:
            add_variable(alg, alg.bunker, (v, p, f), "bunker", route)
            add_variable(alg, alg.bunker_peak, (v, f), "bunker_peak")

    for c, fuels in fuels_per_converter.items():
        for f in fuels:
            for leg in legs:
                add_variable(alg, alg.spend_sea, (v, c, f, *leg), "spend_sea", route)

    # only the converters serving port energy demands spend in port
    for c, fuels in vessel.fuels_per_port_converter.items():
        for f in fuels:
            for p in stops:
                add_variable(alg, alg.spend_port, (v, c, f, p), "spend_port", route)

    for p in route.get_tank_stops():
        for f in vessel.usable_fuels:
            add_variable(alg, alg.mass_tank, (v, p, f), "mass_tank", route)

    for p in stops:
        if can_draw_shore_power(vessel, p, alg.idx):
            add_variable(alg, alg.shore_power, (v, p), "shore_power", route)


def update_regulation_variables(alg: BunkerAlgorithm) -> None:
    """
    Add the regulation variables that do not exist yet.

    A regulation has a remedial factor per policed vessel or per pool. A FLEXIBLE
    one also has the term of each vessel it pools, a free variable, as the term of
    a vessel below an INTENSITY threshold is negative
    (regulation_threshold_flexibility).

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    individual = alg.remedial_factor_individual
    flexibility = alg.remedial_factor_flexibility
    pooled_terms = alg.pooled_term

    for key in alg.regulation_rhs_individual:
        add_variable(alg, individual, key, "remedial_factor_individual")

    for key in alg.regulation_rhs_flexibility:
        add_variable(alg, flexibility, key, "remedial_factor_flexibility")

    for r in alg.regulation_rhs_flexibility:
        for v in alg.vessels:
            if is_pooled(alg, r, v):
                add_variable(alg, pooled_terms, (r, v), "pooled_term", free=True)
