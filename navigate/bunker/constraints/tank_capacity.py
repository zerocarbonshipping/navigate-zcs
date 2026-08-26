# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

from navigate.bunker.constraints._common import get_constraint


def update_tank_capacity_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    r"""
    Add the constraints that the fuel stored in each tank fits its volume.

    For each port p and tank t (vessel index omitted):

        \sum_{f in fuels(t)} m_{p,f} / \rho_f <= size_t

    where m is the fuel mass in tank when departing port p, \rho the fuel mass
    density, and fuels(t) the usable fuels matching the tank's fuel types. A tank
    stores every such fuel, so it is their combined volume that the tank bounds.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which constraints are updated.
    """

    v = vessel.get_name()
    tanks = vessel.tanks
    usable_fuels = vessel.usable_fuels
    change_coefficient = alg.model.chgCoeff

    for p in range(vessel.route.get_number_of_ports()):

        for tank in tanks:

            t = tank.get_name()
            key = (v, p, t)

            constraint = get_constraint(alg, alg.tank_capacity, key, "<=", "tank_capacity")
            constraint.rhs = tank.size.get()

            for fuel_type in tank.get_fuel_types():

                for fuel in alg.fuels_per_fuel_type[fuel_type]:

                    f = fuel.get_name()

                    if f in usable_fuels:
                        change_coefficient(constraint, alg.mass_tank[v, p, f], 1. / fuel.mass_density.get())
