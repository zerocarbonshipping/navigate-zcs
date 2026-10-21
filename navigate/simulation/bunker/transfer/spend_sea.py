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
    Transfer the at-sea fuel spend solution to the vessel expectations and results.

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
        expectation = vessel.expectation

        # the effective LHV accounts for slip
        spend_energy = spend_sea.X * expectation.get_effective_lhv(c, f)
        expectation.add_spend_energy(c, spend_energy)

        # the recorded emissions always count the slip, whatever a policy counts
        for e in alg.emissions:
            ttw_consumption = expectation.get_ttw_consumption(c, f, e)
            ttw_slip = expectation.get_ttw_slip(c, f, e)

            ttw_emissions = (ttw_consumption + ttw_slip) * spend_sea.X
            vessel.results.ttw[f, e][alg.idx] += ttw_emissions
