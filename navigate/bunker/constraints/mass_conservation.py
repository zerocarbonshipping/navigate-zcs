# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

import navigate.bunker.solver as gp
from navigate.bunker.utils import get_converter_fuels, get_converters, get_port_converters


def update_mass_conservation_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Add constraints related to mass conservation in fuel tanks.

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
    converters_v = get_converters(vessel)
    port_converters_v = get_port_converters(vessel)
    converter_fuels_v = get_converter_fuels(vessel)
    mass_conservation = alg.mass_conservation
    ports = vessel.route.ports
    port_idx = range(len(ports))

    for f in vessel.usable_fuels:

        for p in port_idx:

            port = ports[p]
            key = (v, p, f)

            if key in mass_conservation:
                constraint = mass_conservation[key]
            else:
                name = "mass_conservation_{}_{}_{}".format(*key)
                constraint = alg.model.addConstr(gp.LinExpr() == 0., name=name)
                mass_conservation[key] = constraint

            chgCoeff(constraint, mass_tank[v, p, f], voyages)

            if port.is_bunkering_allowed(f):
                chgCoeff(constraint, bunker[v, p, f], -1.)

            for c in port_converters_v:
                if f in converter_fuels_v[c]:
                    chgCoeff(constraint, spend_port[v, c, f, p], 1.)

            if p > 0:
                for c in converters_v:
                    if f in converter_fuels_v[c]:
                        chgCoeff(constraint, spend_sea[v, c, f, p - 1, p], 1.)

                chgCoeff(constraint, mass_tank[v, p - 1, f], -voyages)
