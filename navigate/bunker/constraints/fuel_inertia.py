# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

from navigate.bunker._build import get_constraint
from navigate.core.enum_ import BunkerScopeID
from navigate.util import calculate_inertia


def update_fuel_inertia_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    r"""
    Add the constraints enforcing a floor on bunkered fuel carried over from the previous time-step.

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
        Vessel for which constraints are updated.
    """

    if alg.idx == 0:
        return

    v = vessel.name
    route = vessel.route
    ports = route.ports

    # in case the energy demand of the vessel has been changed since the
    # last time-step, the coefficient is scaled by the ratio. Demand can
    # only be scaled downwards as a vessels increased fuel consumption
    # does not have to match previous bunkering.
    demand_new = alg.vessels[v].expectation.get_total_demand(alg.idx)
    demand_old = alg.vessels[v].expectation.get_total_demand(alg.idx - 1)
    energy_scaling = min(demand_new / demand_old, 1.)

    # scale the inertia by the change in vessel
    # multipliers to mimic that only vessels
    # that actually previously bunkered are affected.
    fleet = alg.fleets[vessel.fleet_assignment]

    if alg.scope == BunkerScopeID.EXISTING:
        previous_multiplier = fleet.expectation.get_existing_multipliers(v, alg.idx - 1)
    else:
        previous_multiplier = fleet.expectation.get_expected_multipliers(v, alg.idx - 1)

    multiplier_scaling = min(previous_multiplier / alg.multipliers[v], 1.)
    change_coefficient = alg.model.chgCoeff

    for f in vessel.usable_fuels:

        for p, port in enumerate(ports):

            if not port.is_bunkering_allowed(f):
                continue

            port_name = port.name
            key = (v, port_name, f)

            constraint = get_constraint(alg, alg.fuel_inertia, key, ">=", "fuel_inertia")

            change_coefficient(constraint, alg.bunker[v, p, f], 1.)

            # update the rhs of the constraint with
            # the newest inertia and bunker value.
            # notice that the initial inertia in
            # expected bunkering uses the value that
            # was previously bunkered in the actual
            # solution
            if alg.scope == BunkerScopeID.EXPECTED and alg.idx > alg.current_idx:
                bunkering = vessel.expectation.get_bunker_mass_expected(port_name, f)
            else:
                bunkering = vessel.expectation.get_bunker_mass_existing(port_name, f)

            if bunkering > 0.:

                inertia = port.get_bunkering_inertia(f).get(alg.time)
                fuel_inertia = bunkering * calculate_inertia(inertia, alg.time_step)
                fuel_inertia *= multiplier_scaling * energy_scaling

                # if fair-share is included in the
                # model, the minimum required can at
                # most equal the vessels fair-share
                if key in alg.allocation_fuel:

                    if fuel_inertia > alg.allocation_fuel[key]:
                        fuel_inertia = alg.allocation_fuel[key]

            else:
                fuel_inertia = 0.

            constraint.rhs = fuel_inertia
