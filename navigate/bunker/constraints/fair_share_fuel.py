# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

import numpy as np

from navigate.bunker.constraints._common import get_constraint


def update_fair_share_fuel_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    r"""
    Add the constraints capping bunkered fuel at each port at the vessel's fair share.

    For each port q and usable fuel f the port may bunker and whose supply is
    finite (vessel index omitted):

        \sum_{p : name(p) = q} b_{p,f} <= A_{q,f}

    where b is the fuel mass bunkered at route stop p and A the vessel's fair-share
    allocation of the port's supply. A constrained port supply is split between the
    competing vessels by the fair-share fixed point (fair_share.py); this caps the
    vessel at its current allocation.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which the constraint is added.
    """

    v = vessel.get_name()
    ports = vessel.route.ports
    change_coefficient = alg.model.chgCoeff

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

            constraint = get_constraint(alg, alg.fair_share_fuel, key, "<=", "fair_share_fuel")
            constraint.rhs = alg.allocation_fuel[key]

            change_coefficient(constraint, alg.bunker[v, p, f], 1.)
