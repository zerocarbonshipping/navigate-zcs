# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the shore-power solution to the vessel expectations or results."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID, ExpenseID
from navigate.simulation.bunker._costs import calculate_shore_power_costs

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_shore_power(alg: BunkerAlgorithm) -> None:
    """
    Transfer the shore-power solution to the vessel expectations or results.

    The existing fleet's solution goes to the vessel and levy results, any other
    scope's to the vessel expectations.

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
    """Write the shore-power energy, expenses, emissions and levies to the results."""
    idx = alg.idx

    for (v, p), shore_power in alg.shore_power.items():
        energy = alg.model.value(shore_power)
        if energy < alg.options.solution_tolerance:
            continue

        vessel = alg.vessels[v]
        port = vessel.route.ports[p]
        expectation = port.expectation
        results = vessel.results
        count = alg.counts[v]
        costs = calculate_shore_power_costs(port, v, idx)

        expenses = costs[ExpenseID.SHORE_POWER] * energy
        levy_expenses = costs[ExpenseID.SHORE_POWER_LEVY] * energy

        results.shore_power_energy[idx] += energy
        results.shore_power_expenses[idx] += expenses
        results.shore_power_levy_expenses[idx] += levy_expenses

        for emission_name in alg.emissions:
            wtw = expectation.shore_power_wtt[emission_name][idx]
            results.shore_power_emission[emission_name][idx] += wtw * energy

        for levy in port.imposed_levies:
            levy_cost = levy.expectation.shore_power_cost[v, port.name][idx]
            collected = levy_cost * energy
            rate = levy.expectation.rate[idx]

            levy.results.collected[idx] += collected * count

            if rate > 0.0:
                results.levy_units[levy.name][idx] += collected / rate


def _transfer_expected(alg: BunkerAlgorithm) -> None:
    """Add the shore-power energy and expenses to the expectations."""
    idx = alg.idx

    for (v, p), shore_power in alg.shore_power.items():
        energy = alg.model.value(shore_power)
        if energy < alg.options.solution_tolerance:
            continue

        vessel = alg.vessels[v]
        port = vessel.route.ports[p]
        expectation = vessel.expectation
        costs = calculate_shore_power_costs(port, v, idx)

        expectation.total_energy[idx] += energy

        for expense, cost in costs.items():
            expectation.expenses[expense][idx] += cost * energy
