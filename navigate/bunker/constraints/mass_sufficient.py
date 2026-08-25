# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

import navigate.bunker.solver as gp
from navigate.bunker.utils import get_converter_fuels, get_converters


def update_mass_sufficient_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Add constraints ensuring sufficient fuel mass in tank for each leg.

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
    spend_sea = alg.spend_sea
    converters_v = get_converters(vessel)
    converter_fuels_v = get_converter_fuels(vessel)
    mass_sufficient = alg.mass_sufficient
    leg_idx = vessel.route.get_leg_indices()

    for f in vessel.usable_fuels:

        for (pi, pe) in leg_idx:

            key = (v, pi, f)

            if key in mass_sufficient:
                constraint = mass_sufficient[key]
            else:
                name = "mass_sufficient_{}_{}_{}".format(*key)
                constraint = alg.model.addConstr(gp.LinExpr() >= 0., name=name)
                mass_sufficient[key] = constraint

            chgCoeff(constraint, mass_tank[v, pi, f], voyages)

            for c in converters_v:
                if f in converter_fuels_v[c]:
                    chgCoeff(constraint, spend_sea[v, c, f, pi, pe], -1.)
