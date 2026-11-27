# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the energy prices and demands, and the prices of the shore-power limits."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_dual_solution(alg: BunkerAlgorithm) -> None:
    """
    Transfer the energy prices and demands, and the prices of the shore-power limits.

    The energy price is the dual of the energy-conservation row, as the solve
    selects it among the optimal ones (``_selection``): where no other priced row
    limits it, the saving from a GJ less demand or, where there is no demand, the
    cost of the first GJ. Where the other rows keep a row without demand from its
    first GJ, the price of every row without demand in that solve is an optimal dual
    the solver chose. The objective scales each vessel's terms by its number of
    vessels, so the dual divided by that number is the price per vessel; the
    right-hand side, the energy demand, is already per vessel.

    The price of a shore-power limit is the dual of its row, selected and divided
    likewise: where no other priced row limits it, the change of the cost per GJ the
    limit rises by. It is zero or negative, and zero at a stop where the vessel has
    no such row, as it cannot draw shore power there.

    A vessel type outside the LP gets nothing: its prices at the time step stay NaN
    and its demands zero, as ``reset_expected_bunkering`` left them.

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
        pi = alg.model.dual(constraint) / alg.counts[v]
        rhs = alg.model.rhs(constraint)

        expectation.energy_conservation_pi_sea[demand_type][leg][idx] = pi
        expectation.energy_conservation_rhs_sea[demand_type][leg][idx] = rhs

    for (v, p, demand_type), constraint in alg.energy_conservation_port.items():
        expectation = alg.vessels[v].expectation
        pi = alg.model.dual(constraint) / alg.counts[v]
        rhs = alg.model.rhs(constraint)

        expectation.energy_conservation_pi_port[demand_type][p][idx] = pi
        expectation.energy_conservation_rhs_port[demand_type][p][idx] = rhs

    limits = alg.shore_power_limit

    for v, vessel in alg.vessels.items():
        expectation = vessel.expectation

        for p in vessel.route.get_stops():
            if (v, p) in limits:
                pi = alg.model.dual(limits[v, p]) / alg.counts[v]
            else:
                pi = 0.0
            expectation.shore_power_limit_pi_port[p][idx] = pi
