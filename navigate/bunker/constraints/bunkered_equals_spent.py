# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

from navigate.bunker._build import get_constraint


def update_bunkered_equals_spent_constraint(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    r"""
    Add the constraints that all fuel bunkered over the route is spent.

    For each usable fuel f (vessel index omitted):

        \sum_{p} b_{p,f} = \sum_{c} \sum_{(i,e)} x_{c,f,i,e} + \sum_{c} \sum_{p} y_{c,f,p}

    where b is the fuel mass bunkered at port p, x the fuel mass spent by converter c
    at sea on leg (i, e), and y the fuel mass spent by converter c in port. Closes the
    route-wide fuel balance; the per-port mass_conservation constraint (ROUND_TRIP
    routes only) additionally tracks when along the route fuel is spent.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which constraints are updated.
    """

    v = vessel.name
    route = vessel.route
    converters_per_fuel = alg.converters_per_fuel
    port_converters_per_fuel = alg.port_converters_per_fuel
    leg_idx = route.get_leg_indices()
    port_idx = range(route.get_number_of_ports())

    change_coefficient = alg.model.chgCoeff

    for f in vessel.usable_fuels:

        key = (v, f)

        constraint = get_constraint(alg, alg.bunker_equals_spent, key, "==", "bunkered_equals_spent")

        for p in port_idx:
            if (v, p, f) in alg.bunker:
                change_coefficient(constraint, alg.bunker[v, p, f], 1.)

        for c in converters_per_fuel[v, f]:
            for port_start, port_end in leg_idx:
                change_coefficient(constraint, alg.spend_sea[v, c, f, port_start, port_end], -1.)

        for c in port_converters_per_fuel[v, f]:
            for p in port_idx:
                change_coefficient(constraint, alg.spend_port[v, c, f, p], -1.)
