# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Set the objective coefficients of the vessel and regulation LP variables."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import BunkerScopeID
from navigate.util import TOLERANCE

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm

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

    for p, port in enumerate(ports):
        port_name = port.name

        for f, fuel in vessel.usable_fuels.items():
            if not port.is_bunkering_allowed(f):
                continue

            price = np.float64(port.expectation.get_bunker_price(f, alg.idx))
            cost_levy = sum(
                alg.cost_levy[(v, port_name, f, levy.name)]
                for levy in port.imposed_levies
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

    shore_power_limits = vessel.expectation.get_shore_power_limit_port(alg.idx)

    for p, port in enumerate(ports):
        key = (v, p)

        if key not in alg.shore_power:
            continue

        cost = float(port.expectation.get_shore_power_cost(alg.idx))

        alg.shore_power[key].UB = float(shore_power_limits[p])
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
