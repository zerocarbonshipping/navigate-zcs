# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Closing the gap between the fleet's trade and the capacity it carries.

Newbuilds fill a shortfall, and secondary scrapping removes a surplus.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.fleet.composition import (
    consolidate_increments,
    get_multipliers,
    get_trade_capacity,
)
from navigate.simulation.fleet.newbuild import (
    add_newbuilds,
    calculate_modelled_newbuilds,
    calculate_orderbook_newbuilds,
    update_current_uptake,
)
from navigate.simulation.fleet.scrapping import perform_secondary_scrapping
from navigate.simulation.fleet.technology_adoption import (
    reconcile_newbuild_technology_caps,
)
from navigate.util import TOLERANCE, YEAR, calculate_inertia

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet

logger = logging.getLogger(__name__)


def close_trade_gap(fleet: Fleet, time_step: float, idx: int) -> None:
    """
    Close the gap between the fleet's trade and the capacity its vessels carry.

    Within each vessel type's newbuild budget, a shortfall is filled by orderbook
    deliveries, then by inertia newbuilds and modelled newbuilds; a surplus is removed
    by secondary scrapping where the fleet allows it. The increments of equal age are
    then merged and the negligible ones dropped, the newbuild technology caps are
    reconciled and the newbuilds added. The newbuilds set the fleet's current uptake,
    and the trade carried goes to the results.

    Parameters
    ----------
    fleet
        Fleet whose trade gap is closed.
    time_step
        Current time-step size, in days.
    idx
        Current time-step index.
    """
    trade = fleet.trade[idx]
    trade_gap = trade - get_trade_capacity(fleet, idx)

    # each vessel type's newbuild budget; the fleet count stands in for yard capacity
    multipliers_total = float(sum(get_multipliers(fleet)))
    limit_share = np.array([fleet.newbuild_limit[v.name].get() for v in fleet.vessels])
    cap_count = limit_share * multipliers_total * (time_step / YEAR)

    newbuilds, delivered_capacity, cap_count = calculate_orderbook_newbuilds(
        fleet, trade_gap, cap_count, idx
    )
    trade_gap -= delivered_capacity

    # inertia decays the current uptake shares before the modelled newbuilds read them
    fleet.current_uptake *= calculate_inertia(fleet.inertia.get(), time_step)

    if trade_gap > TOLERANCE:
        modelled, delivered_capacity = calculate_modelled_newbuilds(
            fleet, trade_gap, cap_count, idx
        )
        newbuilds += modelled
        trade_gap -= delivered_capacity

    elif trade_gap < -TOLERANCE and fleet.allow_secondary_scrapping:
        trade_gap += perform_secondary_scrapping(fleet, trade_gap, idx)

    consolidate_increments(fleet)
    reconcile_newbuild_technology_caps(fleet, newbuilds, time_step, multipliers_total)
    add_newbuilds(fleet, newbuilds, time_step, idx)
    update_current_uptake(fleet, newbuilds, idx)

    carried = trade - trade_gap
    fleet.results.trade[idx] = carried

    if trade > 0.0 and trade_gap > 1e-3 * trade:
        logger.warning(
            "%s: Model was only able to satisfy %s%% of the expected trade.",
            fleet,
            round(carried / trade * 100.0),
        )
