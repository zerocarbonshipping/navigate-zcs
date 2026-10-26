# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the energy-conservation shadow prices and demands to the vessels."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_dual_solution(alg: BunkerAlgorithm) -> None:
    """
    Transfer the shadow prices and right-hand sides of the energy-conservation rows.

    The objective scales each vessel's terms by its number of vessels, so the shadow
    price divided by that number is the price per vessel; the right-hand side is
    already per vessel.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    if alg.scope != BunkerScopeID.EXPECTED:
        return

    idx = alg.idx

    # the sea rows are keyed by a leg's stops, the expectation by its route position
    leg_positions: dict[str, dict[tuple[int, int], int]] = {}

    for v, vessel in alg.vessels.items():
        legs = vessel.route.get_legs()
        leg_positions[v] = {(i, e): leg for leg, (i, e) in enumerate(legs)}

    for (v, i, e, demand_type), constraint in alg.energy_conservation_sea.items():
        expectation = alg.vessels[v].expectation
        leg = leg_positions[v][i, e]
        pi = alg.model.dual(constraint) / alg.multipliers[v]
        rhs = alg.model.rhs(constraint)

        expectation.set_energy_conservation_pi_sea(idx, demand_type, leg, pi)
        expectation.set_energy_conservation_rhs_sea(idx, demand_type, leg, rhs)

    for (v, p, demand_type), constraint in alg.energy_conservation_port.items():
        expectation = alg.vessels[v].expectation
        pi = alg.model.dual(constraint) / alg.multipliers[v]
        rhs = alg.model.rhs(constraint)

        expectation.set_energy_conservation_pi_port(idx, demand_type, p, pi)
        expectation.set_energy_conservation_rhs_port(idx, demand_type, p, rhs)
