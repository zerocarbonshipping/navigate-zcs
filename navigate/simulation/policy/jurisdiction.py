# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Attribution of ports, legs and vessel measures to a regulation's jurisdiction."""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import RegulationMeasureID
from navigate.util import TON_TO_GRAM

if TYPE_CHECKING:
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray, FloatLike


def calculate_jurisdiction_fractions(
    regulation: Regulation, ports: dict[str, Port], times: FloatArray, idx: int
) -> None:
    """
    Calculate the regulated fraction of every port and leg over the remaining timeline.

    A port inside the jurisdiction is regulated at the intra fraction and one outside
    not at all. Every port and every pair of ports is written, so a port that an event
    moves out of the jurisdiction keeps no fraction from an earlier step.

    Parameters
    ----------
    regulation
        Regulation whose jurisdiction the ports and legs are attributed to.
    ports
        All ports in the simulation.
    times
        Remaining timeline, in days.
    idx
        Current time-step index.
    """
    expectation = regulation.expectation
    jurisdiction = regulation.jurisdiction

    intra = regulation.intra_fraction.get(times)
    inter = regulation.inter_fraction.get(times)
    extra = regulation.extra_fraction.get(times)

    for port_name, port in ports.items():
        fraction = intra if port in jurisdiction else 0.0
        expectation.set_port_fraction(idx, port_name, fraction)

    for departure, arrival in itertools.product(ports.values(), repeat=2):
        leg = (departure.name, arrival.name)
        fraction = _leg_fraction(departure, arrival, jurisdiction, intra, inter, extra)
        expectation.set_leg_fraction(idx, leg, fraction)


def calculate_regulation_measures(
    regulations: dict[str, Regulation],
    vessels: dict[str, Vessel],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate the measure of every policed vessel under each active regulation.

    A vessel's threshold, multiplied by its measure, gives the right-hand side of its
    threshold constraint in the bunkering LP. The transport measures derive from the
    vessels' cargo miles, which are rewritten during the step, so the measures are
    recalculated before each bunkering run.

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
    times = timeline[idx:]

    for regulation in regulations.values():
        if not regulation.active:
            continue

        for vessel_name, vessel in vessels.items():
            if not regulation.vessel_is_policed(vessel_name):
                continue

            measure = _calculate_vessel_measure(regulation, vessel, times, idx)
            regulation.expectation.set_vessel_measure(idx, vessel_name, measure)


def _calculate_vessel_measure(
    regulation: Regulation, vessel: Vessel, times: FloatArray, idx: int
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
    idx
        Current time-step index.

    Returns
    -------
    FloatLike
        1 for ABSOLUTE, 0 for INTENSITY, and the capacity-scaled cargo miles in the
        jurisdiction for the transport measures.
    """
    measure = regulation.measure
    expectation = vessel.expectation

    if measure == RegulationMeasureID.ABSOLUTE:
        return 1.0

    if measure == RegulationMeasureID.INTENSITY:
        # the energy of an intensity regulation depends on the bunker solution, so
        # its threshold sits inside the spend coefficient and the measure is zero
        return 0.0

    if measure == RegulationMeasureID.TRANSPORT:
        cargo_miles = expectation.get_cargo_miles_leg(np.s_[idx:])
    elif measure == RegulationMeasureID.TRANSPORT_NOMINAL:
        cargo_miles = expectation.get_cargo_miles_leg_nominal(np.s_[idx:])
    else:
        raise ValueError("Bug in code, Regulation 'Measure' not defined correctly.")

    return _calculate_transport_measure(regulation, vessel, cargo_miles, times, idx)


def _calculate_transport_measure(
    regulation: Regulation,
    vessel: Vessel,
    cargo_miles: list[FloatLike],
    times: FloatArray,
    idx: int,
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
    idx
        Current time-step index.

    Returns
    -------
    FloatLike
        Cargo miles in the jurisdiction, scaled by the regulation's capacity of the
        vessel over its nominal capacity, in units that turn a threshold in grams
        per cargo mile into tons.
    """
    expectation = regulation.expectation
    legs = vessel.route.get_leg_keys()

    measure: FloatLike = 0.0
    for leg, cargo_miles_leg in zip(legs, cargo_miles, strict=True):
        fraction = expectation.get_leg_fraction(leg, np.s_[idx:])
        measure += fraction * cargo_miles_leg

    capacity = expectation.get_vessel_capacity(vessel.name, np.s_[idx:])
    nominal_capacity = vessel.nominal_capacity.get(times)

    measure *= capacity / nominal_capacity
    measure /= TON_TO_GRAM

    return measure


def _leg_fraction(
    departure: Port,
    arrival: Port,
    jurisdiction: list[Port],
    intra: FloatLike,
    inter: FloatLike,
    extra: FloatLike,
) -> FloatLike:
    """
    Return the regulated fraction of a leg from its ports' jurisdiction membership.

    Parameters
    ----------
    departure
        Departure port of the leg.
    arrival
        Arrival port of the leg.
    jurisdiction
        Ports inside the regulation's jurisdiction.
    intra
        Fraction applied to legs with both ports inside.
    inter
        Fraction applied to legs with exactly one port inside.
    extra
        Fraction applied to legs with both ports outside.

    Returns
    -------
    FloatLike
        The fraction of the leg covered by the regulation.
    """
    if (departure in jurisdiction) and (arrival in jurisdiction):
        return intra

    if (departure in jurisdiction) or (arrival in jurisdiction):
        return inter

    return extra
