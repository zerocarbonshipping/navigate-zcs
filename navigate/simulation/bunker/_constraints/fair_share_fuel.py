# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Update the constraints capping a vessel's bunkering at its fair share of supply."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from navigate.simulation.bunker._build import get_constraint

if TYPE_CHECKING:
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def update_fair_share_fuel_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    r"""
    Update the constraints that cap bunkering at each port at the vessel's fair share.

    For each port q and usable fuel f whose supply is fair-share constrained
    (vessel index omitted):

        \sum_{p : name(p) = q} b_{p,f} <= A_{q,f}

    where b is the fuel mass bunkered at route stop p and A the vessel's fair-share
    allocation of the port's supply. A constrained port supply is split between the
    competing vessels by the fair-share fixed point (_fair_share.py); this caps the
    vessel at its current allocation.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel whose constraints are updated.
    """
    v = vessel.name

    rows = alg.fair_share_fuel
    bunker = alg.bunker
    model = alg.model

    for p, port in enumerate(vessel.route.ports):
        for f in vessel.usable_fuels:
            if not is_fair_share_constrained(port, f, alg.idx):
                continue

            key = (v, port.name, f)
            constraint = get_constraint(alg, rows, key, "<=", "fair_share_fuel")

            model.set_rhs(constraint, alg.allocation_fuel[key])
            model.set_coefficient(constraint, bunker[v, p, f], 1.0)


def is_fair_share_constrained(port: Port, fuel_name: str, idx: int) -> bool:
    """
    Check whether a port's supply of a fuel is shared out by fair-share constraints.

    Only a finite supply of a fuel the port may bunker is; an infinite supply was
    never constrained, or its constraint was removed.

    Parameters
    ----------
    port
        Port whose supply is checked.
    fuel_name
        Name of the fuel.
    idx
        Time-step index the supply is read at.

    Returns
    -------
    bool
        True if the port may bunker the fuel and its supply is finite.
    """
    if not port.bunkering_allowed[fuel_name]:
        return False

    supply = float(port.expectation.get_bunker_supply(fuel_name, idx))
    return math.isfinite(supply)
