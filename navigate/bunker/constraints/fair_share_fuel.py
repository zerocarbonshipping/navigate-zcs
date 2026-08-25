# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

import numpy as np

import navigate.bunker.solver as gp


def update_fair_share_fuel_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Add constraints limiting bunkered fuel at each port to its fair-share allocation.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which the constraint is added.
    """

    v = vessel.get_name()
    ports = vessel.route.ports

    for p, port in enumerate(ports):

        port_name = port.get_name()

        for f in vessel.usable_fuels:

            if not port.is_bunkering_allowed(f):
                continue

            supply = port.expectation.get_bunker_supply(f, alg.idx)

            # the fuel is either not initially constrained
            # or the constraint has been removed
            if not np.isfinite(supply):
                continue

            key = (v, port_name, f)

            if key in alg.fair_share_fuel:

                constraint = alg.fair_share_fuel[key]

            else:

                # add the constraint which will be modified below
                name = "fair_share_fuel_{}_{}_{}".format(v, port_name, f)
                constraint = alg.model.addConstr(gp.LinExpr() <= 0., name=name)
                alg.fair_share_fuel[key] = constraint

            # update the rhs of the constraint
            constraint.rhs = alg.allocation_fuel[key]

            # although the coefficients do not change in time
            # it is possible that the same port (with different
            # index) is encountered twice in one loop for
            # ROUND_TRIP routes. This is okay as it simply
            # switches an additional bunker variable on.
            variable = alg.bunker[v, p, f]
            coefficient = 1.
            alg.model.chgCoeff(constraint, variable, coefficient)
