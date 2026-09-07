# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import UtilityID
from navigate.core.increment import Increment
from navigate.fleet.technology_adoption import calculate_package_charter_rates
from navigate.fleet.utils import calculate_increments, extract_cargo_miles
from navigate.util import TOLERANCE, YEAR, to_numpy

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel

logger = logging.getLogger(__name__)


def calculate_orderbook_newbuilds(fleet: Fleet, trade_gap: float, cap_count: np.ndarray, idx: int):
    """
    Calculate the number of vessels for each vessel type that will enter the fleet based on the orderbook.

    Vessels are deferred (kept in `orders_postponed`) when either the trade gap is smaller than the
    orderbook demands, or when delivery would exceed the per-vessel newbuild-count budget `cap_count`.

    Parameters
    ----------
    fleet
        The fleet instance.
    trade_gap
        The trade-gap of the fleet, in cargo-miles.
    cap_count
        Per-vessel newbuild count budget for this timestep
        (fraction of pre-newbuild fleet × time_step/YEAR).
    idx
        Current time-step index.

    Returns
    -------
    A vector of newbuild increments, the delivered capacity, and the cap_count reduced by what was delivered.
    """

    # pre-allocate delivered newbuilds
    nv = len(fleet.assets)
    delivery = np.zeros((nv,))

    if not fleet.orderbooks:
        return delivery, 0., cap_count

    # extract whether the vessel type is allowed
    # and trade delivered by the vessel type
    allowed = np.array([(fleet.allow_vessel[vessel.name] and fleet.newbuild_available[vessel.name])
                        for vessel in fleet.assets])

    cargo_miles = np.array(extract_cargo_miles(fleet.assets, idx=idx))

    # first deliver orders which were postponed
    postponed_before = fleet.orders_postponed.copy()
    postponed_trade = np.dot(fleet.orders_postponed[allowed], cargo_miles[allowed])

    if postponed_trade > 0.:
        # account for whether the trade gap
        # is larger or smaller than the trade
        # from postponed vessels
        scaling = min(trade_gap / postponed_trade, 1.)

        # deliver the postponed vessels
        delivery[allowed] += scaling * fleet.orders_postponed[allowed]

        # reduce the trade gap by the newly added vessels
        trade_gap -= scaling * postponed_trade

        # move the delivered orders from postponement to delivery
        fleet.orders_postponed[allowed] -= delivery[allowed]
        fleet.orders_delivered[allowed] += delivery[allowed]

        if scaling < 1.:
            attempted = np.where(allowed, postponed_before, 0.)
            delivered = np.where(allowed, scaling * postponed_before, 0.)
            log_orderbook_deferral(fleet, delivered, attempted, reason='insufficient trade gap')

    # if the trade gap has not been filled,
    # then look to the orderbook for further orders
    cumulative_orders = to_numpy(fleet.orderbooks)
    incremental_orders = cumulative_orders - fleet.orders_delivered - fleet.orders_postponed
    ordered_trade = np.dot(incremental_orders[allowed], cargo_miles[allowed])

    if ordered_trade > 0.:
        # account for whether the trade gap
        # is larger or smaller than the trade
        # from ordered vessels
        scaling = min(trade_gap / ordered_trade, 1.)

        # deliver the ordered vessels
        orders = scaling * incremental_orders
        fleet.orders_delivered[allowed] += orders[allowed]
        delivery[allowed] += orders[allowed]

        # postpone the undelivered vessels to the next time-step
        fleet.orders_postponed += (1. - scaling) * incremental_orders

        if scaling < 1.:
            attempted = np.where(allowed, incremental_orders, 0.)
            delivered = np.where(allowed, scaling * incremental_orders, 0.)
            log_orderbook_deferral(fleet, delivered, attempted, reason='insufficient trade gap')

    # apply the per-vessel newbuild-limit cap (vessel count)
    over_limit = delivery > cap_count + TOLERANCE
    if np.any(over_limit):
        attempted = delivery.copy()
        excess_count = np.where(over_limit, delivery - cap_count, 0.)
        fleet.orders_delivered -= excess_count
        fleet.orders_postponed += excess_count
        delivery -= excess_count
        log_orderbook_deferral(fleet, delivery, attempted, reason='newbuild limit')

    # transfer to profile
    for v, vessel in enumerate(fleet.assets):
        fleet.profile.add_newbuilds(vessel.name, idx, delivery[v])

    cap_count_remaining = np.maximum(cap_count - delivery, 0.)

    return delivery, np.dot(delivery, cargo_miles), cap_count_remaining


