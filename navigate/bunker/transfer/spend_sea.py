# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

from navigate.core.enum_ import BunkerScopeID


def transfer_spend_sea(alg: BunkerAlgorithm) -> None:
    """
    Transfer spend_sea solutions to vessel profile.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    if not alg.scope == BunkerScopeID.EXISTING:
        return

    # transfer spend at sea solution
    for (v, c, f, _port_start, _port_end), spend_sea in alg.spend_sea.items():

        if spend_sea.X < alg.options.get_solution_tolerance():
            continue

        vessel = alg.vessels[v]

        # transfer spend energy (effective LHV accounts for slip)
        spend_energy = spend_sea.X * alg.effective_lhv[(v, c, f)]
        vessel.expectation.add_spend_energy(c, spend_energy)

        # transfer emissions
        for e in alg.emissions:
            emission_factor = alg.emission_factor[(v, c, f, e)]
            ttw_emissions = emission_factor * spend_sea.X
            vessel.profile.add_TTW(f, e, ttw_emissions, idx=alg.idx)
