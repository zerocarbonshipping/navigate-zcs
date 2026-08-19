# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

from navigate.core.enum_ import BunkerScopeID


def transfer_bunker(alg: BunkerAlgorithm) -> None:
    """
    Transfer bunker variable solutions to vessel/port expectations and profiles.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    fleet_demand = {fleet_name: {f: 0. for f in alg.fuels} for fleet_name in alg.fleets}

    # precompute levy levels (independent of vessel/fuel) to avoid redundant getter calls
    levy_level_cache = {}
    if alg.scope == BunkerScopeID.EXISTING:
        for levies in alg.port_levies.values():
            for levy in levies:
                name = levy.get_name()
                if name not in levy_level_cache:
                    levy_level_cache[name] = levy.expectation.get_level(alg.idx)

    # transfer bunker solution
    for (v, p, f), bunker in alg.bunker.items():

        if bunker.X < alg.options.get_solution_tolerance():
            continue

        # extract relevant nodes
        vessel = alg.vessels[v]
        port = vessel.route.ports[p]
        port_name = port.get_name()

        # add the demand to the fleet
        fleet_name = vessel.fleet_assignment
        fleet_demand[fleet_name][f] += bunker.X * alg.multipliers[v]

        # calculate the fuel expenses
        fuel_energy = alg.fuels[f].lower_heating_value.get() * bunker.X

        # transfer bunkered values for
        # future inertia calculations
        vessel.expectation.add_bunker_mass_expected(port_name, f, bunker.X)
        port.expectation.add_bunker_mass_expected(f, bunker.X)

        if alg.scope == BunkerScopeID.EXISTING:

            # calculate fuel expenses
            fuel_expenses = port.expectation.get_bunker_price(f, alg.idx) * bunker.X

            # transfer bunkered values for
            # future inertia calculations
            vessel.expectation.add_bunker_mass_existing(port_name, f, bunker.X)
            port.expectation.add_bunker_mass_existing(f, bunker.X)

            # transfer to vessel profile
            vessel.profile.add_consumed_mass(f, bunker.X, idx=alg.idx)
            vessel.profile.add_converter_mass(vessel.fuel_type, f, bunker.X, idx=alg.idx)
            vessel.profile.add_fuel_expenses(f, fuel_expenses, alg.idx)

            # transfer to port profile
            port.profile.add_bunker_mass(alg.idx, f, alg.multipliers[v] * bunker.X)

        else:

            # calculate fuel expenses
            fuel_expenses = port.expectation.get_bunker_price(f, alg.idx) * bunker.X
            vessel.expectation.add_total_energy(alg.idx,  fuel_energy)
            vessel.expectation.add_fuel_expenses(alg.idx, fuel_expenses)

        # transfer emissions
        for emission_name in alg.emissions:

            if alg.scope == BunkerScopeID.EXISTING:

                EF = port.expectation.get_bunker_WTT(f, emission_name, alg.idx)
                WTT = EF * bunker.X
                vessel.profile.add_WTT(f, emission_name, WTT, idx=alg.idx)

        # transfer levy penalties and subsidies
        for levy in alg.port_levies[port_name]:

            if not levy.vessel_is_policed(v):
                continue

            collected = alg.cost_levy[(v, port_name, f, levy.get_name())] * bunker.X

            if alg.scope == BunkerScopeID.EXISTING:
                levy.profile.add_collected(alg.idx, collected * alg.multipliers[v])
                vessel.profile.add_levy_expenses(f, collected, alg.idx)

                # track per-vessel levy emission units (collected / level)
                level = levy_level_cache[levy.get_name()]
                if level > 0.:
                    vessel.profile.add_levy_units(levy.get_name(), alg.idx, collected / level)

    # transfer the fleet fuel demand
    if alg.scope == BunkerScopeID.EXPECTED:

        for fleet_name, fleet in alg.fleets.items():
            for f, demand in fleet_demand[fleet_name].items():
                fleet.expectation.set_fuel_demand(alg.idx, f, demand)
