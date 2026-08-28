# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

from navigate.core.enum_ import BunkerScopeID


def transfer_shore_power(alg: BunkerAlgorithm) -> None:
    """
    Transfer shore power solutions to vessel/port expectations.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    tol = alg.options.solution_tolerance

    for (v, p), shore_power_variable in alg.shore_power.items():

        if shore_power_variable.X < tol:
            continue

        vessel = alg.vessels[v]
        port = vessel.route.ports[p]
        shore_energy_gj = shore_power_variable.X

        # cost
        cost = port.expectation.get_shore_power_cost(alg.idx)
        shore_cost = cost * shore_energy_gj

        if alg.scope == BunkerScopeID.EXISTING:

            # transfer to vessel profile
            vessel.profile.add_shore_power_energy(alg.idx, shore_energy_gj)
            vessel.profile.add_shore_power_expenses(alg.idx, shore_cost)

            # WTW emissions
            for e in alg.emissions:
                emission_factor = port.expectation.get_shore_power_emission_factor(e, alg.idx)
                emission_mass = emission_factor * shore_energy_gj
                vessel.profile.add_shore_power_emission(e, alg.idx, emission_mass)

        else:

            vessel.expectation.add_total_energy(alg.idx, shore_energy_gj)
            vessel.expectation.add_fuel_expenses(alg.idx, shore_cost)
