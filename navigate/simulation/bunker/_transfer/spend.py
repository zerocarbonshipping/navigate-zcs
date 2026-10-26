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

    for (v, c, f, _port_start, _port_end), variable in alg.spend_sea.items():
        _transfer_spend(alg, v, c, f, alg.model.value(variable))

    for (v, c, f, _p), variable in alg.spend_port.items():
        _transfer_spend(alg, v, c, f, alg.model.value(variable))


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
    for e in alg.emissions:
        ttw_consumption = expectation.get_ttw_consumption(c, f, e)
        ttw_slip = expectation.get_ttw_slip(c, f, e)

        ttw_emissions = (ttw_consumption + ttw_slip) * spend
        vessel.results.ttw[f, e][alg.idx] += ttw_emissions
