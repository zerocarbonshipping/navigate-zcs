# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Update the constraints that all fuel bunkered over a vessel's route is spent."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.bunker._build import get_constraint
from navigate.simulation.bunker._indices import get_port_converters

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def update_bunkered_equals_spent_constraints(
    alg: BunkerAlgorithm, vessel: Vessel
) -> None:
    r"""
    Update the constraints that all fuel bunkered over the route is spent.

    For each usable fuel f (vessel index omitted):

        \sum_{p} b_{p,f} = \sum_{c} \sum_{(i,e)} x_{c,f,i,e}
        + \sum_{c} \sum_{p} y_{c,f,p}

    where b is the fuel mass bunkered at port p, x the fuel mass spent by converter c
    at sea on leg (i, e), and y the fuel mass spent by converter c in port. Closes the
    route-wide fuel balance; the mass_conservation constraint at each tank stop of the
    route additionally tracks when along the route fuel is spent.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel whose constraints are updated.
    """
    v = vessel.name
    route = vessel.route

    legs = route.get_legs()
    stops = route.get_stops()
    port_converters = get_port_converters(vessel)

    rows = alg.bunkered_equals_spent
    bunker = alg.bunker
    spend_sea = alg.spend_sea
    spend_port = alg.spend_port
    model = alg.model

    for f, converters in vessel.converters_per_fuel.items():
        converters_in_port = [c for c in converters if c in port_converters]

        key = (v, f)
        constraint = get_constraint(alg, rows, key, "==", "bunkered_equals_spent")

        for p in stops:
            if (v, p, f) in bunker:
                model.set_coefficient(constraint, bunker[v, p, f], 1.0)

        for c in converters:
            for i, e in legs:
                model.set_coefficient(constraint, spend_sea[v, c, f, i, e], -1.0)

        for c in converters_in_port:
            for p in stops:
                model.set_coefficient(constraint, spend_port[v, c, f, p], -1.0)
