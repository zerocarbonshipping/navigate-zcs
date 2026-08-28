# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

from navigate.core.enum_ import BunkerScopeID


def transfer_spend_port(alg: BunkerAlgorithm) -> None:
    """
    Transfer spend_port solutions to vessel profile.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    if not alg.scope == BunkerScopeID.EXISTING:
        return

    # transfer spend in port solution
    for (v, c, f, _p), spend_port in alg.spend_port.items():

        if spend_port.X < alg.options.solution_tolerance:
            continue

        vessel = alg.vessels[v]

        # transfer spend energy (effective LHV accounts for slip)
        spend_energy = spend_port.X * alg.effective_lhv[(v, c, f)]
        vessel.expectation.add_spend_energy(c, spend_energy)

        # transfer tank-to-wake emissions
        for e in alg.emissions:
            emission_factor = alg.emission_factor[(v, c, f, e)]
            ttw_emissions = emission_factor * spend_port.X
            vessel.profile.add_TTW(f, e, ttw_emissions, idx=alg.idx)
