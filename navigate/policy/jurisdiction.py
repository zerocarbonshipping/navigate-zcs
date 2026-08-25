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

        port_i = ports[pi]
        port_e = ports[pe]

        # intra region travel
        if (port_i in jurisdiction) and (port_e in jurisdiction):

            attribute += intra * attribute_sea[leg]

        # inter region travel
        elif (((port_i in jurisdiction) and (port_e not in jurisdiction))
              or ((port_i not in jurisdiction) and (port_e in jurisdiction))):

            attribute += inter * attribute_sea[leg]

        # extra region travel
        else:

            attribute += extra * attribute_sea[leg]

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
