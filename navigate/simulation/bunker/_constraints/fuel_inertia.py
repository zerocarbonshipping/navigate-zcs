# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Update the constraints flooring bunkering at the vessel's previous, decayed level."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import BunkerScopeID
from navigate.simulation.bunker._build import get_constraint
from navigate.util import calculate_step_inertia

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def update_fuel_inertia_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    r"""
    Update the constraints that floor bunkering at its previous, decayed level.

    For each port q and usable fuel f the port may bunker (vessel index omitted):

        \sum_{p : name(p) = q} b_{p,f} >= I_{q,f}

    where b is the fuel mass bunkered at route stop p and I the inertia floor: the
    previously bunkered mass decayed by the port's bunkering inertia over the
    time-step, scaled down when the vessel count or energy demand shrank, and capped
    at the fair-share allocation. Models the stickiness of fuel procurement: an
    established offtake winds down at the inertia rate instead of vanishing between
    time-steps.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel whose constraints are updated.
    """
    if alg.idx == 0:
        return

    v = vessel.name

    # a change in the vessel's energy demand since the last time-step scales the
    # floor by the ratio, downwards only: a vessel whose fuel consumption grew
    # need not match its previous bunkering
    demand_new = _calculate_total_demand(vessel, alg.idx)
    demand_old = _calculate_total_demand(vessel, alg.idx - 1)
    energy_scaling = min(demand_new / demand_old, 1.0)

    # the floor is scaled by the change in vessel multipliers, so that only the
    # vessels that actually bunkered previously are affected
    expectation = alg.fleets[vessel.fleet_assignment].expectation
    multiplier_old = float(expectation.get_multiplier(v, alg.scope, alg.idx - 1))
    multiplier_scaling = min(multiplier_old / alg.multipliers[v], 1.0)

    scaling = multiplier_scaling * energy_scaling

    rows = alg.fuel_inertia
    bunker = alg.bunker
    model = alg.model

    for f in vessel.usable_fuels:
        for p, port in enumerate(vessel.route.ports):
            if not port.bunkering_allowed[f]:
                continue

            key = (v, port.name, f)
            bunkered = _get_previous_bunker_mass(alg, vessel, port.name, f)

            # an established offtake winds down at the port's inertia rate, capped
            # at the vessel's fair share where a fair-share constraint applies
            if bunkered > 0.0:
                inertia = port.bunkering_inertia[f].get(alg.time)
                decay = calculate_step_inertia(inertia, alg.time_step)
                cap = alg.allocation_fuel.get(key, np.inf)
                floor = min(bunkered * decay * scaling, cap)
            else:
                floor = 0.0

            constraint = get_constraint(alg, rows, key, ">=", "fuel_inertia")

            model.set_rhs(constraint, floor)
            model.set_coefficient(constraint, bunker[v, p, f], 1.0)


def _get_previous_bunker_mass(
    alg: BunkerAlgorithm, vessel: Vessel, port_name: str, fuel_name: str
) -> float:
    """
    Get the fuel mass the previous time-step bunkered at the port.

    Later expected steps continue from the expected solution; the existing scope and
    the first expected step continue from what the existing solution actually
    bunkered.
    """
    expectation = vessel.expectation

    if alg.scope == BunkerScopeID.EXPECTED and alg.idx > alg.current_idx:
        mass = expectation.get_bunker_mass_expected(port_name, fuel_name, alg.idx - 1)
        return float(mass)

    return expectation.get_bunker_mass_existing(port_name, fuel_name)


def _calculate_total_demand(vessel: Vessel, idx: int) -> np.float64:
    """
    Sum a vessel's energy demand over every leg and port of its route, in GJ/year.

    The sum stays a numpy float, so a ratio over a vessel without demand gives inf or
    nan instead of raising.
    """
    expectation = vessel.expectation

    energy_sea = expectation.get_energy_sea_leg(idx)
    energy_port = expectation.get_energy_port(idx)

    energies = np.concatenate([*energy_sea.values(), *energy_port.values()])

    return np.float64(np.add.reduce(energies))
