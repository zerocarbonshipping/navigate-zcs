# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

import navigate.bunker.solver as gp
import navigate.core.enum_ as enum_
from navigate.bunker.utils import get_converter_fuels, get_converters, get_port_converters


def update_vessel_variables(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Update all variables related to a single vessel to the model.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which variables are updated.
    """

    v = vessel.get_name()
    route = vessel.route
    ports = route.ports
    usable_fuels = vessel.usable_fuels
    converters = get_converters(vessel)
    port_converters = get_port_converters(vessel)
    converter_fuels = get_converter_fuels(vessel)
    leg_idx = route.get_leg_indices()
    port_idx = range(len(ports))

    # add bunker variables
    for p, port in enumerate(ports):

        for f in usable_fuels:

            key = (v, p, f)

            if port.is_bunkering_allowed(f):

                if key not in alg.bunker:

                    name = "bunker_{}_{}_{}".format(*key)
                    alg.bunker[key] = alg.model.addVar(vtype=gp.GRB.CONTINUOUS, name=name)

    # # add spend at sea variables
    for c in converters:

        for f in converter_fuels[c]:

            for p1, p2 in leg_idx:

                key = (v, c, f, p1, p2)

                if key not in alg.spend_sea:

                    name = "spend_sea_{}_{}_{}_{}_{}".format(*key)
                    alg.spend_sea[key] = alg.model.addVar(vtype=gp.GRB.CONTINUOUS, name=name)

    # add spend in port variables (only for converters with port energy demand)
    for c in port_converters:

        for f in converter_fuels[c]:

            for p in port_idx:

                key = (v, c, f, p)

                if key not in alg.spend_port:

                    name = "spend_port_{}_{}_{}_{}".format(*key)
                    alg.spend_port[key] = alg.model.addVar(vtype=gp.GRB.CONTINUOUS, name=name)

    # add mass variables
    if route.route_type == enum_.RouteTypeID.ROUND_TRIP:

        for p in port_idx:

            for f in usable_fuels:

                key = (v, p, f)

                if key not in alg.mass_tank:

                    name = "mass_tank_{}_{}_{}".format(*key)
                    alg.mass_tank[key] = alg.model.addVar(vtype=gp.GRB.CONTINUOUS, name=name)

    # add shore power variables
    vessel_capacity = vessel.expectation.get_shore_power_capacity(alg.idx)

    if vessel_capacity > 0.:

        for p, port in enumerate(ports):

            connection_share = port.expectation.get_shore_power_connection_share(alg.idx)

            if connection_share > 0.:

                key = (v, p)

                if key not in alg.shore_power:
                    name = "shore_power_{}_{}".format(*key)
                    alg.shore_power[key] = alg.model.addVar(vtype=gp.GRB.CONTINUOUS, name=name)


def update_regulation_variables(alg: BunkerAlgorithm) -> None:
    """
    Update regulation remedial factor variables.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    for key in alg.regulation_rhs_individual:

        if key not in alg.remedial_factor_individual:
            name = "remedial_factor_individual_{}_{}".format(*key)
            alg.remedial_factor_individual[key] = alg.model.addVar(vtype=gp.GRB.CONTINUOUS, name=name)

    for key in alg.regulation_total_rhs_flexibility:

        if key not in alg.remedial_factor_flexibility:
            name = "remedial_factor_flexibility_{}".format(key)
            alg.remedial_factor_flexibility[key] = alg.model.addVar(vtype=gp.GRB.CONTINUOUS, name=name)
