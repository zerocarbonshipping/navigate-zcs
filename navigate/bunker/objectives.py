# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Set the objective coefficients of the vessel and regulation LP variables."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

import navigate.core.enum_ as enum_
from navigate.core.enum_ import BunkerScopeID
from navigate.util import MWD_TO_GJ, TOLERANCE

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

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
    v = vessel.name
    multiplier = alg.multipliers[v]
    ports = vessel.route.ports
    port_levies = alg.port_levies

    for p, port in enumerate(ports):
        port_name = port.name
        levies = port_levies[port_name]

        for f, fuel in vessel.usable_fuels.items():
            if not port.is_bunkering_allowed(f):
                continue

            price = np.float64(port.expectation.get_bunker_price(f, alg.idx))
            cost_levy = sum(
                alg.cost_levy[(v, port_name, f, levy.name)]
                for levy in levies
                if levy.vessel_is_policed(v)
            )
            total_price = price + cost_levy

            alg.bunker[v, p, f].Obj = multiplier * total_price

            # a zero price on available supply is typically unintended
            if (alg.scope == BunkerScopeID.EXISTING) and (total_price <= TOLERANCE):
                supply = port.expectation.get_bunker_supply(f, alg.idx)

                if supply > 0.0:
                    logger.warning(
                        "The bunker price of %s for %s in %s is negative or zero (%s).",
                        fuel,
                        vessel,
                        port,
                        round(total_price, 1),
                    )

    time_port = vessel.expectation.get_time_port(alg.idx)
    vessel_capacity = vessel.expectation.get_shore_power_capacity(alg.idx)
    electrical_demand = vessel.expectation.get_energy_port(idx=alg.idx).get(
        enum_.EnergyDemandTypeID.ELECTRICAL, [0.0] * len(ports)
    )

    for p, port in enumerate(ports):
        key = (v, p)

        if key not in alg.shore_power:
            continue

        cost = float(port.expectation.get_shore_power_cost(alg.idx))
        connection_share = float(
            port.expectation.get_shore_power_connection_share(alg.idx)
        )

        # shore power flows only for the connected share of the time in port, at the
        # lesser of the connection's capacity and the constant load
        capacity_bound = vessel_capacity * float(time_port[p]) * MWD_TO_GJ
        demand_bound = float(electrical_demand[p])
        alg.shore_power[key].UB = connection_share * min(capacity_bound, demand_bound)

        alg.shore_power[key].Obj = multiplier * cost


def update_regulation_objectives(alg: BunkerAlgorithm) -> None:
    """
    Update objective coefficients for regulation remedial factors.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    for r, v in alg.regulation_rhs_individual:
        key = (r, v)
        regulation = alg.regulations[r]
        remedial_cost = regulation.expectation.get_remedial_cost(alg.idx)
        alg.remedial_factor_individual[key].Obj = remedial_cost * alg.multipliers[v]

    for r in alg.regulation_total_rhs_flexibility:
        regulation = alg.regulations[r]
        remedial_cost = regulation.expectation.get_remedial_cost(alg.idx)
        alg.remedial_factor_flexibility[r].Obj = remedial_cost
