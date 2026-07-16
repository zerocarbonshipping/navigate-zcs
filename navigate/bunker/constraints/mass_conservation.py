# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.vessel import Vessel

import navigate.bunker.solver as gp


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
    converters_v = alg.converters[v]
    port_converters_v = alg.port_converters[v]
    converter_fuels_v = alg.converter_fuels[v]
    mass_conservation = alg.mass_conservation
    ports = alg.vessels[v].route.ports

    for f in alg.usable_fuels[v]:

        for p in alg.port_idx[v]:

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
