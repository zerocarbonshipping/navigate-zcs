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
    # the sea rows are keyed by each leg's stops, the expectation lists the legs in
    # the order of their route
    leg_positions = {
        v: {leg: position for position, leg in enumerate(vessel.route.get_legs())}
        for v, vessel in alg.vessels.items()
    }

    for (v, i, e, energy_id), constr in alg.energy_conservation_sea.items():
        vessel = alg.vessels[v]
        position = leg_positions[v][i, e]

        # the objective scales the shadow price by the number of vessels, so
        # dividing by it gives the impact per vessel; the rhs is already per vessel
        shadow_price = constr.Pi / alg.multipliers[v]
        rhs = constr.RHS

        vessel.expectation.set_energy_conservation_pi_sea(
            alg.idx, energy_id, position, shadow_price
        )
        vessel.expectation.set_energy_conservation_rhs_sea(
            alg.idx, energy_id, position, rhs
        )

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
