# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

from navigate.bunker.constraints._common import get_constraint


def update_mass_conservation_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    r"""
    Add the constraints balancing the fuel mass in tanks from port to port.

    For each usable fuel f and port p > 0 (vessel index omitted):

        n m_{p,f} = n m_{p-1,f} + b_{p,f} - \sum_{c} x_{c,f,(p-1,p)} - \sum_{c} y_{c,f,p}

    and for the first port n m_{0,f} = b_{0,f} - \sum_{c} y_{c,f,0}, i.e. the round
    trip starts and ends with empty tanks. Here m is the fuel mass in tank when
    departing a port on one voyage, n the number of voyages per year, b the annual
    fuel mass bunkered at the port, x the annual mass spent by converter c at sea on
    the leg into p, and y the annual mass spent by converter c in port. Ties tank
    levels to bunkering and spend so fuel is only spent after it was bunkered
    earlier on the voyage.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which constraints are updated.
    """

    v = vessel.get_name()
    voyages = vessel.expectation.get_voyages(alg.idx)
    chgCoeff = alg.model.chgCoeff
    mass_tank = alg.mass_tank
    bunker = alg.bunker
    spend_port = alg.spend_port
    spend_sea = alg.spend_sea
    converters_per_fuel = alg.converters_per_fuel
    port_converters_per_fuel = alg.port_converters_per_fuel
    mass_conservation = alg.mass_conservation
    ports = vessel.route.ports
    port_idx = range(len(ports))

    for f in vessel.usable_fuels:

        for p in port_idx:

            port = ports[p]
            key = (v, p, f)

            constraint = get_constraint(alg, mass_conservation, key, "==", "mass_conservation")

            chgCoeff(constraint, mass_tank[v, p, f], voyages)

            if port.is_bunkering_allowed(f):
                chgCoeff(constraint, bunker[v, p, f], -1.)

            for c in port_converters_per_fuel[v, f]:
                chgCoeff(constraint, spend_port[v, c, f, p], 1.)

            if p > 0:
                for c in converters_per_fuel[v, f]:
                    chgCoeff(constraint, spend_sea[v, c, f, p - 1, p], 1.)

                chgCoeff(constraint, mass_tank[v, p - 1, f], -voyages)
