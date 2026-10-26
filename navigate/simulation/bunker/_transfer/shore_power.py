# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the shore-power solution to the vessel expectations or results."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_shore_power(alg: BunkerAlgorithm) -> None:
    """
    Transfer the shore-power solution to the vessel expectations or results.

    The existing fleet's solution goes to the vessel results, any other scope's to the
    vessel expectations.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    if alg.scope == BunkerScopeID.EXISTING:
        _transfer_existing(alg)
    else:
        _transfer_expected(alg)


def _transfer_existing(alg: BunkerAlgorithm) -> None:
    """Write the shore-power energy, expenses and WTW emissions to the results."""
    idx = alg.idx

    for (v, p), shore_power in alg.shore_power.items():
        energy = alg.model.value(shore_power)
        if energy < alg.options.solution_tolerance:
            continue

        vessel = alg.vessels[v]
        port = vessel.route.ports[p]
        expectation = port.expectation
        results = vessel.results

        cost = expectation.get_shore_power_cost(idx)
        expenses = cost * energy

        results.shore_power_energy[idx] += energy
        results.shore_power_expenses[idx] += expenses

        for emission_name in alg.emissions:
            wtw = expectation.get_shore_power_emission_factor(emission_name, idx)
            results.shore_power_emission[emission_name][idx] += wtw * energy


def _transfer_expected(alg: BunkerAlgorithm) -> None:
    """Add the shore-power energy and expenses to the vessel expectations."""
    idx = alg.idx

    for (v, p), shore_power in alg.shore_power.items():
        energy = alg.model.value(shore_power)
        if energy < alg.options.solution_tolerance:
            continue

        vessel = alg.vessels[v]
        port = vessel.route.ports[p]

        cost = port.expectation.get_shore_power_cost(idx)
        expenses = cost * energy

        vessel.expectation.add_total_energy(idx, energy)
        vessel.expectation.add_fuel_expenses(idx, expenses)
