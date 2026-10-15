# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The reference trip a vessel's operation scales to a year, derived from its route.

The derivation is the one reader of a route's operational inputs, and the one place
that tells the route types apart: a ROUND_TRIP states its trip directly, while a
REGIONAL_TRIP states a reference year, which becomes a trip of one voyage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import RouteTypeID
from navigate.core.wrap import to_floats, to_numpy
from navigate.util import HOUR_TO_DAYS, ROUND_OFF, YEAR, divide_nonzero

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from navigate.core.enum_ import EnergyDemandID
    from navigate.core.nodes.route import Route
    from navigate.util.types_ import BoolArray, FloatArray, FloatLike, IntArray


@dataclass(frozen=True)
class ConditionLegs:
    """
    The leg each sailing condition of a route is sailed on.

    It is the one binding of the per-condition values to the legs, read off
    `Route.get_conditions` by `bind_conditions_to_legs`.

    Attributes
    ----------
    legs
        Leg of each condition, in the order of `Route.get_conditions`.
    n_legs
        Number of legs of the route, as `Route.get_legs` lists them.
    """

    legs: IntArray
    n_legs: int


@dataclass(frozen=True)
class ReferenceTrip:
    """
    One voyage of a route's reference pattern, at the route's reference speeds.

    Attributes
    ----------
    condition_legs
        Leg of each sailing condition.
    speeds
        Reference speed in each condition, in knots.
    shares
        Share of its leg's sea time spent in each condition.
    utilizations
        Cargo capacity utilization in each condition.
    leg_miles
        Distance of each leg, in the order of `Route.get_legs`, in nautical
        miles/voyage.
    port_days
        Time at each stop, in days/voyage.
    """

    # per condition
    condition_legs: ConditionLegs
    speeds: FloatArray
    shares: FloatArray
    utilizations: FloatArray

    # per leg and per stop
    leg_miles: FloatArray
    port_days: FloatArray

    @property
    def sailed(self) -> BoolArray:
        """
        Whether each condition takes sea time, the ones a speed extreme is taken over.

        A condition with a zero share, or on a leg without miles, takes no sea time
        at any speed.
        """
        miles = self.leg_miles[self.condition_legs.legs]
        return (self.shares > 0.0) & (miles > 0.0)


def derive_reference_trip(route: Route) -> ReferenceTrip:
    """
    Derive the reference trip of a route from its current inputs.

    Parameters
    ----------
    route
        Route whose reference trip is derived.

    Returns
    -------
    ReferenceTrip
        Reference trip of the route.
    """
    condition_legs = bind_conditions_to_legs(route)
    entries = [entry for _, entry in route.get_conditions()]

    speeds = to_numpy(route.speeds)[entries]
    utilizations = to_numpy(route.utilizations)[entries]

    # check_requirements requires TimeAtSea on every REGIONAL_TRIP, so the None test
    # only narrows its type
    if route.route_type == RouteTypeID.REGIONAL_TRIP and route.time_at_sea is not None:
        time_at_sea = route.time_at_sea.get()
        shares = np.array(route.condition_distribution)[entries]

        speeds_leg = sum_per_leg(condition_legs, shares * speeds)
        leg_miles = _calculate_regional_leg_miles(route, speeds_leg, time_at_sea)
        port_days = _calculate_regional_port_days(route, time_at_sea)

    else:
        shares = np.ones(len(entries))
        leg_miles = to_numpy(route.distances)
        port_days = to_numpy(route.port_durations)

    return ReferenceTrip(
        condition_legs, speeds, shares, utilizations, leg_miles, port_days
    )


def bind_conditions_to_legs(route: Route) -> ConditionLegs:
    """
    Bind each sailing condition of a route to the leg it is sailed on.

    Parameters
    ----------
    route
        Route defining the legs and their conditions.

    Returns
    -------
    ConditionLegs
        Leg of each condition.
    """
    legs = np.array([leg for leg, _ in route.get_conditions()])
    return ConditionLegs(legs, len(route.get_legs()))


def sum_per_leg(
    condition_legs: ConditionLegs, values: FloatArray | Sequence[FloatLike]
) -> FloatArray:
    """
    Sum per-condition values over the conditions of each leg.

    Parameters
    ----------
    condition_legs
        Leg of each condition.
    values
        One value, or one array over time-steps, per condition.

    Returns
    -------
    FloatArray
        One value, or one array over time-steps, per leg.
    """
    values_condition = np.asarray(values, dtype=float)

    sums = np.zeros((condition_legs.n_legs, *values_condition.shape[1:]))
    np.add.at(sums, condition_legs.legs, values_condition)

    return sums


def sum_energy_per_leg(
    condition_legs: ConditionLegs,
    energies: Mapping[EnergyDemandID, FloatArray | Sequence[FloatLike]],
) -> dict[EnergyDemandID, list[FloatLike]]:
    """
    Sum an energy per condition over the conditions of each leg, per demand type.

    Parameters
    ----------
    condition_legs
        Leg of each condition.
    energies
        Energy per energy demand type and condition, in GJ/year.

    Returns
    -------
    dict[EnergyDemandID, list[FloatLike]]
        Energy per energy demand type and leg, in GJ/year.
    """
    return {
        energy_id: list(sum_per_leg(condition_legs, energy))
        for energy_id, energy in energies.items()
    }


def _calculate_regional_leg_miles(
    route: Route, speeds_leg: FloatArray, time_at_sea: float
) -> FloatArray:
    """
    Split the sea miles of a regional route's reference year over its legs.

    A voyage share is the share of the sea miles sailed on its leg. The miles are
    those that fill the reference year's sea time at each leg's mean reference speed.

    Parameters
    ----------
    route
        Regional route holding the voyage shares.
    speeds_leg
        Mean reference speed on each leg, in knots.
    time_at_sea
        Reference share of the year spent at sea.

    Returns
    -------
    FloatArray
        Distance of each leg, in nautical miles/year.
    """
    voyage_shares = _normalize_voyage_shares(route)

    sea_days = time_at_sea * YEAR
    days_per_mile = np.sum(divide_nonzero(voyage_shares, speeds_leg)) * HOUR_TO_DAYS

    return voyage_shares * sea_days / days_per_mile


def _calculate_regional_port_days(route: Route, time_at_sea: float) -> FloatArray:
    """
    Split the port time of a regional route's reference year by the port calls.

    Parameters
    ----------
    route
        Regional route holding the port calls.
    time_at_sea
        Reference share of the year spent at sea.

    Returns
    -------
    FloatArray
        Time at each port, in days/year.
    """
    port_calls = to_numpy(route.port_calls)
    port_days = (1.0 - time_at_sea) * YEAR

    return port_days * divide_nonzero(port_calls, np.sum(port_calls))


def _normalize_voyage_shares(route: Route) -> FloatArray:
    """
    Normalize a regional route's voyage shares to sum to unity, one per leg.

    The shares are rounded in total, and split equally where they total zero.

    Parameters
    ----------
    route
        Regional route holding the voyage shares, keyed by port names.

    Returns
    -------
    FloatArray
        Voyage share of each leg, in the order of `Route.get_legs`.
    """
    shares = to_floats(route.voyage_distribution)
    total = np.round(np.sum(list(shares.values()), axis=0), ROUND_OFF)

    names = [port.name for port in route.ports]
    shares_leg = np.array([shares[(names[i], names[j])] for i, j in route.get_legs()])

    return divide_nonzero(shares_leg, total, default=1.0 / len(shares))
