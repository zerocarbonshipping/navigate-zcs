# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the energy-conservation shadow prices and demands to the vessels."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_dual_solution(alg: BunkerAlgorithm) -> None:
    """
    Transfer the shadow prices and right-hand sides of the energy-conservation rows.

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
        vessel = alg.vessels[v]
        leg = vessel.route.local_to_global_leg_idx(port_start, port_end)

        # the objective scales the shadow price by the number of vessels, so
        # dividing by it gives the impact per vessel; the rhs is already per vessel
        shadow_price = constr.Pi / alg.multipliers[v]
        rhs = constr.RHS

        vessel.expectation.set_energy_conservation_pi_sea(
            alg.idx, energy_id, leg, shadow_price
        )
        vessel.expectation.set_energy_conservation_rhs_sea(alg.idx, energy_id, leg, rhs)

    for (v, p, energy_id), constr in alg.energy_conservation_port.items():
        # the objective scales the shadow price by the number of vessels, so
        # dividing by it gives the impact per vessel; the rhs is already per vessel
        shadow_price = constr.Pi / alg.multipliers[v]
        rhs = constr.RHS

        vessel = alg.vessels[v]
        vessel.expectation.set_energy_conservation_pi_port(
            alg.idx, energy_id, p, shadow_price
        )
        vessel.expectation.set_energy_conservation_rhs_port(alg.idx, energy_id, p, rhs)
