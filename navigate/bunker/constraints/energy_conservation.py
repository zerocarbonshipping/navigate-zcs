# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

import navigate.bunker.solver as gp
import navigate.core.enum_ as enum_
from navigate.bunker.utils import get_converter_fuels


def update_energy_conservation_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Add constraints related to the power-system model, namely that the fuel spend must satisfy the energy demand.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which constraints are updated.
    """

    v = vessel.get_name()
    expectation = vessel.expectation
    power_system = vessel.power_system
    route = vessel.route

    # local variable hoisting for inner loops
    effective_lhv = alg.effective_lhv
    converter_fuels_v = get_converter_fuels(vessel)
    spend_sea = alg.spend_sea
    spend_port = alg.spend_port
    chgCoeff = alg.model.chgCoeff
    addConstr = alg.model.addConstr
    energy_conservation_sea = alg.energy_conservation_sea
    energy_conservation_port = alg.energy_conservation_port
    leg_idx_v = route.get_leg_indices()
    port_idx_v = range(route.get_number_of_ports())

    # extract the demand as dictionaries
    demands_sea = expectation.get_regional_energy_sea(idx=alg.idx)
    demands_port = expectation.get_energy_port(idx=alg.idx)

    # energy demand at sea
    for energy_type, demand in demands_sea.items():

        converter = power_system.get_converter_by_energy_type(energy_type)
        c = converter.get_name()
        eff = converter.efficiency.get()

        for leg, (pi, pe) in enumerate(leg_idx_v):

            key = (v, pi, pe, energy_type)
            rhs = demand[leg]

            if key in energy_conservation_sea:
                constraint = energy_conservation_sea[key]
            else:
                name_sea = "energy_conservation_at_sea_{}_{}_{}_{}".format(*key)
                constraint = addConstr(gp.LinExpr() == 0., name=name_sea)
                energy_conservation_sea[key] = constraint

            constraint.rhs = rhs

            for f in converter_fuels_v[c]:
                lhv_eff = effective_lhv[(v, c, f)]
                chgCoeff(constraint, spend_sea[v, c, f, pi, pe], eff * lhv_eff)

    # energy demand in port
    for energy_type, demand in demands_port.items():

        converter = power_system.get_converter_by_energy_type(energy_type)
        c = converter.get_name()
        eff = converter.efficiency.get()

        for p in port_idx_v:

            key = (v, p, energy_type)
            rhs = demand[p]

            if key in energy_conservation_port:
                constraint = energy_conservation_port[key]
            else:
                name_port = "energy_conservation_in_port_{}_{}_{}".format(*key)
                constraint = addConstr(gp.LinExpr() == 0., name=name_port)
                energy_conservation_port[key] = constraint

            constraint.rhs = rhs

            for f in converter_fuels_v[c]:
                lhv_eff = effective_lhv[(v, c, f)]
                chgCoeff(constraint, spend_port[v, c, f, p], eff * lhv_eff)

            # shore power contributes to ELECTRICAL port energy conservation
            if energy_type == enum_.EnergyDemandTypeID.ELECTRICAL:
                sp_key = (v, p)
                if sp_key in alg.shore_power:
                    chgCoeff(constraint, alg.shore_power[sp_key], 1.0)
