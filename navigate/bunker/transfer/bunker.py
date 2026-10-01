# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the bunkered fuel mass to the vessel, port, levy and fleet results."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import BunkerScopeID

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_bunker(alg: BunkerAlgorithm) -> None:
    """
    Transfer the bunker solution to the vessel, port, levy and fleet results.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    fleet_demand = {
        fleet_name: dict.fromkeys(alg.fuels, 0.0) for fleet_name in alg.fleets
    }

    # the levy levels depend on neither vessel nor fuel, so each is read once
    levy_level_cache = {}
    if alg.scope == BunkerScopeID.EXISTING:
        for levies in alg.port_levies.values():
            for levy in levies:
                name = levy.name
                if name not in levy_level_cache:
                    levy_level_cache[name] = levy.expectation.get_level(alg.idx)

    for (v, p, f), bunker in alg.bunker.items():
        if alg.options.solution_tolerance > bunker.X:
            continue

        vessel = alg.vessels[v]
        port = vessel.route.ports[p]
        port_name = port.name

        fleet_name = vessel.fleet_assignment
        fleet_demand[fleet_name][f] += bunker.X * alg.multipliers[v]

        fuel_energy = alg.fuels[f].lower_heating_value.get() * bunker.X
        price = np.float64(port.expectation.get_bunker_price(f, alg.idx))

        # kept for the inertia floor of the next time-step
        vessel.expectation.add_bunker_mass_expected(port_name, f, bunker.X)

        if alg.scope == BunkerScopeID.EXISTING:
            fuel_expenses = price * bunker.X

            # kept for the inertia floor of the next time-step
            vessel.expectation.add_bunker_mass_existing(port_name, f, bunker.X)

            vessel.profile.add_consumed_mass(f, bunker.X, idx=alg.idx)
            vessel.profile.add_converter_mass(
                vessel.primary_fuel_type, f, bunker.X, idx=alg.idx
            )
            vessel.profile.add_fuel_expenses(f, fuel_expenses, alg.idx)
            port.profile.add_bunker_mass(f, alg.multipliers[v] * bunker.X, alg.idx)

        else:
            fuel_expenses = price * bunker.X
            vessel.expectation.add_total_energy(alg.idx, fuel_energy)
            vessel.expectation.add_fuel_expenses(alg.idx, fuel_expenses)

        for emission_name in alg.emissions:
            if alg.scope == BunkerScopeID.EXISTING:
                emission_factor = np.float64(
                    port.expectation.get_bunker_wtt(f, emission_name, alg.idx)
                )
                wtt_emissions = emission_factor * bunker.X
                vessel.profile.add_wtt(f, emission_name, wtt_emissions, idx=alg.idx)

        for levy in alg.port_levies[port_name]:
            if not levy.vessel_is_policed(v):
                continue

            collected = alg.cost_levy[(v, port_name, f, levy.name)] * bunker.X

            if alg.scope == BunkerScopeID.EXISTING:
                levy.profile.add_collected(collected * alg.multipliers[v], alg.idx)
                vessel.profile.add_levy_expenses(f, collected, alg.idx)

                level = levy_level_cache[levy.name]
                if level > 0.0:
                    vessel.profile.add_levy_units(levy.name, collected / level, alg.idx)

    if alg.scope == BunkerScopeID.EXPECTED:
        for fleet_name, fleet in alg.fleets.items():
            for f, demand in fleet_demand[fleet_name].items():
                fleet.expectation.set_fuel_demand(alg.idx, f, demand)
