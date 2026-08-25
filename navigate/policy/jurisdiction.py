# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.enum_ import RouteTypeID


def calculate_cargo_miles_in_policy_jurisdiction(regulation, vessel, time, idx):

    expectation = vessel.expectation
    cargo_miles = expectation.get_cargo_miles_per_leg(idx)

    return _calculate_attribute_in_policy_jurisdiction(regulation, vessel, time, cargo_miles)


def calculate_nominal_cargo_miles_in_policy_jurisdiction(regulation, vessel, time, idx):

    expectation = vessel.expectation
    nominal_cargo_miles = expectation.get_cargo_miles_per_leg_nominal(idx)

    return _calculate_attribute_in_policy_jurisdiction(regulation, vessel, time, nominal_cargo_miles)


def leg_jurisdiction_fraction(port_i, port_e, jurisdiction, intra_fraction, inter_fraction, extra_fraction):
    """
    The regulated fraction of a leg from its ports' jurisdiction membership.

    Parameters
    ----------
    port_i : Port | str
        Departure port of the leg, in the same representation as the jurisdiction.
    port_e : Port | str
        Arrival port of the leg.
    jurisdiction : list
        Ports inside the regulation's jurisdiction.
    intra_fraction : float
        Fraction applied to legs with both ports inside.
    inter_fraction : float
        Fraction applied to legs with exactly one port inside.
    extra_fraction : float
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


def _calculate_attribute_in_policy_jurisdiction(regulation, vessel, times, attribute_sea):
    """

    Parameters
    ----------
    regulation : Regulation
        Regulation for which energy calculation is made
    vessel : Vessel
        Vessel operating under the jurisdiction of the regulation.
    times : float | np.ndarray
        Time since start of simulation.
    attr_sea : np.ndarray
        Attribute per leg at sea.

    Returns
    -------
    np.ndarray
        Energy used within the regulation jurisdiction.
    """

    jurisdiction = [port.get_name() for port in regulation.jurisdiction]

    intra = regulation.intra_fraction.get(times)
    inter = regulation.inter_fraction.get(times)
    extra = regulation.extra_fraction.get(times)

    # scale the demand by the fraction of time
    # spent in the jurisdiction of the regulation
    route = vessel.route
    ports = [port.get_name() for port in route.ports]
    leg_idx = route.get_leg_indices()

    if route.route_type != RouteTypeID.ROUND_TRIP:

        # calculate the energy per leg
        attribute_sea = np.add.reduce(attribute_sea)
        voyage_distribution = route.get_voyage_distribution()
        attribute_sea = [attribute_sea * fraction for fraction in voyage_distribution.values()]

    attribute = 0.

    # sum attribute at sea
    for leg, (pi, pe) in enumerate(leg_idx):

        fraction = leg_jurisdiction_fraction(ports[pi], ports[pe], jurisdiction, intra, inter, extra)
        attribute += fraction * attribute_sea[leg]

    return attribute


def policies_affecting_port(port, policies):
    """
    Get a list of all the levies which jurisdiction affects the port.

    Parameters
    ----------
    port : Port
        Port to find regulations or levies for.
    policies : dict[str, Regulation | Levy]
        All regulations or levies in the simulation.

    Returns
    -------
    list[Regulation | Levy]
        List of policies affecting the port.
    """

    affected = []

    for policy in policies.values():

        if not policy.is_active():
            continue

        jurisdiction = policy.jurisdiction

        if port in jurisdiction:
            affected.append(policy)

    return affected
