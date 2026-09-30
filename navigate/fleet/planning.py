# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Newbuild planning: orderbook deliveries, inertia and modelled newbuilds."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import UtilityID
from navigate.core.increment import VesselIncrement
from navigate.core.wrap import to_numpy
from navigate.economics.decision import calculate_two_axis_uptake
from navigate.fleet.technology_adoption import calculate_package_charter_rates
from navigate.util import TOLERANCE, YEAR

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)


def calculate_orderbook_newbuilds(
    fleet: Fleet, trade_gap: float, cap_count: FloatArray, idx: int
) -> tuple[FloatArray, float, FloatArray]:
    """
    Calculate the number of vessels per type the orderbook delivers.

    Orders are postponed, into ``orders_postponed``, when the trade gap is smaller
    than the orderbook or the delivery would exceed the newbuild budget
    ``cap_count``.

    Parameters
    ----------
    fleet
        Fleet whose orderbook is delivered.
    trade_gap
        Trade gap of the fleet, cargo-miles/year.
    cap_count
        Newbuild budget of each vessel type for this time-step, number of vessels.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Delivered vessels per type, number of vessels.
    float
        Delivered capacity, cargo-miles/year.
    FloatArray
        Newbuild budget left after the delivery, number of vessels.
    """
    nv = len(fleet.assets)
    delivery = np.zeros((nv,))

    if not fleet.orderbooks:
        return delivery, 0.0, cap_count

    allowed = np.array(
        [
            (fleet.allow_vessel[vessel.name] and fleet.newbuild_available[vessel.name])
            for vessel in fleet.assets
        ]
    )

    cargo_miles = extract_cargo_miles(fleet.assets, idx=idx)

    # the orders postponed earlier are delivered first
    postponed_before = fleet.orders_postponed.copy()
    postponed_trade = np.dot(fleet.orders_postponed[allowed], cargo_miles[allowed])

    if postponed_trade > 0.0:
        # a trade gap smaller than the postponed trade delivers only part of it
        scaling = min(trade_gap / postponed_trade, 1.0)
        delivery[allowed] += scaling * fleet.orders_postponed[allowed]
        trade_gap -= scaling * postponed_trade

        fleet.orders_postponed[allowed] -= delivery[allowed]
        fleet.orders_delivered[allowed] += delivery[allowed]

        if scaling < 1.0:
            attempted = np.where(allowed, postponed_before, 0.0)
            delivered = np.where(allowed, scaling * postponed_before, 0.0)
            log_orderbook_deferral(
                fleet, delivered, attempted, reason="insufficient trade gap"
            )

    cumulative_orders = to_numpy(fleet.orderbooks)
    incremental_orders = (
        cumulative_orders - fleet.orders_delivered - fleet.orders_postponed
    )
    ordered_trade = np.dot(incremental_orders[allowed], cargo_miles[allowed])

    if ordered_trade > 0.0:
        # a trade gap smaller than the ordered trade delivers only part of it, and
        # the rest is postponed to the next time-step
        scaling = min(trade_gap / ordered_trade, 1.0)
        orders = scaling * incremental_orders
        fleet.orders_delivered[allowed] += orders[allowed]
        delivery[allowed] += orders[allowed]
        fleet.orders_postponed += (1.0 - scaling) * incremental_orders

        if scaling < 1.0:
            attempted = np.where(allowed, incremental_orders, 0.0)
            delivered = np.where(allowed, scaling * incremental_orders, 0.0)
            log_orderbook_deferral(
                fleet, delivered, attempted, reason="insufficient trade gap"
            )

    over_limit = delivery > cap_count + TOLERANCE
    if np.any(over_limit):
        attempted = delivery.copy()
        excess_count = np.where(over_limit, delivery - cap_count, 0.0)
        fleet.orders_delivered -= excess_count
        fleet.orders_postponed += excess_count
        delivery -= excess_count
        log_orderbook_deferral(fleet, delivery, attempted, reason="newbuild limit")

    for v, vessel in enumerate(fleet.assets):
        fleet.profile.add_newbuilds(vessel.name, delivery[v], idx)

    cap_count_remaining = np.maximum(cap_count - delivery, 0.0)

    return delivery, np.dot(delivery, cargo_miles), cap_count_remaining


