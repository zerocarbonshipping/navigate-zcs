# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the bunkered fuel mass to the vessel, port and levy results."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID, ExpenseID
from navigate.simulation.bunker._costs import calculate_bunker_costs

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_bunker(alg: BunkerAlgorithm) -> None:
    """
    Transfer the bunker solution to the vessel expectations or results.

    The existing fleet's solution goes to the vessel, port and levy results, any
    other scope's to the vessel expectations.

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
    """Write the bunkered mass, expenses, WTT emissions and levies to the results."""
    idx = alg.idx

    # every fleet vessel restarts its bunker mass from zero, also one out of the LP
    for fleet in alg.fleets.values():
        for vessel in fleet.vessels:
            vessel.expectation.reset_bunker_mass_existing()

    for (v, p, f), bunker in alg.bunker.items():
        mass = alg.model.value(bunker)
        if mass < alg.options.solution_tolerance:
            continue

        vessel = alg.vessels[v]
        port = vessel.route.ports[p]
        results = vessel.results
        count = alg.counts[v]
        costs = calculate_bunker_costs(port, v, f, idx)

        # kept for the inertia floor of the next time-step
        vessel.expectation.bunker_mass_existing[port.name, f] += mass

        results.consumed_mass[f][idx] += mass
        results.converter_mass[vessel.primary_fuel_type][f][idx] += mass
        results.fuel_expenses[f][idx] += costs[ExpenseID.FUEL] * mass
        results.levy_expenses[f][idx] += costs[ExpenseID.FUEL_LEVY] * mass
        port.results.bunker_mass[f][idx] += count * mass

        for emission_name in alg.emissions:
            wtt = port.expectation.bunker_wtt[f, emission_name][idx]
            results.wtt[emission_name][idx] += wtt * mass

        for levy in port.imposed_levies:
            cost = levy.expectation.cost[v, port.name, f][idx]
            collected = cost * mass
            rate = levy.expectation.rate[idx]

            levy.results.collected[idx] += collected * count

            if rate > 0.0:
                results.levy_units[levy.name][idx] += collected / rate


def _transfer_expected(alg: BunkerAlgorithm) -> None:
    """Add the bunkered energy, mass and expenses to the expectations."""
    idx = alg.idx

    for (v, p, f), bunker in alg.bunker.items():
        mass = alg.model.value(bunker)
        if mass < alg.options.solution_tolerance:
            continue

        vessel = alg.vessels[v]
        port = vessel.route.ports[p]
        expectation = vessel.expectation

        energy = alg.fuels[f].lower_heating_value.get() * mass
        costs = calculate_bunker_costs(port, v, f, idx)

        expectation.total_energy[idx] += energy
        expectation.bunker_mass_expected[port.name, f][idx] += mass

        for expense, cost in costs.items():
            expectation.expenses[expense][idx] += cost * mass