def log_orderbook_deferral(fleet: Fleet,
                           delivered_counts: np.ndarray,
                           attempted_counts: np.ndarray,
                           reason: str) -> None:
    """
    Emit a single INFO log line for the fleet if any orderbook delivery was deferred.

    Parameters
    ----------
    fleet
        The fleet instance, used as the prefix in the log line.
    delivered_counts
        Per-vessel order counts that were actually delivered this timestep.
    attempted_counts
        Per-vessel order counts that should have been delivered (delivered + deferred).
    reason
        Short reason string identifying which deferral path triggered the log.
    """

    attempted_total = float(np.sum(attempted_counts))
    delivered_total = float(np.sum(delivered_counts))

    if attempted_total - delivered_total <= TOLERANCE:
        return

    pct = 100. * delivered_total / attempted_total if attempted_total > 0. else 0.

    logger.info("%s: Deferred orderbook deliveries due to %s (%.0f%% delivered).",
                fleet, reason, pct)


def calculate_modelled_newbuilds(fleet: Fleet, trade_gap: float, cap_count: np.ndarray, idx: int):
    """
    Calculate the number and type of vessels that will enter the fleet to satisfy a given trade gap.

    Parameters
    ----------
    fleet
        The fleet instance.
    trade_gap
        Gap in trade due to scrapping and market growth/decline
    cap_count
        Per-vessel newbuild count budget remaining for this timestep (after the orderbook step).
    idx
        Current time-step index.

    Returns
    -------
    A vector of newbuild increments and the delivered capacity.
    """

    # extract allowed vessels and index map
    index, vessels = zip(*((i, vessel) for i, vessel in enumerate(fleet.assets)
                           if fleet.allow_vessel[vessel.name]
                           and fleet.newbuild_available[vessel.name]))

    # make it a valid array index to numpy
    index = np.array(index)

    # extract the cargo-miles per active vessel
    cargo_miles = np.array(extract_cargo_miles(vessels, idx))

    # calculate inertia based increments of
    # each vessel. Notice that the inertia
    # related reduction of trade-gap was
    # accounted for in the previously
    # by reducing the uptake shares
    inertia_increments = calculate_increments(fleet.current_uptake[index], cargo_miles, trade_gap)

    # apply per-vessel newbuild-limit cap on inertia (no redistribution: unused capacity rolls into the
    # residual trade gap and is filled by the modelled DCM)
    cap_count_subset = cap_count[index].astype(np.float64).copy()
    over = inertia_increments > cap_count_subset + TOLERANCE
    if np.any(over):
        attempted = float(np.sum(inertia_increments))
        inertia_increments[over] = cap_count_subset[over]
        delivered = float(np.sum(inertia_increments))
        pct = 100. * delivered / attempted if attempted > 0. else 0.

        logger.info("%s: Inertia not fully applied due to newbuild limit (%.0f%% delivered).",
                    fleet, pct)

    cap_count_subset = np.maximum(cap_count_subset - inertia_increments, 0.)

    # reduce the trade-gap by the new vessels
    trade_gap -= np.dot(inertia_increments, cargo_miles)

    # convert remaining count cap to a fraction-of-trade-gap (cm) bound for the modelled DCM:
    # cap_share[v] = cap_count_subset[v] · cargo_miles[v] / trade_gap, clamped to [0, 1]
    if trade_gap > TOLERANCE:
        cap_share = np.minimum(cap_count_subset * cargo_miles / trade_gap, 1.)
    else:
        cap_share = np.ones_like(cap_count_subset)

    # calculate the modelled increments of each vessel
    modelled_uptakes = calculate_modelled_uptake(fleet, vessels, idx, cap_share=cap_share)
    modelled_increments = calculate_increments(modelled_uptakes, cargo_miles, trade_gap)

    # expand back to full size of the vessel type list
    increments = np.zeros((len(fleet.assets)))

    for i, v in enumerate(index):
        increments[v] = inertia_increments[i] + modelled_increments[i]

        # transfer to the profile
        fleet.profile.add_newbuilds(fleet.assets[v].name, idx, increments[v])

    return increments, np.dot(np.add(inertia_increments, modelled_increments), cargo_miles)