def log_orderbook_deferral(
    fleet: Fleet,
    delivered_counts: FloatArray,
    attempted_counts: FloatArray,
    reason: str,
) -> None:
    """
    Log one INFO line for the fleet if any orderbook delivery was deferred.

    Parameters
    ----------
    fleet
        Fleet whose deliveries were deferred; it prefixes the log line.
    delivered_counts
        Orders delivered this time-step per vessel type, number of vessels.
    attempted_counts
        Orders due this time-step per vessel type, delivered or deferred, number of
        vessels.
    reason
        Which deferral path triggered the log.
    """
    attempted_total = float(np.sum(attempted_counts))
    delivered_total = float(np.sum(delivered_counts))

    if attempted_total - delivered_total <= TOLERANCE:
        return

    pct = 100.0 * delivered_total / attempted_total if attempted_total > 0.0 else 0.0

    logger.info(
        "%s: Deferred orderbook deliveries due to %s (%.0f%% delivered).",
        fleet,
        reason,
        pct,
    )


def calculate_inertia_increments(
    fleet: Fleet,
    uptakes: FloatArray,
    cargo_miles: FloatArray,
    trade_gap: float,
    cap_count: FloatArray,
) -> tuple[FloatArray, FloatArray]:
    """
    Calculate the newbuilds that inertia carries over from the previous uptake.

    Parameters
    ----------
    fleet
        Fleet whose newbuilds are calculated; it prefixes the log line.
    uptakes
        Current uptake share of each vessel type, already decayed by the inertia,
        fraction.
    cargo_miles
        Cargo-miles of one vessel of each type, cargo-miles/year.
    trade_gap
        Trade gap left by scrapping and trade growth or decline, cargo-miles/year.
    cap_count
        Newbuild budget of each vessel type for this time-step, number of vessels.

    Returns
    -------
    FloatArray
        Inertia newbuilds per vessel type, number of vessels.
    FloatArray
        Newbuild budget left after them, number of vessels.
    """
    increments = _calculate_increments(uptakes, cargo_miles, trade_gap)

    # apply the per-vessel newbuild-limit cap on inertia (no redistribution: unused
    # capacity rolls into the residual trade gap and is filled by the modelled DCM)
    cap_count = cap_count.astype(np.float64).copy()
    over = increments > cap_count + TOLERANCE
    if np.any(over):
        attempted = float(np.sum(increments))
        increments[over] = cap_count[over]
        delivered = float(np.sum(increments))
        pct = 100.0 * delivered / attempted if attempted > 0.0 else 0.0

        logger.info(
            "%s: Inertia not fully applied due to newbuild limit (%.0f%% delivered).",
            fleet,
            pct,
        )

    return increments, np.maximum(cap_count - increments, 0.0)


def calculate_modelled_newbuilds(
    fleet: Fleet, trade_gap: float, cap_count: FloatArray, idx: int
) -> tuple[FloatArray, float]:
    """
    Calculate the newbuilds per vessel type that fill a trade gap.

    Parameters
    ----------
    fleet
        Fleet whose newbuilds are calculated.
    trade_gap
        Trade gap left by scrapping and trade growth or decline, cargo-miles/year.
    cap_count
        Newbuild budget of each vessel type left after the orderbook, number of
        vessels.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Newbuilds per vessel type, number of vessels.
    float
        Delivered capacity, cargo-miles/year.
    """
    allowed_indices, allowed_vessels = zip(
        *(
            (i, vessel)
            for i, vessel in enumerate(fleet.assets)
            if fleet.allow_vessel[vessel.name] and fleet.newbuild_available[vessel.name]
        ),
        strict=True,
    )

    index = np.array(allowed_indices)
    vessels = list(allowed_vessels)
    cargo_miles = extract_cargo_miles(vessels, idx)

    inertia_increments, cap_count_subset = calculate_inertia_increments(
        fleet, fleet.current_uptake[index], cargo_miles, trade_gap, cap_count[index]
    )

    trade_gap -= np.dot(inertia_increments, cargo_miles)

    # the DCM bounds shares of the trade gap, so the remaining count budget becomes
    # each vessel type's share of the gap, clamped to [0, 1]
    if trade_gap > TOLERANCE:
        cap_share = np.minimum(cap_count_subset * cargo_miles / trade_gap, 1.0)
    else:
        cap_share = np.ones_like(cap_count_subset)

    modelled_uptakes = calculate_modelled_uptake(
        fleet, vessels, idx, cap_share=cap_share
    )
    modelled_increments = _calculate_increments(
        modelled_uptakes, cargo_miles, trade_gap
    )

    increments = np.zeros(len(fleet.assets))

    for i, v in enumerate(index):
        increments[v] = inertia_increments[i] + modelled_increments[i]
        fleet.profile.add_newbuilds(fleet.assets[v].name, increments[v], idx)

    return increments, np.dot(
        np.add(inertia_increments, modelled_increments), cargo_miles
    )


