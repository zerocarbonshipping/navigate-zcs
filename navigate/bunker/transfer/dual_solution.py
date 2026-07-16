# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

logger = logging.getLogger(__name__)


def transfer_dual_solution(alg: BunkerAlgorithm) -> None:
    """
    Transfer shadow prices and RHS values from energy conservation constraints.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    # only compute ranging for debug logging (expensive)
    # SARHSLow/SARHSUp are used in heuristic.py
    transfer_ranging = logger.getEffectiveLevel() <= logging.DEBUG

    for (v, p1, p2, energy_id), constr in alg.energy_conservation_sea.items():

        # convert a local leg-port pair index to the global leg idx
        vessel = alg.vessels[v]
        leg = vessel.route.local_to_global_leg_idx(p1, p2)

        # the shadow price has been scaled with the number of vessels
        # in the objective function, so in order to get the impact
        # per vessel, it needs to be divided by the number of vessels
        pi = constr.Pi / alg.multipliers[v]

        # the energy requirement (rhs) and energy polytope in
        # which the shadow price is valid is given per vessel
        rhs = constr.RHS

        vessel.expectation.set_energy_conservation_pi_sea(alg.idx, energy_id, leg, pi)
        vessel.expectation.set_energy_conservation_rhs_sea(alg.idx, energy_id, leg, rhs)

        if transfer_ranging:
            vessel.expectation.set_energy_conservation_sarhslow_sea(alg.idx, energy_id, leg, constr.SARHSLow)
            vessel.expectation.set_energy_conservation_sarhsup_sea(alg.idx, energy_id, leg, constr.SARHSUp)

    for (v, p, energy_id), constr in alg.energy_conservation_port.items():

        # the shadow price has been scaled with the number of vessels
        # in the objective function, so in order to get the impact
        # per vessel, it needs to be divided by the number of vessels
        pi = constr.Pi / alg.multipliers[v]

        # the energy requirement (rhs) and energy polytope in
        # which the shadow price is valid is given per vessel
        rhs = constr.RHS

        vessel = alg.vessels[v]
        vessel.expectation.set_energy_conservation_pi_port(alg.idx, energy_id, p, pi)
        vessel.expectation.set_energy_conservation_rhs_port(alg.idx, energy_id, p, rhs)

        if transfer_ranging:
            vessel.expectation.set_energy_conservation_sarhslow_port(alg.idx, energy_id, p, constr.SARHSLow)
            vessel.expectation.set_energy_conservation_sarhsup_port(alg.idx, energy_id, p, constr.SARHSUp)
