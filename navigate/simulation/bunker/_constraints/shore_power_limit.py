# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Update the constraints that the shore power drawn at each port fits its limit."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import EnergyDemandID
from navigate.simulation.bunker._build import get_constraint

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def update_shore_power_limit_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    r"""
    Update the constraints that the shore power drawn at each port fits its limit.

    For each port p where the vessel has a shore-power variable (vessel index
    omitted):

        s_p <= L_p

    where s is the shore power in GJ/year and L the most the vessel can take there,
    by the port's availability and the vessel's shore-power capacity, in GJ/year.
    The constraint is priced: its dual, zero or negative, is the change of the cost
    per GJ more of limit, as the solve selects it (dual_solution). A vessel without
    capacity has the constraint too, at a limit of zero, so that the capacity it
    lacks has a price.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel whose constraints are updated.
    """
    v = vessel.name
    route = vessel.route
    limits = vessel.expectation.shore_power_limit_port.at[alg.idx]

    rows = alg.shore_power_limit
    shore_power = alg.shore_power
    model = alg.model

    for p, limit in enumerate(limits):
        key = (v, p)
        if key not in shore_power:
            continue

        constraint = get_constraint(
            alg, rows, key, "<=", "shore_power_limit", route, priced=True
        )
        model.set_rhs(constraint, limit)
        model.set_coefficient(constraint, shore_power[key], 1.0)


def can_draw_shore_power(vessel: Vessel, p: int, idx: int) -> bool:
    """
    Check whether a vessel can draw shore power at a stop of its route.

    It can where the port offers shore power and the vessel has an electrical demand
    there. The vessel's shore-power capacity plays no part: its limit holds the
    vessel to it.

    The port offers shore power where its availability is positive at any time-step,
    not only at the given one. The expected bunkering builds the LP of every step
    ahead, so a port that offers shore power from a later date on would otherwise
    lose and regain its variables at every time-step, and a removed variable stays
    in the model as a dead column. At a step without availability the limit is zero.

    The demand is that of the given step: with no demand to cover, the shore-power
    limit and the energy-conservation row bind only together, and the solver chooses
    which carries the price (_selection, Duals).

    Parameters
    ----------
    vessel
        Vessel calling at the port.
    p
        Stop index of the port on the vessel's route.
    idx
        Time-step index the electrical demand is read at.

    Returns
    -------
    bool
        True if the port's availability is positive at any time-step and the
        vessel's electrical demand at the stop is positive at the given one.
    """
    port = vessel.route.ports[p]
    availability = port.expectation.shore_power_availability
    energy_port = vessel.expectation.energy_port[EnergyDemandID.ELECTRICAL]

    return bool(np.any(availability > 0.0) and energy_port[p][idx] > 0.0)
