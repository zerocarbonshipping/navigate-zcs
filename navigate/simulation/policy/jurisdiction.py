# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Attribution of vessel legs and ports to the jurisdiction of a policy."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import RouteTypeID

if TYPE_CHECKING:
    from navigate.core.nodes.levy import Levy
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatLike


def calculate_cargo_miles_in_policy_jurisdiction(
    regulation: Regulation, vessel: Vessel, time: float, idx: int
) -> float:
    """
    Calculate the vessel's cargo miles at sea that fall within the regulation.

    Parameters
    ----------
    regulation
        Regulation whose jurisdiction the cargo miles are attributed to.
    vessel
        Vessel whose cargo miles are attributed.
    time
        Time since start of simulation, in days.
    idx
        Current time-step index.

    Returns
    -------
    float
        Cargo miles within the regulation jurisdiction.
    """
    expectation = vessel.expectation
    cargo_miles = expectation.get_cargo_miles_per_leg(idx)

    return _calculate_attribute_in_policy_jurisdiction(
        regulation, vessel, time, cargo_miles
    )


def calculate_nominal_cargo_miles_in_policy_jurisdiction(
    regulation: Regulation, vessel: Vessel, time: float, idx: int
) -> float:
    """
    Calculate the vessel's nominal cargo miles at sea that fall within the regulation.

    Parameters
    ----------
    regulation
        Regulation whose jurisdiction the nominal cargo miles are attributed to.
    vessel
        Vessel whose nominal cargo miles are attributed.
    time
        Time since start of simulation, in days.
    idx
        Current time-step index.

    Returns
    -------
    float
        Nominal cargo miles within the regulation jurisdiction.
    """
    expectation = vessel.expectation
    nominal_cargo_miles = expectation.get_cargo_miles_per_leg_nominal(idx)

    return _calculate_attribute_in_policy_jurisdiction(
        regulation, vessel, time, nominal_cargo_miles
    )


def leg_jurisdiction_fraction(
    port_i: Port,
    port_e: Port,
    jurisdiction: list[Port],
    intra_fraction: float,
    inter_fraction: float,
    extra_fraction: float,
) -> float:
    """
    Return the regulated fraction of a leg from its ports' jurisdiction membership.

    Parameters
    ----------
    port_i
        Departure port of the leg.
    port_e
        Arrival port of the leg.
    jurisdiction
        Ports inside the regulation's jurisdiction.
    intra_fraction
        Fraction applied to legs with both ports inside.
    inter_fraction
        Fraction applied to legs with exactly one port inside.
    extra_fraction
        Fraction applied to legs with both ports outside.

    Returns
    -------
    float
        The fraction of the leg covered by the regulation.
    """
    if (port_i in jurisdiction) and (port_e in jurisdiction):
        return intra_fraction

    if (port_i in jurisdiction) or (port_e in jurisdiction):
        return inter_fraction

    return extra_fraction


def _calculate_attribute_in_policy_jurisdiction(
    regulation: Regulation,
    vessel: Vessel,
    time: float,
    attribute_sea: list[FloatLike],
) -> float:
    """
    Calculate the attribute value accumulated within the regulation jurisdiction.

    Parameters
    ----------
    regulation
        Regulation for which energy calculation is made
    vessel
        Vessel operating under the jurisdiction of the regulation.
    time
        Time since start of simulation, in days.
    attribute_sea
        Attribute per leg at sea.

    Returns
    -------
    float
        Attribute accumulated within the regulation jurisdiction.
    """
    jurisdiction = regulation.jurisdiction

    intra = regulation.intra_fraction.get(time)
    inter = regulation.inter_fraction.get(time)
    extra = regulation.extra_fraction.get(time)

    # scale the demand by the fraction of time
    # spent in the jurisdiction of the regulation
    route = vessel.route
    ports = route.ports
    leg_idx = route.get_leg_indices()

    attribute_per_leg = attribute_sea
    if route.route_type != RouteTypeID.ROUND_TRIP:
        attribute_total = np.add.reduce(np.asarray(attribute_sea))
        voyage_distribution = route.get_voyage_distribution()
        attribute_per_leg = [
            attribute_total * fraction for fraction in voyage_distribution.values()
        ]

    attribute: FloatLike = 0.0

    for leg, (pi, pe) in enumerate(leg_idx):
        fraction = leg_jurisdiction_fraction(
            ports[pi], ports[pe], jurisdiction, intra, inter, extra
        )
        attribute += fraction * attribute_per_leg[leg]

    return float(attribute)


def policies_affecting_port(port: Port, policies: dict[str, Levy]) -> list[Levy]:
    """
    Get a list of all the levies which jurisdiction affects the port.

    Parameters
    ----------
    port
        Port to find levies for.
    policies
        All levies in the simulation.

    Returns
    -------
    list[Levy]
        List of levies affecting the port.
    """
    affected = []

    for policy in policies.values():
        if not policy.is_active():
            continue

        jurisdiction = policy.jurisdiction

        if port in jurisdiction:
            affected.append(policy)

    return affected
