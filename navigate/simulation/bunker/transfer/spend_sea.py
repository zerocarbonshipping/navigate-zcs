# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the at-sea fuel spend to the vessel results."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_spend_sea(alg: BunkerAlgorithm) -> None:
    """
    Transfer the at-sea fuel spend solution to the vessel expectations and profiles.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    if alg.scope != BunkerScopeID.EXISTING:
        return

    for (v, c, f, _port_start, _port_end), spend_sea in alg.spend_sea.items():
        if alg.options.solution_tolerance > spend_sea.X:
            continue

        vessel = alg.vessels[v]

        # the effective LHV accounts for slip
        spend_energy = spend_sea.X * alg.effective_lhv[(v, c, f)]
        vessel.expectation.add_spend_energy(c, spend_energy)

        for e in alg.emissions:
            emission_factor = alg.emission_factor[(v, c, f, e)]
            ttw_emissions = emission_factor * spend_sea.X
            vessel.profile.add_ttw(f, e, ttw_emissions, idx=alg.idx)
