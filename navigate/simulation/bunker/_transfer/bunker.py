# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the bunkered fuel mass to the vessel, port and levy results."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID

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

    # every vessel in the LP restarts its bunker mass from zero, as it is added up below
    for vessel in alg.vessels.values():
        vessel.expectation.reset_bunker_mass_existing()

    for (v, p, f), bunker in alg.bunker.items():
        mass = alg.model.value(bunker)
        if mass < alg.options.solution_tolerance:
            continue

        vessel = alg.vessels[v]
        port = vessel.route.ports[p]
        results = vessel.results
        multiplier = alg.multipliers[v]

        price = float(port.expectation.get_bunker_price(f, idx))
        expenses = price * mass

        # kept for the inertia floor of the next time-step
        vessel.expectation.add_bunker_mass_existing(port.name, f, mass)

        results.consumed_mass[f][idx] += mass
        results.converter_mass[vessel.primary_fuel_type][f][idx] += mass
        results.fuel_expenses[f][idx] += expenses
        port.results.bunker_mass[f][idx] += multiplier * mass

        for emission_name in alg.emissions:
            wtt = float(port.expectation.get_bunker_wtt(f, emission_name, idx))
            results.wtt[f, emission_name][idx] += wtt * mass

        for levy in port.imposed_levies:
            cost = levy.expectation.get_cost((v, port.name, f), idx)
            collected = cost * mass
            level = levy.expectation.get_level(idx)

            levy.results.collected[idx] += collected * multiplier
            results.levy_expenses[f][idx] += collected

            if level > 0.0:
                results.levy_units[levy.name][idx] += collected / level


def _transfer_expected(alg: BunkerAlgorithm) -> None:
    """Add the bunkered energy, expenses and mass to the vessel expectations."""
    idx = alg.idx

    for (v, p, f), bunker in alg.bunker.items():
        mass = alg.model.value(bunker)
        if mass < alg.options.solution_tolerance:
            continue

        vessel = alg.vessels[v]
        port = vessel.route.ports[p]

        energy = alg.fuels[f].lower_heating_value.get() * mass
        price = float(port.expectation.get_bunker_price(f, idx))
        expenses = price * mass

        vessel.expectation.add_total_energy(idx, energy)
        vessel.expectation.add_fuel_expenses(idx, expenses)
        vessel.expectation.add_bunker_mass_expected(idx, port.name, f, mass)
