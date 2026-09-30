# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_dual_solution(alg: BunkerAlgorithm) -> None:
    """
    Transfer shadow prices and RHS values from energy conservation constraints.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    for (
        v,
        port_start,
        port_end,
        energy_id,
    ), constr in alg.energy_conservation_sea.items():
        # convert a local leg-port pair index to the global leg idx
        vessel = alg.vessels[v]
        leg = vessel.route.local_to_global_leg_idx(port_start, port_end)

        # the shadow price has been scaled with the number of vessels
        # in the objective function, so in order to get the impact
        # per vessel, it needs to be divided by the number of vessels
        shadow_price = constr.Pi / alg.multipliers[v]

        # the energy requirement (rhs) is given per vessel
        rhs = constr.RHS

        vessel.expectation.set_energy_conservation_pi_sea(
            alg.idx, energy_id, leg, shadow_price
        )
        vessel.expectation.set_energy_conservation_rhs_sea(alg.idx, energy_id, leg, rhs)

    for (v, p, energy_id), constr in alg.energy_conservation_port.items():
        # the shadow price has been scaled with the number of vessels
        # in the objective function, so in order to get the impact
        # per vessel, it needs to be divided by the number of vessels
        shadow_price = constr.Pi / alg.multipliers[v]

        # the energy requirement (rhs) is given per vessel
        rhs = constr.RHS

        vessel = alg.vessels[v]
        vessel.expectation.set_energy_conservation_pi_port(
            alg.idx, energy_id, p, shadow_price
        )
        vessel.expectation.set_energy_conservation_rhs_port(alg.idx, energy_id, p, rhs)
