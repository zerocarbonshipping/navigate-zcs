# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Add the constraints balancing tank fuel mass from tank stop to tank stop."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.bunker._build import get_constraint

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def update_mass_conservation_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    r"""
    Add the constraints balancing the fuel mass in tanks from tank stop to tank stop.

    The tank legs of a route chain its tank stops 0, ..., N-1 in order. For each
    usable fuel f and tank stop p > 0 (vessel index omitted):

        n m_{p,f} = n m_{p-1,f} + b_{p,f} - \sum_{c} x_{c,f,(p-1,p)}
        - \sum_{c} y_{c,f,p}

    and for the first tank stop n m_{0,f} = b_{0,f} - \sum_{c} y_{c,f,0}, i.e. the
    tank starts and ends the voyage empty. Here m is the fuel mass in tank when
    departing a stop on one voyage, n the number of voyages per year, b the annual
    fuel mass bunkered at the stop, x the annual mass spent by converter c at sea on
    the tank leg into p, and y the annual mass spent by converter c in port. Ties tank
    levels to bunkering and spend so fuel is only spent after it was bunkered
    earlier on the voyage.

    No row debits a leg that is not a tank leg, such as the wrap leg (N-1, 0) back to
    the first tank stop. Summing the rows telescopes to

        n m_{N-1,f} = \sum_{p} b_{p,f} - \sum_{c} \sum_{p} y_{c,f,p}
        - \sum_{c} \sum_{p=1}^{N-1} x_{c,f,(p-1,p)}

    and the bunkered_equals_spent row, which spends over every leg including the
    wrap leg, reduces this to n m_{N-1,f} = \sum_{c} x_{c,f,(N-1,0)}: the tank
    leaves the last tank stop holding exactly the wrap leg's fuel and reaches the
    first tank stop empty.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which constraints are updated.
    """
    v = vessel.name
    route = vessel.route
    ports = route.ports
    voyages = float(vessel.expectation.get_voyages(alg.idx))
    change_coefficient = alg.model.chgCoeff
    mass_tank = alg.mass_tank
    bunker = alg.bunker
    spend_port = alg.spend_port
    spend_sea = alg.spend_sea
    converters_per_fuel = alg.converters_per_fuel
    port_converters_per_fuel = alg.port_converters_per_fuel
    mass_conservation = alg.mass_conservation

    for f in vessel.usable_fuels:
        for p in route.get_tank_stops():
            key = (v, p, f)

            constraint = get_constraint(
                alg, mass_conservation, key, "==", "mass_conservation"
            )

            change_coefficient(constraint, mass_tank[v, p, f], voyages)

            if ports[p].is_bunkering_allowed(f):
                change_coefficient(constraint, bunker[v, p, f], -1.0)

            for c in port_converters_per_fuel[v, f]:
                change_coefficient(constraint, spend_port[v, c, f, p], 1.0)

        # a tank leg carries the tank from its origin's row into its destination's
        for i, e in route.get_tank_legs():
            constraint = mass_conservation[v, e, f]

            for c in converters_per_fuel[v, f]:
                change_coefficient(constraint, spend_sea[v, c, f, i, e], 1.0)

            change_coefficient(constraint, mass_tank[v, i, f], -voyages)
