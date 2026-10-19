# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Attribution of ports, legs and vessel measures to a regulation's jurisdiction."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import RegulationMeasureID
from navigate.util import TON_TO_GRAM

if TYPE_CHECKING:
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.route import Route
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray, FloatLike


def calculate_jurisdiction_fractions(
    regulation: Regulation, routes: dict[str, Route], times: FloatArray, idx: int
) -> None:
    """
    Calculate the regulated fraction of every route port and leg.

    A port inside the jurisdiction is regulated at the intra fraction and one outside
    not at all; a leg at the intra, inter or extra fraction as both, one or neither of
    its ports lie inside. The fractions are Forecasts that events can change, so they
    are rewritten over the remaining timeline every step.

    Parameters
    ----------
    regulation
        Regulation whose jurisdiction the ports and legs are attributed to.
    routes
        All routes in the simulation.
    times
        Remaining timeline, in days.
    idx
        Current time-step index.
    """
    expectation = regulation.expectation
    jurisdiction = set(regulation.jurisdiction)

    intra = regulation.intra_fraction.get(times)
    inter = regulation.inter_fraction.get(times)
    extra = regulation.extra_fraction.get(times)

    for route in routes.values():
        ports = route.ports

        for port in ports:
            fraction = intra if port in jurisdiction else 0.0
            expectation.set_port_fraction(idx, port.name, fraction)

        for (i, j), leg in zip(route.get_legs(), route.get_leg_keys(), strict=True):
            departure_inside = ports[i] in jurisdiction
            arrival_inside = ports[j] in jurisdiction

            if departure_inside and arrival_inside:
                fraction = intra
            elif departure_inside or arrival_inside:
                fraction = inter
            else:
                fraction = extra

            expectation.set_leg_fraction(idx, leg, fraction)


def calculate_regulation_measures(
    regulations: dict[str, Regulation],
    vessels: dict[str, Vessel],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate the measure of every policed vessel under each active regulation.

    Multiplied by the vessel's threshold, the measure gives the vessel's allowance.

    Parameters
    ----------
    regulations
        All regulations in the simulation.
    vessels
        All vessels in the simulation.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    horizon = np.s_[idx:]
    times = timeline[horizon]

    for regulation in regulations.values():
        if not regulation.active:
            continue

        for vessel_name, vessel in vessels.items():
            if not regulation.vessel_is_policed(vessel_name):
                continue

            measure = _calculate_vessel_measure(regulation, vessel, times, horizon)
            regulation.expectation.set_vessel_measure(idx, vessel_name, measure)


def _calculate_vessel_measure(
    regulation: Regulation, vessel: Vessel, times: FloatArray, horizon: slice
) -> FloatLike:
    """
    Calculate a vessel's measure under a regulation over the remaining timeline.

    Parameters
    ----------
    regulation
        Regulation whose measure is calculated.
    vessel
        Vessel whose measure is calculated.
    times
        Remaining timeline, in days.
    horizon
        Slice of the remaining timeline.

    Returns
    -------
    FloatLike
        1 for ABSOLUTE, 0 for INTENSITY, and the capacity-scaled cargo miles in the
        jurisdiction for the transport measures.
    """
    vessel_expectation = vessel.expectation

    if regulation.measure == RegulationMeasureID.ABSOLUTE:
        return 1.0

    if regulation.measure == RegulationMeasureID.INTENSITY:
        # an intensity regulation measures emissions per unit of energy, which only
        # the bunkering determines, so it has no fixed measure
        return 0.0

    if regulation.measure == RegulationMeasureID.TRANSPORT:
        cargo_miles = vessel_expectation.get_cargo_miles_leg(horizon)
    else:
        cargo_miles = vessel_expectation.get_cargo_miles_leg_nominal(horizon)

    return _calculate_transport_measure(regulation, vessel, cargo_miles, times, horizon)


def _calculate_transport_measure(
    regulation: Regulation,
    vessel: Vessel,
    cargo_miles: list[FloatLike],
    times: FloatArray,
    horizon: slice,
) -> FloatLike:
    """
    Calculate a vessel's capacity-scaled cargo miles in the regulation's jurisdiction.

    Parameters
    ----------
    regulation
        Regulation whose jurisdiction the cargo miles are attributed to.
    vessel
        Vessel whose cargo miles are attributed.
    cargo_miles
        Cargo miles per leg over the remaining timeline, in the order of
        `Route.get_legs`.
    times
        Remaining timeline, in days.
    horizon
        Slice of the remaining timeline.

    Returns
    -------
    FloatLike
        Cargo miles in the jurisdiction, scaled by the regulation's capacity of the
        vessel over its nominal capacity, in units that turn a threshold in grams
        per cargo mile into tons.
    """
    regulation_expectation = regulation.expectation
    legs = vessel.route.get_leg_keys()

    transport_measure: FloatLike = 0.0
    for leg, cargo_miles_leg in zip(legs, cargo_miles, strict=True):
        fraction = regulation_expectation.get_leg_fraction(leg, horizon)
        transport_measure += fraction * cargo_miles_leg

    capacity = regulation_expectation.get_vessel_capacity(vessel.name, horizon)
    nominal_capacity = vessel.nominal_capacity.get(times)

    transport_measure *= capacity / nominal_capacity
    transport_measure /= TON_TO_GRAM

    return transport_measure
