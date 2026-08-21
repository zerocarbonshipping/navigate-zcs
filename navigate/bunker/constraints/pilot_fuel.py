# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

import navigate.bunker.solver as gp


def update_pilot_fuel_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Add constraints related to the pilot fuel, namely that enough pilot fuel is used for the combustion process.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which constraints are added.
    """

    v = vessel.get_name()
    effective_lhv = alg.effective_lhv
    spend_sea = alg.spend_sea
    spend_port = alg.spend_port
    chgCoeff = alg.model.chgCoeff

    for c, converter in alg.converters[v].items():

        if not converter.is_dual_fuel():
            continue

        fraction = converter.minimum_pilot_fuel.get()

        pilot_fuels = [fuel.get_name()
                       for fuel_type in converter.pilot_fuel_types
                       for fuel in alg.fuels_per_fuel_type[fuel_type]
                       if fuel.get_name() in alg.usable_fuels[v]]

        main_fuels = [fuel.get_name()
                      for fuel_type in converter.main_fuel_types
                      for fuel in alg.fuels_per_fuel_type[fuel_type]
                      if fuel.get_name() in alg.usable_fuels[v]]

        # at sea
        for pi, pe in alg.leg_idx[v]:

            key = (v, c, pi, pe)

            if key in alg.pilot_fuel_sea:
                constraint = alg.pilot_fuel_sea[key]
            else:
                name = "pilot_fuel_at_sea_{}_{}_{}_{}".format(*key)
                constraint = alg.model.addConstr(gp.LinExpr() >= 0., name=name)
                alg.pilot_fuel_sea[key] = constraint

            for f in pilot_fuels:
                coeff = (1. - fraction) * effective_lhv[(v, c, f)]
                chgCoeff(constraint, spend_sea[v, c, f, pi, pe], coeff)

            for f in main_fuels:
                coeff = -fraction * effective_lhv[(v, c, f)]
                chgCoeff(constraint, spend_sea[v, c, f, pi, pe], coeff)

        # skip the converter used for propulsion
        propulsion_name = vessel.power_system.propulsion.get_name()
        if c == propulsion_name:
            continue

        # in port
        for p in alg.port_idx[v]:

            key = (v, c, p)

            if key in alg.pilot_fuel_port:
                constraint = alg.pilot_fuel_port[key]
            else:
                name = "pilot_fuel_in_port_{}_{}_{}".format(*key)
                constraint = alg.model.addConstr(gp.LinExpr() >= 0., name=name)
                alg.pilot_fuel_port[key] = constraint

            for f in pilot_fuels:
                coeff = (1. - fraction) * effective_lhv[(v, c, f)]
                chgCoeff(constraint, spend_port[v, c, f, p], coeff)

            for f in main_fuels:
                coeff = -fraction * effective_lhv[(v, c, f)]
                chgCoeff(constraint, spend_port[v, c, f, p], coeff)
