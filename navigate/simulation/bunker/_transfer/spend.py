# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the fuel spend at sea and in port to the vessel results."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_spend(alg: BunkerAlgorithm) -> None:
    """
    Transfer the fuel spend solution to the vessel expectations and results.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    if alg.scope != BunkerScopeID.EXISTING:
        return

    # every vessel's spent energy restarts, as a vessel out of the LP spends none
    for fleet in alg.fleets.values():
        for vessel in fleet.vessels:
            vessel.expectation.reset_spend_energy()

    for (v, c, f, _, _), spend_sea in alg.spend_sea.items():
        _transfer_spend(alg, v, c, f, alg.model.value(spend_sea))

    for (v, c, f, _), spend_port in alg.spend_port.items():
        _transfer_spend(alg, v, c, f, alg.model.value(spend_port))


def _transfer_spend(alg: BunkerAlgorithm, v: str, c: str, f: str, spend: float) -> None:
    """Transfer one spend entry to the vessel expectation and results."""
    if spend < alg.options.solution_tolerance:
        return

    vessel = alg.vessels[v]
    expectation = vessel.expectation

    # the effective LHV accounts for slip
    spend_energy = spend * expectation.get_effective_lhv(c, f)
    expectation.add_spend_energy(c, spend_energy)

    # the recorded emissions always count the slip, whatever a policy counts
    for emission_name in alg.emissions:
        ttw_consumption = expectation.get_ttw_consumption(c, f, emission_name)
        ttw_slip = expectation.get_ttw_slip(c, f, emission_name)

        ttw_emissions = (ttw_consumption + ttw_slip) * spend
        vessel.results.ttw[f, emission_name][alg.idx] += ttw_emissions
