# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Vessels added to the fleet: orderbook deliveries, inertia and modelled newbuilds."""

from __future__ import annotations

import itertools
import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import UtilityID
from navigate.core.increment import VesselIncrement
from navigate.core.wrap import to_numpy
from navigate.simulation.economics import calculate_two_axis_uptake
from navigate.simulation.fleet._composition import extract_cargo_miles
from navigate.simulation.fleet._package import calculate_package_charter_rates
from navigate.util import TOLERANCE, YEAR, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import BoolArray, FloatArray

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
        Trade gap of the fleet, in cargo-miles/year.
    cap_count
        Newbuild budget of each vessel type for this time-step, in vessels.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Delivered vessels per type.
    float
        Delivered capacity, in cargo-miles/year.
    FloatArray
        Newbuild budget left after the delivery, in vessels.
    """
    if not fleet.orderbooks:
        return np.zeros(len(fleet.vessels)), 0.0, cap_count

    allowed = is_newbuild_allowed(fleet)
    cargo_miles = extract_cargo_miles(fleet.vessels, idx)

    # the orders postponed earlier are delivered first
    postponed = np.where(allowed, fleet.orders_postponed, 0.0)
    delivery, _ = _calculate_delivery(fleet, postponed, cargo_miles, trade_gap)
    fleet.orders_postponed -= delivery
    fleet.orders_delivered += delivery
    trade_gap -= np.dot(delivery, cargo_miles)

    # new orders the trade gap leaves undelivered are postponed to the next time-step
    cumulative = to_numpy(fleet.orderbooks)
    new_orders = cumulative - fleet.orders_delivered - fleet.orders_postponed
    due = np.where(allowed, new_orders, 0.0)
    new_delivery, share = _calculate_delivery(fleet, due, cargo_miles, trade_gap)
    fleet.orders_postponed += (1.0 - share) * new_orders
    fleet.orders_delivered += new_delivery
    delivery += new_delivery

    # deliveries beyond the newbuild budget are postponed as well
    over = delivery > cap_count + TOLERANCE
    excess = np.where(over, delivery - cap_count, 0.0)
    capped = delivery - excess
    fleet.orders_delivered -= excess
    fleet.orders_postponed += excess

    attempted = np.sum(delivery)
    delivered = np.sum(capped)
    _log_deferral(fleet, "orderbook deliveries", "newbuild limit", delivered, attempted)

    return capped, np.dot(capped, cargo_miles), np.maximum(cap_count - capped, 0.0)


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
        Trade gap left by scrapping and trade growth or decline, in cargo-miles/year.
    cap_count
        Newbuild budget of each vessel type left after the orderbook, in vessels.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Newbuilds per vessel type.
    float
        Delivered capacity, in cargo-miles/year.
    """
    allowed = is_newbuild_allowed(fleet)
    vessels = list(itertools.compress(fleet.vessels, allowed))
    cargo_miles = extract_cargo_miles(vessels, idx)

    current_uptake = fleet.current_uptake[allowed]
    inertia, cap_count_left = _calculate_inertia_newbuilds(
        fleet, current_uptake, cargo_miles, trade_gap, cap_count[allowed]
    )
    trade_gap -= np.dot(inertia, cargo_miles)

    # the DCM bounds shares of the trade gap, so the remaining count budget becomes
    # each vessel type's share of the gap, clamped to [0, 1]
    if trade_gap > TOLERANCE:
        cap_share = np.minimum(cap_count_left * cargo_miles / trade_gap, 1.0)
    else:
        cap_share = np.ones_like(cap_count_left)

    uptakes = _calculate_modelled_uptake(fleet, vessels, idx, cap_share)
    modelled = _calculate_newbuilds(uptakes, cargo_miles, trade_gap)

    allowed_newbuilds = inertia + modelled
    newbuilds = np.zeros(len(fleet.vessels))
    newbuilds[allowed] = allowed_newbuilds

    return newbuilds, np.dot(allowed_newbuilds, cargo_miles)


def add_newbuilds(
    fleet: Fleet, newbuilds: FloatArray, time_step: float, idx: int
) -> None:
    """
    Append each vessel type's newbuilds to its increments, at age zero.

    Parameters
    ----------
    fleet
        Fleet receiving the newbuilds.
    newbuilds
        Newbuilds per vessel type.
    time_step
        Current time-step size, in days.
    idx
        Current time-step index.
    """
    packages = fleet.technology_packages
    cost_flows = fleet.package_cost_flows
    dt = time_step / YEAR

    for v, count in enumerate(newbuilds):
        vessel = fleet.vessels[v]
        fleet.results.newbuilds[vessel.name][idx] += count

        if count <= 0.0:
            continue

        increments = fleet.increments[v]
        package_uptake = fleet.newbuild_package_uptake[v]

        # the technology bundle chosen at build is charged as a constant yearly rate
        # levelized over the full vessel lifetime
        package_rates = calculate_package_charter_rates(packages, cost_flows, vessel)
        charter_rate = float(np.dot(package_uptake, package_rates))

        baseline = None if increments else count
        increment = VesselIncrement(
            multiplier=count,
            age=0.0,
            age_span=dt,
            package_uptake=package_uptake.copy(),
            baseline=baseline,
            technology_charter_rate=charter_rate,
        )
        increments.append(increment)


