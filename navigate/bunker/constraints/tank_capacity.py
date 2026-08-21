# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

import navigate.bunker.solver as gp


def update_tank_capacity_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Add constraints limiting fuel mass in tank to tank capacity.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which constraints are updated.
    """

    v = vessel.get_name()
    tanks = vessel.tanks

    for p in alg.port_idx[v]:

        for tank in tanks:

            t = tank.get_name()
            key = (v, p, t)

            if key in alg.tank_capacity:

                constraint = alg.tank_capacity[key]

            else:

                name = "tank_capacity_{}_{}_{}".format(*key)
                constraint = alg.model.addConstr(gp.LinExpr() <= 0., name=name)
                alg.tank_capacity[key] = constraint

            # update the rhs of the constraint
            constraint.rhs = tank.size.get()

            for fuel_type in tank.get_fuel_types():

                for fuel in alg.fuels_per_fuel_type[fuel_type]:

                    f = fuel.get_name()

                    if f in alg.usable_fuels[v]:

                        # although the coefficient does not change,
                        # this is necessary to activate later added
                        # bunker fuels which were not available
                        # when the constraint was initialized
                        variable = alg.mass_tank[v, p, f]
                        coefficient = 1. / fuel.mass_density.get()
                        alg.model.chgCoeff(constraint, variable, coefficient)
