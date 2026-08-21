# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

import logging

import navigate.core.enum_ as enum_
from navigate.bunker.helpers import extract_times
from navigate.core.enum_ import BunkerScopeID
from navigate.core.unit import MWD_TO_GJ
from navigate.util import TOLERANCE

logger = logging.getLogger(__name__)


def update_vessel_objectives(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Update objective coefficients for a single vessel.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which objective is updated.
    """

    v = vessel.get_name()
    multiplier = alg.multipliers[v]
    ports = vessel.route.ports
    port_levies = alg.port_levies

    # add bunkering costs
    for p, port in enumerate(ports):

        port_name = port.get_name()
        levies = port_levies[port_name]

        for f, fuel in alg.usable_fuels[v].items():

            if port.is_bunkering_allowed(f):

                price = port.expectation.get_bunker_price(f, alg.idx)

                # calculate the cost across all levies
                cost_levy = sum(alg.cost_levy[(v, port_name, f, levy.get_name())]
                                for levy in levies if levy.vessel_is_policed(v))

                # calculate the total price for fuel and levies
                total_price = price + cost_levy

                # update the objective function coefficient
                # of the specific bunker variable
                obj = multiplier * total_price
                alg.bunker[v, p, f].Obj = obj

                # in case the price is zero and there is
                # available supply, then log a warning
                # as this is typically unintended
                if (alg.scope == BunkerScopeID.EXISTING) and (total_price <= TOLERANCE):

                    supply = port.expectation.get_bunker_supply(f, alg.idx)

                    if supply > 0.:
                        logger.warning("The bunker price of {} for {} in {} is negative or zero ({})."
                                       .format(fuel, vessel, port, round(total_price, 1)))

    # add shore power costs and bounds
    _, time_port = extract_times(vessel, alg.idx)
    vessel_capacity = vessel.expectation.get_shore_power_capacity(alg.idx)

    # electrical demand at each port for share-based upper bound
    demands_port = vessel.expectation.get_energy_port(idx=alg.idx)
    electrical_demand = demands_port.get(enum_.EnergyDemandTypeID.ELECTRICAL, [0.] * len(ports))

    for p, port in enumerate(ports):

        key = (v, p)

        if key not in alg.shore_power:
            continue

        cost = port.expectation.get_shore_power_cost(alg.idx)
        connection_share = port.expectation.get_shore_power_connection_share(alg.idx)

        # upper bound: min of capacity-based limit and share-based demand limit
        capacity_ub = vessel_capacity * time_port[p] * MWD_TO_GJ
        share_ub = connection_share * electrical_demand[p]
        ub = min(capacity_ub, share_ub)
        alg.shore_power[key].UB = float(ub)

        # objective coefficient
        alg.shore_power[key].Obj = multiplier * cost


def update_regulation_objectives(alg: BunkerAlgorithm) -> None:
    """
    Update objective coefficients for regulation remedial factors.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    for (r, v) in alg.regulation_rhs_individual:

        key = (r, v)
        regulation = alg.regulations[r]
        remedial_cost = regulation.expectation.get_remedial_cost(alg.idx)
        alg.remedial_factor_individual[key].Obj = remedial_cost * alg.multipliers[v]

    for r in alg.regulation_total_rhs_flexibility:

        regulation = alg.regulations[r]
        remedial_cost = regulation.expectation.get_remedial_cost(alg.idx)
        alg.remedial_factor_flexibility[r].Obj = remedial_cost
