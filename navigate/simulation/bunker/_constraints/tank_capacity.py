# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Update the constraints that the fuel stored in each tank fits its volume."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.bunker._build import get_constraint

if TYPE_CHECKING:
    from navigate.core.nodes.tank import Tank
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def update_tank_capacity_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    r"""
    Update the constraints that the fuel stored in each tank fits its volume.

    For each tank stop p and tank t (vessel index omitted):

        \sum_{f in fuels(t)} m_{p,f} / \rho_f <= size_t

    where m is the fuel mass in tank when departing stop p, \rho the fuel mass
    density, and fuels(t) the usable fuels matching the tank's fuel types. A tank
    stores every such fuel, so it is their combined volume that the tank bounds.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel whose constraints are updated.
    """
    v = vessel.name
    tanks = vessel.tanks
    stops = vessel.route.get_tank_stops()

    volume_per_ton = {tank.name: _calculate_volume_per_ton(alg, tank) for tank in tanks}

    rows = alg.tank_capacity
    mass_tank = alg.mass_tank
    model = alg.model

    for p in stops:
        for tank in tanks:
            t = tank.name
            key = (v, p, t)
            constraint = get_constraint(alg, rows, key, "<=", "tank_capacity")
            model.set_rhs(constraint, tank.size.get())

            for f, coefficient in volume_per_ton[t].items():
                model.set_coefficient(constraint, mass_tank[v, p, f], coefficient)


def _calculate_volume_per_ton(alg: BunkerAlgorithm, tank: Tank) -> dict[str, float]:
    """
    Calculate the volume a ton of each fuel the tank stores takes up.

    Parameters
    ----------
    alg
        The algorithm instance.
    tank
        Tank whose fuels are converted.

    Returns
    -------
    dict[str, float]
        Inverse mass density per fuel name, in m3/t.
    """
    volume_per_ton: dict[str, float] = {}

    for fuel_type in tank.get_fuel_types():
        for fuel in alg.fuels_per_fuel_type[fuel_type]:
            volume_per_ton[fuel.name] = 1.0 / fuel.mass_density.get()

    return volume_per_ton
