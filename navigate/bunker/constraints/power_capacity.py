# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

from navigate.bunker.utils import extract_times
from navigate.core.unit import DAY_TO_HOURS, MWH_TO_GJ


def update_power_capacity_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Add constraints related to the installed power, namely that there is enough power to satisfy the demand.
    # TODO: this constraint is redundant. Just check installed power vs speed-power curve
    # TODO: using LHV is inconsistent with electricity. Should be MWh to GJ unit conversion

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which constraints are added.
    """

    v = vessel.get_name()

    time_sea, time_port = extract_times(vessel, alg.idx)
    unit = DAY_TO_HOURS * MWH_TO_GJ
    efficiency_v = alg.efficiency[v]
    effective_lhv = alg.effective_lhv
    spend_sea = alg.spend_sea
    spend_port = alg.spend_port
    converter_fuels_v = alg.converter_fuels[v]

    # at sea
    for c, converter in alg.converters[v].items():

        eff = efficiency_v[c]
        power_cap = converter.power_capacity.get()

        for leg, (pi, pe) in enumerate(alg.leg_idx[v]):

            key = (v, c, pi, pe)
            rhs = time_sea[leg] / eff * unit * power_cap

            if key in alg.power_capacity_sea:
                alg.power_capacity_sea[key].rhs = rhs
            else:
                lhs = sum(spend_sea[v, c, f, pi, pe] * effective_lhv[(v, c, f)] for f in converter_fuels_v[c])
                name_sea = "power_capacity_at_sea_{}_{}_{}_{}".format(*key)
                alg.power_capacity_sea[key] = alg.model.addConstr(lhs <= rhs, name=name_sea)

    # in port (only converters with port energy demand)
    for c, converter in alg.port_converters[v].items():

        eff = efficiency_v[c]
        power_cap = converter.power_capacity.get()

        for p in alg.port_idx[v]:

            key = (v, c, p)
            rhs = time_port[p] / eff * unit * power_cap

            if key in alg.power_capacity_port:
                alg.power_capacity_port[key].rhs = rhs
            else:
                lhs = sum(spend_port[v, c, f, p] * effective_lhv[(v, c, f)] for f in converter_fuels_v[c])
                name_port = "power_capacity_in_port_{}_{}_{}".format(*key)
                alg.power_capacity_port[key] = alg.model.addConstr(lhs <= rhs, name=name_port)