def calculate_modelled_uptake(fleet: Fleet,
                              vessels: list[Vessel],
                              idx: int,
                              cap_share: np.ndarray | None = None) -> np.ndarray:
    """
    Calculate the relative uptake share of each vessel type using a two-axis discrete choice model
    grouped by fuel type.

    When `cap_share` is provided, per-vessel upper bounds are projected to the two DCM levels: the
    inter-fuel cap per fuel type is the *sum* of the constituent vessel caps (clamped to 1.0), so
    a fuel group with multiple capped vessels can absorb their joint capacity. The intra-fuel cap
    per vessel is normalized by the group cap so the composed per-vessel bound matches
    `cap_share[i]`.

    Parameters
    ----------
    fleet
        The fleet instance.
    vessels
        List of all allowed vessels.
    idx
        Time-step index.
    cap_share
        Optional per-vessel upper bound on cm-share of `trade_gap` (each in [0, 1]), derived from a
        vessel-count cap. Length matches `vessels`. None disables limits.

    Returns
    -------
    np.ndarray
        The uptake shares of each vessel type based on the discrete choice model.
    """

    from navigate.economics.decision import calculate_asset_shares
    from navigate.util import define_index_map, unique_list

    fuel_types = [vessel.fuel_type for vessel in vessels]
    fuel_technology_map = define_index_map(fuel_types)
    unique_fuel_types = unique_list(fuel_types)

    metrics = [vessel.expectation.get_freight_rate(idx) for vessel in vessels]

    metrics_inter_fuel: list[float] = []
    uptake = np.zeros((len(metrics),))
    inter_fuel_limits: list[float] | None = [] if cap_share is not None else None

    for fuel_type in unique_fuel_types:

        indices = fuel_technology_map[fuel_type]
        metrics_intra_fuel = [metrics[i] for i in indices]

        # The inter-fuel cap is the sum of constituent per-vessel caps (clamped to 1.0); intra-fuel caps
        # are normalized by the group cap so the composed bound `group_cap · intra_limits[i]` equals
        # `cap_share[i]`.
        intra_limits = None
        group_cap = None
        if cap_share is not None:
            group_cap = min(sum(cap_share[i] for i in indices), 1.)
            if group_cap > 0.:
                intra_limits = [cap_share[i] / group_cap for i in indices]
            else:
                # Group hard-capped to zero by the inter-fuel limit; intra shares are irrelevant but
                # the intra DCM still needs well-posed limits.
                intra_limits = [1. for _ in indices]

        shares, msg = calculate_asset_shares(metrics_intra_fuel,
                                             UtilityID.LOWER_LOG_RATIO,
                                             fleet.intra_fuel_sensitivity.get(),
                                             limits=intra_limits)

        if msg:
            logger.warning("{}: The number of allowed vessels for fuel type {} {}"
                           .format(fleet, fuel_type, msg))

        for i, share in zip(indices, shares):
            uptake[i] = share

        # average across options of the same fuel type
        metrics_inter_fuel.append(float(np.dot(metrics_intra_fuel, shares)))

        if inter_fuel_limits is not None:
            inter_fuel_limits.append(group_cap)

    fuel_shares, msg = calculate_asset_shares(metrics_inter_fuel,
                                              UtilityID.LOWER_LOG_RATIO,
                                              fleet.inter_fuel_sensitivity.get(),
                                              limits=inter_fuel_limits)

    if msg:
        if inter_fuel_limits is not None:
            ignored_pct = max(0., 1. - float(sum(inter_fuel_limits))) * 100.
            logger.warning("%s: Uptake newbuilds not fully applied (%.0f%% ignored) due to newbuild limit.",
                           fleet, ignored_pct)
        else:
            logger.warning("{}: The number of unique fuel types {}".format(fleet, msg))

    for j, fuel_type in enumerate(unique_fuel_types):

        indices = fuel_technology_map[fuel_type]

        for i in indices:
            uptake[i] *= fuel_shares[j]

    return uptake


def add_newbuilds(fleet: Fleet, increments: list[float], time_step: float):
    """
    Add the newbuild increments to the multiple lists keeping track of multiplier increments.

    Parameters
    ----------
    fleet
        The fleet instance.
    increments
        Multiplier increments per vessel.
    time_step
        Current time-step size.
    """

    for v, increment in enumerate(increments):

        if increment > 0.:

            # the technology bundle chosen at build is charged as a constant
            # yearly rate levelized over the full vessel lifetime
            package_rates = calculate_package_charter_rates(fleet.technology_packages, fleet.assets[v])
            charter_rate = float(np.dot(fleet.newbuild_package_uptake[v], package_rates))

            # expand all increment related lists by one.
            # Per definition the new increments have an age of 0.
            was_empty = not fleet.increments[v]
            fleet.increments[v].append(
                Increment(increment, 0., time_step / YEAR,
                          package_uptake=fleet.newbuild_package_uptake[v].copy(),
                          technology_charter_rate=charter_rate))

            # set baseline if this is the first increment in the list
            if was_empty:
                fleet.increments[v][0].baseline = increment