def is_newbuild_allowed(fleet: Fleet) -> BoolArray:
    """
    Mark the vessel types the fleet allows and that are available as newbuilds.

    Parameters
    ----------
    fleet
        Fleet whose vessel types are marked.

    Returns
    -------
    BoolArray
        Whether each vessel type can be added as a newbuild.
    """
    allowed = np.zeros(len(fleet.vessels), dtype=bool)

    for v, vessel in enumerate(fleet.vessels):
        name = vessel.name
        allowed[v] = fleet.allow_vessel[name] and fleet.newbuild_available[name]

    return allowed


def update_current_uptake(fleet: Fleet, newbuilds: FloatArray, idx: int) -> None:
    """
    Update the fleet's uptake shares from this time-step's newbuilds.

    Each vessel type's share is the trade its newbuilds carry. The next time-step's
    inertia decays the current shares and carries them into its newbuilds, and the
    evolution expectation reads the memory-weighted history of the normalized shares.
    Without newbuilds, the current shares carry over as inertia left them.

    Parameters
    ----------
    fleet
        Fleet whose uptake shares are updated.
    newbuilds
        Newbuilds per vessel type this time-step.
    idx
        Current time-step index.
    """
    if np.sum(newbuilds) > 0.0:
        cargo_miles = extract_cargo_miles(fleet.vessels, idx)
        trade = newbuilds * cargo_miles
        fleet.current_uptake = trade / np.dot(newbuilds, cargo_miles)

    shares = divide_nonzero(fleet.current_uptake, np.sum(fleet.current_uptake))
    fleet.expectation.set_uptakes(idx, shares)


def _calculate_delivery(
    fleet: Fleet, orders: FloatArray, cargo_miles: FloatArray, trade_gap: float
) -> tuple[FloatArray, float]:
    """
    Calculate the orders delivered as far as the trade gap takes the trade they carry.

    Parameters
    ----------
    fleet
        Fleet whose orders are delivered; it prefixes the log line.
    orders
        Orders due per vessel type.
    cargo_miles
        Cargo-miles of one vessel of each type, in cargo-miles/year.
    trade_gap
        Trade gap of the fleet, in cargo-miles/year.

    Returns
    -------
    FloatArray
        Delivered vessels per type.
    float
        Share of the orders delivered; 1.0 when they carry no trade, as none is
        deferred then.
    """
    trade = np.dot(orders, cargo_miles)

    if trade <= 0.0:
        return np.zeros_like(orders), 1.0

    share = min(trade_gap / trade, 1.0)
    delivery = share * orders

    attempted = np.sum(orders)
    delivered = np.sum(delivery)
    reason = "insufficient trade gap"
    _log_deferral(fleet, "orderbook deliveries", reason, delivered, attempted)

    return delivery, share


def _calculate_inertia_newbuilds(
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
        Cargo-miles of one vessel of each type, in cargo-miles/year.
    trade_gap
        Trade gap left by scrapping and trade growth or decline, in cargo-miles/year.
    cap_count
        Newbuild budget of each vessel type for this time-step, in vessels.

    Returns
    -------
    FloatArray
        Inertia newbuilds per vessel type.
    FloatArray
        Newbuild budget left after them, in vessels.
    """
    newbuilds = _calculate_newbuilds(uptakes, cargo_miles, trade_gap)

    # the newbuild budget caps inertia without redistribution: the trade it leaves
    # goes to the modelled newbuilds
    over = newbuilds > cap_count + TOLERANCE
    capped = np.where(over, cap_count, newbuilds)

    attempted = np.sum(newbuilds)
    delivered = np.sum(capped)
    _log_deferral(fleet, "inertia newbuilds", "newbuild limit", delivered, attempted)

    return capped, np.maximum(cap_count - capped, 0.0)


def _calculate_modelled_uptake(
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
        intra_metrics=metrics,
        inter_metrics=metrics,
        intra_utility=UtilityID.LOWER_LOG_RATIO,
        inter_utility=UtilityID.LOWER_LOG_RATIO,
        intra_odds=fleet.intra_fuel_sensitivity.get(),
        inter_odds=fleet.inter_fuel_sensitivity.get(),
        limits=cap_share,
        context=str(fleet),
    )


def _calculate_newbuilds(
    uptakes: FloatArray, cargo_miles: FloatArray, trade_gap: float
) -> FloatArray:
    """
    Calculate the vessels of each type that fill their uptake share of the trade gap.

    Parameters
    ----------
    uptakes
        Uptake share of each vessel type, fraction.
    cargo_miles
        Cargo-miles of one vessel of each type, in cargo-miles/year.
    trade_gap
        Trade gap of the fleet, in cargo-miles/year.

    Returns
    -------
    FloatArray
        Vessels per type.
    """
    return uptakes * trade_gap / cargo_miles


def _log_deferral(
    fleet: Fleet, source: str, reason: str, delivered: float, attempted: float
) -> None:
    """
    Log one INFO line for the fleet if newbuilds from a source were deferred.

    Parameters
    ----------
    fleet
        Fleet whose newbuilds were deferred; it prefixes the log line.
    source
        Newbuilds deferred, such as the orderbook deliveries.
    reason
        What deferred them.
    delivered
        Newbuilds delivered this time-step.
    attempted
        Newbuilds due this time-step, delivered or deferred.
    """
    if attempted - delivered <= TOLERANCE:
        return

    percent = 100.0 * delivered / attempted if attempted > 0.0 else 0.0

    logger.info(
        "%s: Deferred %s due to %s (%.0f%% delivered).",
        fleet,
        source,
        reason,
        percent,
    )
