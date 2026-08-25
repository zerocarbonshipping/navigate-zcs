# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

from navigate.bunker.utils import get_converter_fuels, get_converters, get_port_converters


def update_bunkered_equals_spent_constraint(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Add constraint ensuring total bunkered fuel equals total spent fuel.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which constraints are updated.
    """

    v = vessel.get_name()
    route = vessel.route
    ports = route.ports
    converters = get_converters(vessel)
    port_converters = get_port_converters(vessel)
    converter_fuels = get_converter_fuels(vessel)
    leg_idx = route.get_leg_indices()
    port_idx = range(len(ports))

    for f in vessel.usable_fuels:

        key = (v, f)
        rhs = 0.

        if key in alg.bunker_equals_spent:

            constraint = alg.bunker_equals_spent[key]

            for p, _port in enumerate(ports):

                # although the coefficient does not change,
                # this is necessary to activate later added
                # bunker fuels which were not available
                # when the constraint was initialized
                if (v, p, f) in alg.bunker:

                    variable = alg.bunker[v, p, f]
                    coefficient = 1.
                    alg.model.chgCoeff(constraint, variable, coefficient)

        else:

            # add constraint to the model
            lhs = (sum(alg.bunker[v, p, f]
                       for p, port in enumerate(ports)
                       if port.is_bunkering_allowed(f))
                   - sum(alg.spend_sea[v, c, f, pi, pe]
                         for c in converters
                         if f in converter_fuels[c]
                         for pi, pe in leg_idx)
                   - sum(alg.spend_port[v, c, f, p]
                         for c in port_converters
                         if f in converter_fuels[c]
                         for p in port_idx))

            name = "bunkered_equals_spent_{}_{}".format(*key)
            alg.bunker_equals_spent[key] = alg.model.addConstr(lhs == rhs, name=name)
