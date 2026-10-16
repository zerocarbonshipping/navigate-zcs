# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the bunkered fuel mass to the vessel, port and levy results."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import BunkerScopeID

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_bunker(alg: BunkerAlgorithm) -> None:
    """
    Transfer the bunker solution to the vessel, port and levy results.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    for (v, p, f), bunker in alg.bunker.items():
        if alg.options.solution_tolerance > bunker.X:
            continue

        vessel = alg.vessels[v]
        port = vessel.route.ports[p]
        port_name = port.name

        fuel_energy = alg.fuels[f].lower_heating_value.get() * bunker.X
        price = np.float64(port.expectation.get_bunker_price(f, alg.idx))

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
            vessel.expectation.add_bunker_mass_expected(alg.idx, port_name, f, bunker.X)

        for emission_name in alg.emissions:
            if alg.scope == BunkerScopeID.EXISTING:
                emission_factor = np.float64(
                    port.expectation.get_bunker_wtt(f, emission_name, alg.idx)
                )
                wtt_emissions = emission_factor * bunker.X
                vessel.profile.add_wtt(f, emission_name, wtt_emissions, idx=alg.idx)

        for levy in port.imposed_levies:
            cost = levy.expectation.get_cost((v, port_name, f), alg.idx)
            collected = cost * bunker.X

            if alg.scope == BunkerScopeID.EXISTING:
                levy.profile.add_collected(collected * alg.multipliers[v], alg.idx)
                vessel.profile.add_levy_expenses(f, collected, alg.idx)

                level = float(levy.expectation.get_level(alg.idx))
                if level > 0.0:
                    vessel.profile.add_levy_units(levy.name, collected / level, alg.idx)