def calculate_modelled_uptake(
    fleet: Fleet, vessels: list[Vessel], idx: int, cap_share: FloatArray
) -> FloatArray:
    """
    Calculate each vessel type's uptake share with a two-axis DCM grouped by fuel type.

    Parameters
    ----------
    fleet
        Fleet holding the choice sensitivities.
    vessels
        Vessel types allowed as newbuilds.
    idx
        Current time-step index.
    cap_share
        Upper bound on each vessel type's share of the trade gap, from its newbuild
        budget, fraction; one entry per vessel.

    Returns
    -------
    FloatArray
        Uptake share of each vessel type, fraction.
    """
    fuel_types = [vessel.primary_fuel_type for vessel in vessels]
    metrics = [vessel.expectation.get_freight_rate(idx) for vessel in vessels]

    return calculate_two_axis_uptake(
        group_keys=fuel_types,
        metrics_intra=metrics,
        metrics_inter=metrics,
        intra_utility=UtilityID.LOWER_LOG_RATIO,
        inter_utility=UtilityID.LOWER_LOG_RATIO,
        intra_odds=fleet.intra_fuel_sensitivity.get(),
        inter_odds=fleet.inter_fuel_sensitivity.get(),
        limits=cap_share,
        context=str(fleet),
    )


def add_newbuilds(fleet: Fleet, increments: FloatArray, time_step: float) -> None:
    """
    Append each vessel type's newbuilds to its increments, at age zero.

    Parameters
    ----------
    fleet
        Fleet receiving the newbuilds.
    increments
        Newbuilds per vessel type, number of vessels.
    time_step
        Current time-step size, days.
    """
    for v, increment in enumerate(increments):
        if increment > 0.0:
            # the technology bundle chosen at build is charged as a constant
            # yearly rate levelized over the full vessel lifetime
            package_rates = calculate_package_charter_rates(
                fleet.technology_packages, fleet.assets[v]
            )
            charter_rate = float(
                np.dot(fleet.newbuild_package_uptake[v], package_rates)
            )

            was_empty = not fleet.increments[v]
            fleet.increments[v].append(
                VesselIncrement(
                    increment,
                    0.0,
                    time_step / YEAR,
                    package_uptake=fleet.newbuild_package_uptake[v].copy(),
                    technology_charter_rate=charter_rate,
                )
            )

            if was_empty:
                fleet.increments[v][0].baseline = increment


def extract_cargo_miles(vessels: list[Vessel], idx: int) -> FloatArray:
    """
    Extract each vessel's cargo-miles at a single time-step index.

    Parameters
    ----------
    vessels
        Vessels to extract cargo-miles for.
    idx
        Time-step index.

    Returns
    -------
    FloatArray
        Cargo-miles of one vessel of each type, cargo-miles/year.
    """
    return np.array([vessel.expectation.get_cargo_miles(idx) for vessel in vessels])


def extract_cargo_miles_timeline(vessels: list[Vessel], idx: slice) -> list[FloatArray]:
    """
    Extract each vessel's cargo-miles across a slice of the timeline.

    Parameters
    ----------
    vessels
        Vessels to extract cargo-miles for.
    idx
        Timeline slice.

    Returns
    -------
    list[FloatArray]
        Cargo-miles of one vessel of each type over the slice, cargo-miles/year.
    """
    return [np.asarray(vessel.expectation.get_cargo_miles(idx)) for vessel in vessels]


def _calculate_increments(
    uptakes: FloatArray, cargo_miles: FloatArray, trade_gap: float
) -> FloatArray:
    """
    Calculate the vessels of each type that fill their uptake share of the trade gap.

    Parameters
    ----------
    uptakes
        Uptake share of each vessel type, fraction.
    cargo_miles
        Cargo-miles of one vessel of each type, cargo-miles/year.
    trade_gap
        Trade gap of the fleet, cargo-miles/year.

    Returns
    -------
    FloatArray
        Vessels per type, number of vessels.
    """
    return uptakes * trade_gap / cargo_miles
