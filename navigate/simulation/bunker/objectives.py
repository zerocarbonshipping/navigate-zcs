# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Set the objective coefficients of the vessel and regulation LP variables."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID
from navigate.util import TOLERANCE

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm

logger = logging.getLogger(__name__)


def update_vessel_objectives(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Update the objective coefficients of one vessel, and its shore-power bounds.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which objective is updated.
    """
    _update_bunker_objectives(alg, vessel)
    _update_shore_power(alg, vessel)


def _update_bunker_objectives(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """Set each bunker variable's cost: the multiplier times the price plus levies."""
    v = vessel.name
    multiplier = alg.multipliers[v]
    is_existing = alg.scope == BunkerScopeID.EXISTING

    for p, port in enumerate(vessel.route.ports):
        for f, fuel in vessel.usable_fuels.items():
            if not port.bunkering_allowed[f]:
                continue

            price = float(port.expectation.get_bunker_price(f, alg.idx))

            levy_cost = 0.0
            for levy in port.imposed_levies:
                levy_cost += levy.expectation.get_cost((v, port.name, f), alg.idx)

            total_price = price + levy_cost

            alg.model.set_cost(alg.bunker[v, p, f], multiplier * total_price)

            # a zero or negative price on available supply is typically unintended
            if is_existing and total_price <= TOLERANCE:
                supply = port.expectation.get_bunker_supply(f, alg.idx)

                if supply > 0.0:
                    logger.warning(
                        "The bunker price of %s for %s in %s is negative or zero (%s).",
                        fuel,
                        vessel,
                        port,
                        round(total_price, 1),
                    )


def _update_shore_power(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """Set the cost and upper bound of each shore-power variable of the vessel."""
    v = vessel.name
    multiplier = alg.multipliers[v]
    limits = vessel.expectation.get_shore_power_limit_port(alg.idx)

    for p, port in enumerate(vessel.route.ports):
        if (v, p) not in alg.shore_power:
            continue

        shore_power = alg.shore_power[v, p]
        cost = float(port.expectation.get_shore_power_cost(alg.idx))

        alg.model.set_upper_bound(shore_power, float(limits[p]))
        alg.model.set_cost(shore_power, multiplier * cost)


def update_regulation_objectives(alg: BunkerAlgorithm) -> None:
    """
    Update objective coefficients for regulation remedial factors.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    for r, v in alg.regulation_rhs_individual:
        cost = alg.regulations[r].expectation.get_remedial_cost(alg.idx)
        remedial_factor = alg.remedial_factor_individual[r, v]
        alg.model.set_cost(remedial_factor, alg.multipliers[v] * cost)

    for r in alg.regulation_total_rhs_flexibility:
        cost = alg.regulations[r].expectation.get_remedial_cost(alg.idx)
        alg.model.set_cost(alg.remedial_factor_flexibility[r], cost)
